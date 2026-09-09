"""Tests for the noisy tier: the mathematics in tools/noisy_tier.py, and the internal
consistency of every committed record.

The mathematics tests pin the conventions the records depend on, because the first
version of this material (docs/GATE_NOISE.md before 2026-09-04) used the wrong
depolarizing convention and understated the error probability by 4/3 per channel.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

qml = pytest.importorskip("pennylane")
import noisy_tier as nt  # noqa: E402
import noise_models as nm  # noqa: E402

RECORDS = ROOT / "experiments" / "noisy_tier" / "records"

# Numerical slack for comparisons that are exact identities in real arithmetic but are
# evaluated over thousands of gates on Hamiltonians with |E| up to 100 Ha. A density-matrix
# evaluation of the N2 UCCSD circuit applies 16,528 channels, and the accumulated rounding
# is ~1e-10 Ha. Anything below this is not a physical quantity: the certification threshold
# is 10 mHa and penalties are reported to 0.1 mHa, so 1e-6 mHa is a millionth of the last
# reported digit. Comparisons that must hold *physically* (the bound, the variational
# floor) keep their own tighter tolerances above their own scale.
TOL_MHA = 1e-6
TOL_HA = TOL_MHA / 1e3


# ── conventions ───────────────────────────────────────────────────────────────

def test_depolarizing_channel_convention_is_four_thirds():
    """PennyLane's DepolarizingChannel(p) is (1 - 4p/3) rho + (4p/3) I/2, so the
    probability of full depolarization is q = 4p/3, not p."""
    p = 0.05
    dev = qml.device("default.mixed", wires=1)
    psi = np.array([np.cos(0.4), np.exp(0.3j) * np.sin(0.4)])
    rho = np.outer(psi, psi.conj())

    @qml.qnode(dev)
    def q():
        qml.StatePrep(psi, wires=0)
        qml.DepolarizingChannel(p, wires=0)
        return qml.density_matrix(wires=0)

    expected = (1 - 4 * p / 3) * rho + (4 * p / 3) * np.eye(2) / 2
    assert np.max(np.abs(q() - expected)) < 1e-12


def test_eps_model_uses_q_equals_four_thirds_p():
    spec = {"params": {"p_1q": 5e-4, "p_2q": 5e-3, "channels": ["depolarizing"]}}
    counts = {"n_1q": 10, "n_2q": 4}
    eps = nt.eps_model(spec, counts)
    q1, q2 = 4 * 5e-4 / 3, 4 * 5e-3 / 3
    assert eps == pytest.approx(1 - (1 - q1) ** 10 * (1 - q2) ** 8, rel=1e-12)
    # and it is larger than the old convention would say
    assert eps > 1 - (1 - 5e-4) ** 10 * (1 - 5e-3) ** 8


def test_eps_model_undefined_for_non_depolarizing_models():
    _, _, _, spec = nm.get("device-sc/v1")
    assert nt.eps_model(spec, {"n_1q": 3, "n_2q": 1}) is None


def test_single_gate_single_qubit_penalty_is_exactly_the_full_mixing_estimate():
    """With one gate on one qubit, any error event mixes the whole register, so
    penalty = eps (c_I - E) must hold exactly. This is the analytic check that fixes
    the convention: under q = p instead of 4p/3 the estimate would be 3/4 of the
    measurement."""
    H = qml.Hamiltonian([0.3, -0.7, 0.2], [qml.Identity(0), qml.PauliZ(0), qml.PauliX(0)])
    wires = [0]
    theta = 0.83

    def circuit_fn(p):
        qml.BasisState(np.array([1]), wires=wires)
        qml.RY(p[0], wires=0)

    decomposed, counts = nt.prepare_tape(circuit_fn, np.array([theta]), H, wires)
    assert counts == {"n_1q": 1, "n_2q": 0, "n_ops_total": 2}
    dev = qml.device("default.mixed", wires=wires)
    e0 = nt._execute(decomposed, dev)
    _, a1, a2, spec = nm.get("depolarizing-current/v1")
    e1 = nt._execute(nt.noisy_tape(decomposed, a1, a2), dev)
    eps = nt.eps_model(spec, counts)
    c_I = 0.3
    assert e1 - e0 == pytest.approx(eps * (c_I - e0), abs=1e-12)


def test_noisy_tape_inserts_one_channel_per_wire_per_gate_and_scales():
    H = qml.Hamiltonian([1.0], [qml.PauliZ(0) @ qml.PauliZ(1)])
    wires = [0, 1]

    def circuit_fn(p):
        qml.RY(p[0], wires=0)
        qml.CNOT(wires=[0, 1])
        qml.RZ(p[1], wires=1)

    decomposed, counts = nt.prepare_tape(circuit_fn, np.array([0.1, 0.2]), H, wires)
    assert counts["n_1q"] == 2 and counts["n_2q"] == 1
    _, a1, a2, _ = nm.get("depolarizing-current/v1")
    assert nt._count_channels(nt.noisy_tape(decomposed, a1, a2, scale=1)) == 2 + 2 * 1
    assert nt._count_channels(nt.noisy_tape(decomposed, a1, a2, scale=3)) == 3 * (2 + 2 * 1)


def test_channel_composition_scaling_equals_closed_form():
    """Applying DepolarizingChannel(p) lambda times equals one channel with
    1 - 4p'/3 = (1 - 4p/3)^lambda. The extrapolation's noise axis is therefore exact,
    not a linearisation."""
    p, lam = 0.02, 3
    q = 4 * p / 3
    p_eff = 0.75 * (1 - (1 - q) ** lam)
    psi = np.array([np.cos(0.6), np.sin(0.6)])
    dev = qml.device("default.mixed", wires=1)

    @qml.qnode(dev)
    def composed():
        qml.StatePrep(psi, wires=0)
        for _ in range(lam):
            qml.DepolarizingChannel(p, wires=0)
        return qml.density_matrix(wires=0)

    @qml.qnode(dev)
    def single():
        qml.StatePrep(psi, wires=0)
        qml.DepolarizingChannel(p_eff, wires=0)
        return qml.density_matrix(wires=0)

    assert np.max(np.abs(composed() - single())) < 1e-12


def test_richardson_recovers_polynomial_intercept():
    # E(lambda) = a + b lambda + c lambda^2 through three points -> exactly a.
    a, b, c = -1.2345, 0.31, -0.07
    e = [a + b * s + c * s * s for s in (1, 2, 3)]
    assert nt.richardson([1, 2, 3], e) == pytest.approx(a, abs=1e-12)
    assert nt.richardson([1, 2, 3], e) == pytest.approx(3 * e[0] - 3 * e[1] + e[2], abs=1e-12)
    assert nt.richardson([1, 2], e[:2]) == pytest.approx(2 * e[0] - e[1], abs=1e-12)


def test_split_commuting_exponentials_is_exact():
    """exp(i t (c1 P1 + c2 P2)) = exp(i t c1 P1) exp(i t c2 P2) when [P1, P2] = 0. The
    tapered UCCSD and ADAPT operators are sums of commuting Pauli words, and the
    decomposition to gates relies on this split."""
    t = 0.37
    P1 = qml.PauliX(0) @ qml.PauliY(1)
    P2 = qml.PauliY(0) @ qml.PauliX(1)
    base = 0.5 * P1 - 0.25 * P2
    tape = qml.tape.QuantumScript([qml.exp(base, coeff=1j * t)], [qml.expval(qml.PauliZ(0))])
    split = nt._split_commuting_exponentials(tape)
    assert len(split.operations) == 2 and all(o.name == "Exp" for o in split.operations)
    U_full = qml.matrix(tape.operations[0], wire_order=[0, 1])
    U_split = qml.matrix(split.operations[1], wire_order=[0, 1]) @ qml.matrix(split.operations[0], wire_order=[0, 1])
    assert np.max(np.abs(U_full - U_split)) < 1e-12


def test_split_refuses_non_commuting_terms():
    base = qml.PauliX(0) + qml.PauliZ(0)
    tape = qml.tape.QuantumScript([qml.exp(base, coeff=0.1j)], [qml.expval(qml.PauliZ(0))])
    with pytest.raises(RuntimeError, match="non-commuting"):
        nt._split_commuting_exponentials(tape)


def test_decomposed_exponential_matches_statevector():
    """The full path -- split, decompose to the gate set, run as a density matrix --
    reproduces the statevector energy of an Exp-based circuit."""
    H = qml.Hamiltonian([0.5, -0.3, 0.2],
                        [qml.PauliZ(0), qml.PauliX(1) @ qml.PauliY(2), qml.PauliZ(0) @ qml.PauliZ(1)])
    wires = [0, 1, 2]
    gen = 0.7 * (qml.PauliX(0) @ qml.PauliY(1) @ qml.PauliZ(2)) - 0.2 * (qml.PauliY(0) @ qml.PauliX(1) @ qml.PauliZ(2))

    def circuit_fn(p):
        qml.BasisState(np.array([1, 0, 0]), wires=wires)
        qml.apply(qml.exp(gen, coeff=1j * p[0]))

    params = np.array([0.41])
    decomposed, counts = nt.prepare_tape(circuit_fn, params, H, wires)
    assert counts["n_2q"] > 0 and all(op.name in nt.GATE_SET for op in decomposed.operations)

    @qml.qnode(qml.device("default.qubit", wires=wires))
    def sv(p):
        circuit_fn(p)
        return qml.expval(H)

    e_mixed = nt._execute(decomposed, qml.device("default.mixed", wires=wires))
    assert e_mixed == pytest.approx(float(sv(params)), abs=1e-12)


# ── committed records ─────────────────────────────────────────────────────────

def _records():
    if not RECORDS.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(RECORDS.glob("*.json"))]


@pytest.mark.skipif(not RECORDS.is_dir(), reason="no noisy-tier records committed")
def test_records_exist_for_every_entry_at_or_below_ten_qubits():
    db = ROOT / "releases" / "v4" / "db"
    expected = set()
    for p in db.glob("*.json"):
        d = json.loads(p.read_text())
        if d["artifacts"]["qubit_hamiltonian"]["num_qubits"] <= 10:
            expected.add(d["entry_id"])
    have = {r["entry_id"] for r in _records()}
    assert expected <= have, "missing records: %s" % sorted(expected - have)


# Entries whose stored circuit the current pipeline cannot reconstruct, and why. A record
# may be "failed" only if it is listed here with the recorded reason; anything else
# failing is a regression. See docs/NOISY_TIER.md, "What the measurement exposed".
EXPECTED_REBUILD_FAILURES = {
    # CASSCF on cyclobutadiene: the orbital gauge is machine-bound. Under the Haswell
    # BLAS kernel the pipeline finds a third Z2 symmetry (5 tapered qubits) where the
    # generating run found two (6), and the UCCSD/ADAPT operator pool, which lives in
    # the stored gauge, cannot be regenerated. Under SkylakeX -- the kernel these two
    # entries were generated with -- it reproduces the stored Hamiltonian to the last
    # bit and both rebuild, which is how the published records were measured
    # (2026-09-09, cluster; see docs/CROSS_MACHINE.md). The names stay here so that a
    # re-run on an AVX2 machine is a known limitation rather than a silent regression.
    # The two HEA entries of the same molecule need no pool and rebuild on either.
    "C4H4_ccpvdz_JW_UCCSD_v4_casscf_tapered": "pipeline tapers to 5 qubits today",
    "C4H4_ccpvdz_JW_ADAPT_v4_casscf_tapered": "pipeline tapers to 5 qubits today",
}


@pytest.mark.parametrize("rec", _records(), ids=lambda r: r["entry_id"][:40])
def test_record_is_internally_consistent(rec):
    assert rec["record_version"] == nt.RECORD_VERSION
    if rec["status"] != "ok":
        expected = [v for k, v in EXPECTED_REBUILD_FAILURES.items() if rec["entry_id"].startswith(k)]
        assert expected, "unexpected rebuild failure: %s" % rec.get("reason")
        assert expected[0] in (rec.get("reason") or "")
        return
    rb, hm = rec["rebuild"], rec["hamiltonian"]
    # the gate: the rebuild reproduced the stored energy, and the decomposition it
    assert rb["rebuild_deviation_Ha"] <= nt.REBUILD_TOL_HA
    assert rb["decomposition_deviation_Ha"] <= 1e-8
    # the tapered sector cannot lie below the stored exact energy
    assert hm["lambda_min_Ha"] >= rb["E_exact_Ha"] - 1e-6
    assert hm["c_I_Ha"] >= rb["E_rebuild_Ha"] - TOL_HA   # mixed energy is not below the state's
    constant_H = abs(hm["mixed_minus_E_Ha"]) <= nt.CONSTANT_H_TOL_HA   # noise cannot act on a constant
    assert constant_H == ("constant_hamiltonian" in rec.get("flags", []))
    assert (abs(rb["constant_correction_Ha"]) > 0) == ("constant_correction_applied" in rec.get("flags", []))
    counts = rec["gate_counts"]
    for name, m in rec["models"].items():
        spec = {"params": m["params"]}
        eps = nt.eps_model(spec, counts)
        assert m["eps_model"] == (pytest.approx(eps, rel=1e-12) if eps is not None else None)
        assert m["noisy_gap_mHa"] >= -TOL_MHA                    # variational, always
        assert m["meets_threshold_under_noise"] == (m["noisy_gap_mHa"] < nt.THRESHOLD_HA * 1e3)
        if constant_H:
            assert m["eps_eff"] is None and abs(m["penalty_mHa"]) < TOL_MHA
        else:
            assert m["eps_eff"] == pytest.approx(m["penalty_mHa"] / 1e3 / hm["mixed_minus_E_Ha"], rel=1e-9)
        if eps is not None:
            assert m["penalty_mHa"] <= m["bound_mHa"] + 1e-9     # the rigorous bound holds
            assert m["bound_mHa"] == pytest.approx(eps * (hm["lambda_max_Ha"] - rb["E_rebuild_Ha"]) * 1e3, rel=1e-9)
            assert m["full_mixing_estimate_mHa"] == pytest.approx(eps * hm["mixed_minus_E_Ha"] * 1e3, rel=1e-9)
            assert m["n_channels"] == counts["n_1q"] + 2 * counts["n_2q"]
    if "zne" in rec:
        z = rec["zne"]
        assert z["scales"] == [1, 2, 3]
        e = z["energies_Ha"]
        assert e[0] == rec["models"][z["model"]]["E_noisy_Ha"]
        if 1.0 - rec["models"][z["model"]]["eps_model"] < 1e-9:
            # Saturated: the probability that NO depolarizing event occurred anywhere is
            # below 1e-9, so the coherent part of the state is gone and the energy sits at
            # the fully mixed value c_I. It does not sit there exactly at lambda = 1, and
            # an earlier version of this test wrongly assumed it did. eps counts "at least
            # one event", not "fully mixed": one depolarizing event on one wire leaves the
            # other wires correlated, and the residue decays only as the channel set is
            # applied again. Both saturated entries show that decay -- C4H4 UCCSD sits
            # 2.8e-3 of the mixing range below c_I at lambda = 1, 5.4e-5 at 2, 1.3e-6 at 3;
            # N2 UCCSD, four times the gate count, starts at 1.8e-6 and is at the numerical
            # floor by lambda = 2, where the last digits no longer order. So: near c_I on
            # the variational side at every scale, and no further away at the end than at
            # the start. No ZNE claim is made in this regime; the record's residual (1.16 Ha
            # for C4H4) says so itself.
            for x in e:
                assert abs(hm["c_I_Ha"] - x) <= 1e-2 * hm["mixed_minus_E_Ha"]
            assert abs(hm["c_I_Ha"] - e[2]) <= abs(hm["c_I_Ha"] - e[0]) + 1e-6
        else:
            assert e[0] <= e[1] + TOL_HA and e[1] <= e[2] + TOL_HA   # more noise, higher energy
        # The recorded value comes from a least-squares polynomial fit; the closed forms
        # below are the same number in exact arithmetic, to the conditioning of a 3-point
        # Vandermonde on energies of order 100 Ha.
        assert z["E_quadratic_Ha"] == pytest.approx(3 * e[0] - 3 * e[1] + e[2], abs=TOL_HA)
        assert z["E_linear_Ha"] == pytest.approx(2 * e[0] - e[1], abs=TOL_HA)
        assert z["residual_mHa"] == pytest.approx((z["E_zne_Ha"] - rb["E_rebuild_Ha"]) * 1e3, rel=1e-9)
        assert z["meets_threshold_after_zne"] == (abs(z["zne_gap_mHa"]) < nt.THRESHOLD_HA * 1e3)


@pytest.mark.skipif(not RECORDS.is_dir(), reason="no noisy-tier records committed")
def test_penalties_increase_with_error_rate():
    for rec in _records():
        if rec["status"] != "ok":
            continue
        opt = rec["models"]["depolarizing-opt/v1"]["penalty_mHa"]
        cur = rec["models"]["depolarizing-current/v1"]["penalty_mHa"]
        pes = rec["models"]["depolarizing-pessimistic/v1"]["penalty_mHa"]
        if "constant_hamiltonian" in rec.get("flags", []):
            # Nothing to order: every penalty is zero up to rounding.
            assert max(abs(x) for x in (opt, cur, pes)) < TOL_MHA, rec["entry_id"]
            continue
        assert -TOL_MHA <= opt <= cur + TOL_MHA <= pes + 2 * TOL_MHA, rec["entry_id"]


@pytest.mark.skipif(not RECORDS.is_dir(), reason="no noisy-tier records committed")
def test_doc_table_matches_records():
    """docs/NOISY_TIER.md carries the table between markers; it must be the generated one."""
    doc = (ROOT / "docs" / "NOISY_TIER.md").read_text()
    begin, end = "<!-- TABLE:BEGIN -->", "<!-- TABLE:END -->"
    body = doc[doc.index(begin) + len(begin):doc.index(end)].strip()
    assert body == nt.markdown_table(str(RECORDS)).strip(), "run tools/fill_noisy_tier_doc.py"


@pytest.mark.skipif(not RECORDS.is_dir(), reason="no noisy-tier records committed")
def test_summary_matches_records():
    summary = RECORDS.parent / "summary.json"
    assert summary.exists(), "run tools/noisy_tier.py --summarise"
    s = json.loads(summary.read_text())
    rows = {r["entry_id"]: r for r in s["rows"]}
    for rec in _records():
        row = rows[rec["entry_id"]]
        assert row["status"] == rec["status"]
        if rec["status"] == "ok":
            assert row["penalty_current_mHa"] == rec["models"]["depolarizing-current/v1"]["penalty_mHa"]
            assert row["zne_residual_mHa"] == rec["zne"]["residual_mHa"]
