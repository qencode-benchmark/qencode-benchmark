#!/usr/bin/env python3
"""Noisy tier: the measured hardware penalty of every published entry under named
gate-noise models.

What this measures
------------------
For each published entry the certified circuit is rebuilt with the pipeline's own
builders (HEA, tapered UCCSD or ADAPT, with the stored parameters and, for ADAPT, the
stored operator selection), and the rebuild is gated: its noiseless energy must
reproduce the stored energy or the entry is recorded as failed and nothing else is
reported for it. The circuit is then decomposed to a fixed one- and two-qubit gate set
and simulated as a density matrix with a named noise model's channels inserted after
every gate. No sampling is involved: gate noise is a bias, not a variance, so the
result is a single deterministic number per (entry, model).

Reported per (entry, model):

    E_noisy                the energy of the noisy state
    penalty     = E_noisy - E_rebuild            (mHa; the hardware penalty)
    noisy_gap   = E_noisy - E_exact              (mHa; >= 0 always, variational)
    meets_threshold_under_noise = noisy_gap < 10 mHa
    eps_model              the exact probability that at least one depolarizing
                           event occurred anywhere in the circuit (pure depolarizing
                           models only; see "Conventions")
    eps_eff     = penalty / (c_I - E_rebuild)    the measured fraction of the way
                           from the ideal energy to the maximally mixed energy
    bound       = eps_model * (lambda_max - E_rebuild)   a rigorous upper bound
    estimate    = eps_model * (c_I - E_rebuild)          the full-mixing estimate

and for one model (default depolarizing-current/v1) a zero-noise extrapolation:
the circuit is evaluated with every channel applied lambda = 1, 2, 3 times in
succession (the mixed-state analogue of gate folding; exact, no approximation of the
scaled channel), and Richardson-extrapolated to lambda = 0.

Conventions (these are where earlier material in this repository went wrong)
-------------------------------------------------------------------------
PennyLane's DepolarizingChannel(p) is  rho -> (1-p) rho + (p/3)(X rho X + Y rho Y + Z rho Z),
which equals  (1 - 4p/3) rho + (4p/3) I/2.  The probability that the qubit is replaced
by the maximally mixed state is therefore q = 4p/3, NOT p. A two-qubit gate carries one
such channel on each of its two wires. Hence for N1 one-qubit and N2 two-qubit gates

    eps = 1 - (1 - 4 p1/3)^N1 * (1 - 4 p2/3)^(2 N2).

Because the total channel is a convex mixture of "no event anywhere" (probability
1 - eps, state exactly ideal) and "at least one event" (some density matrix sigma),

    E_noisy = (1 - eps) E + eps Tr(sigma H),    so   penalty <= eps (lambda_max - E).

That inequality is the bound. Replacing sigma by I/2^n gives eps (c_I - E) with
c_I = Tr(H)/2^n; that is an *estimate* that assumes every error event fully mixes the
register, and it is not a bound in either direction. The measured ratio
eps_eff / eps_model says how far a typical error event actually pushes the energy
toward the mixed value.

Gate counts are those of the decomposed circuit that the channels are inserted into,
not the untapered standard-decomposition counts in circuit_stats.

Usage
-----
    python tools/noisy_tier.py                       # every entry <= 10 tapered qubits
    python tools/noisy_tier.py --entries H2O LiH     # substrings of entry ids
    python tools/noisy_tier.py --workers 8           # one process per entry
    python tools/noisy_tier.py --summarise           # records -> summary.json / .csv
"""
from __future__ import annotations

import os

# Pinned before anything that loads BLAS. The pipeline pins these at import too, but a
# spawned worker imports NumPy first, and a pin applied after BLAS has started has no
# effect: an unpinned 12-worker run showed 127 threads per worker on a 64-core machine.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

DB_DIR = os.path.join(ROOT, "releases", "v4", "db")
OUT_DIR = os.path.join(ROOT, "experiments", "noisy_tier", "records")
RECORD_VERSION = "1"

# The decomposition target. Every operation the noisy circuit contains must be one of
# these, so a "gate" means the same thing for every entry and every ansatz.
ONE_QUBIT_GATES = ["RX", "RY", "RZ", "Hadamard", "PauliX", "PauliY", "PauliZ",
                   "S", "T", "PhaseShift"]
TWO_QUBIT_GATES = ["CNOT", "CZ"]
NOISELESS_OPS = ["BasisState", "StatePrep", "GlobalPhase"]   # state prep, bookkeeping
GATE_SET = set(ONE_QUBIT_GATES + TWO_QUBIT_GATES + NOISELESS_OPS)

THRESHOLD_HA = 0.01          # the suite's single certification threshold
REBUILD_TOL_HA = 1e-6        # rebuild must reproduce the stored energy this closely
# A Hamiltonian is "constant" when the ideal energy already equals the maximally mixed
# energy. Any real Hamiltonian separates the two by millihartree at least; 1e-9 Ha is
# far above the rounding of an expectation value at |E| ~ 100 Ha (observed 3e-12).
CONSTANT_H_TOL_HA = 1e-9
DEFAULT_MODELS = ["depolarizing-opt/v1", "depolarizing-current/v1",
                  "depolarizing-pessimistic/v1", "device-sc/v1"]
DEFAULT_ZNE_MODEL = "depolarizing-current/v1"
DEFAULT_ZNE_SCALES = [1, 2, 3]


# ── circuit rebuild ───────────────────────────────────────────────────────────

def _load_entries(max_qubits, substrings):
    out = []
    for fn in sorted(os.listdir(DB_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(DB_DIR, fn)) as fh:
            d = json.load(fh)
        nq = d["artifacts"]["qubit_hamiltonian"]["num_qubits"]
        eid = d["entry_id"]
        if nq > max_qubits:
            continue
        if substrings and not any(s in eid for s in substrings):
            continue
        out.append(d)
    return out


def _hamiltonian_from_entry(entry):
    """The tapered Hamiltonian exactly as the entry serialised it, on wires 0..n-1.

    This is the certified object: its terms are inside the entry hash. It is used in
    preference to re-deriving the Hamiltonian through PySCF because a CASSCF energy is
    invariant under rotations inside the active space, so the converged orbitals -- and
    with them every Pauli coefficient -- are fixed only by rounding. The stored VQE
    parameters belong to the orbital gauge of the generating run, which a re-derivation
    on another day or machine does not reproduce (measured: 3e-5 Ha per coefficient for
    N2 CASSCF, 1e-15 for LiH with canonical HF orbitals).
    """
    import re
    import pennylane as qml
    h = entry["artifacts"]["qubit_hamiltonian"]
    n = int(h["num_qubits"])
    P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}
    coeffs, ops = [], []
    for t in h["pauli_terms"]:
        ps = str(t["pauli_string"]).strip()
        factors = re.findall(r"([XYZ])(\d+)", ps)
        if ps in ("", "I"):
            op = qml.Identity(0)
        elif not factors or "".join(p + w for p, w in factors) != ps:
            raise RuntimeError("unparseable Pauli string %r in entry" % ps)
        else:
            op = None
            for p, w in factors:
                w = int(w)
                if w >= n:
                    raise RuntimeError("Pauli term on wire %d but entry has %d qubits" % (w, n))
                f = P[p](w)
                op = f if op is None else op @ f
        coeffs.append(float(t["coefficient"]))
        ops.append(op)
    return qml.Hamiltonian(coeffs, ops), list(range(n))


def _max_coeff_deviation(H_pipeline, entry):
    """How far today's re-derived Hamiltonian is from the stored one, coefficient by
    coefficient, using the pipeline's own serialiser so the formats agree. Reported,
    not gated on: it measures orbital-gauge drift, which does not affect energies."""
    from qencode.pipeline import generate_entry_v4 as ge
    mine = {}
    for t in ge.serialize_hamiltonian(H_pipeline):
        mine[t["pauli_string"]] = mine.get(t["pauli_string"], 0.0) + t["coefficient"]
    stored = {}
    for t in entry["artifacts"]["qubit_hamiltonian"]["pauli_terms"]:
        stored[str(t["pauli_string"]).strip()] = stored.get(str(t["pauli_string"]).strip(), 0.0) + t["coefficient"]
    keys = set(mine) | set(stored)
    return max(abs(mine.get(k, 0.0) - stored.get(k, 0.0)) for k in keys)


def rebuild_circuit(entry):
    """Rebuild the entry's circuit with the pipeline's own ansatz builders.

    The Hamiltonian and tapered HF state come from the entry. The HEA needs nothing
    else. The UCCSD and ADAPT operator pools are functions of the untapered
    Hamiltonian's symmetry structure (generators, Pauli-X operators, sectors), which is
    regenerated through PySCF and Z2 tapering and must match what the entry stored.

    Returns (circuit_fn, params, H_tapered, wires, shift, checks). `shift` is the
    constant the pipeline added to every energy of this entry after tapering.
    """
    import numpy as np
    from qencode.pipeline import generate_entry_v4 as ge

    prob = entry["problem"]
    enc = entry["encoding"]
    vqe = entry["results"]["vqe"]
    tap = enc["tapering"]

    H_t, wires = _hamiltonian_from_entry(entry)
    n = len(wires)
    if n != int(tap["tapered_num_qubits"]):
        raise RuntimeError("stored Hamiltonian has %d qubits, tapering block says %d"
                           % (n, tap["tapered_num_qubits"]))
    hf_t = np.asarray(tap["hf_tapered_state"], dtype=int)
    if len(hf_t) != n:
        raise RuntimeError("stored tapered HF state has %d qubits, Hamiltonian %d" % (len(hf_t), n))

    # The pipeline adds this constant to every energy of the entry after tapering; every
    # energy computed from H_t below is shifted by it so absolute values are comparable.
    # A non-zero value means the tapered sector's ground energy lies that far above the
    # exact ground energy -- see docs/NOISY_TIER.md, "What the measurement exposed".
    shift = float(tap.get("bk_constant_correction_ha") or 0.0)
    checks = {
        "hamiltonian_source": "entry artifacts.qubit_hamiltonian.pauli_terms",
        "constant_correction_Ha": shift,
    }

    params = np.asarray(vqe["optimal_params"], dtype=float)
    ansatz = enc["ansatz_type"]
    if ansatz == "hea":
        circuit_fn, n_params, _label = ge.build_hea_circuit(H_t, hf_t, reps=int(enc["ansatz_reps"]))
        checks["operator_pool_source"] = None
    elif ansatz in ("uccsd_tapered", "adapt"):
        mol = ge.load_molecule(prob["name"])
        py = ge.run_pyscf_suite(mol, prob["basis"], orbital_opt=prob["orbital_optimization"],
                                run_classical=False)
        symbols, coords = ge.pyscf_geom_to_symbols_coords(mol["geometry_pyscf"])
        H_full, nq = ge.build_pl_hamiltonian(
            symbols, coords, prob["basis"], enc["mapping"],
            py["n_electrons"], py["n_orbitals"],
            mf=py["_mf"], use_of_bridge=True, e_casci=py["e_casci"], mo_coeff=py.get("mo_coeff"),
        )
        H_pipe, hf_pipe, meta = ge.apply_tapering(H_full, nq, py["n_electrons"], py["e_casci"],
                                                  mapping=enc["mapping"])
        stored_casci = entry["results"]["reference"]["casci_ground_energy_hartree"]
        checks["casci_dev_Ha"] = abs(float(py["e_casci"]) - stored_casci)
        if checks["casci_dev_Ha"] > 1e-6:
            raise RuntimeError("CASCI energy does not reproduce: %.3e Ha off" % checks["casci_dev_Ha"])
        if nq != int(tap["original_num_qubits"]):
            raise RuntimeError("untapered qubit count %d differs from stored %d" % (nq, tap["original_num_qubits"]))
        if len(H_pipe.wires) != n:
            raise RuntimeError("pipeline tapers to %d qubits today (%d symmetries); the entry stores %d. "
                               "The operator pool cannot be reconstructed in the stored gauge."
                               % (len(H_pipe.wires), len(meta["generators"]), n))
        if sorted(H_pipe.wires) != wires:
            raise RuntimeError("pipeline tapered wires %s are not 0..%d" % (sorted(H_pipe.wires), n - 1))
        if list(map(int, hf_pipe)) != list(map(int, hf_t)):
            raise RuntimeError("pipeline tapered HF state differs from stored")
        if list(map(int, meta["sectors"])) != list(map(int, tap["sectors"])):
            raise RuntimeError("pipeline tapering sectors differ from stored")
        pipe_shift = float(meta.get("bk_constant_correction") or 0.0)
        if abs(pipe_shift - shift) > 1e-6:
            raise RuntimeError("pipeline tapering constant %.8f differs from stored %.8f" % (pipe_shift, shift))
        checks["pipeline_hamiltonian_max_coeff_dev_Ha"] = _max_coeff_deviation(H_pipe, entry)
        checks["operator_pool_source"] = ("pipeline rebuild: PySCF %s orbitals, Z2 tapering"
                                          % prob["orbital_optimization"])

        if ansatz == "uccsd_tapered":
            circuit_fn, n_params, label = ge.build_uccsd_circuit(
                H_t, hf_t, py["n_electrons"], nq, meta["generators"], meta["paulixops"], meta["sectors"])
            if label != "uccsd_tapered":
                raise RuntimeError("UCCSD builder fell back to %s" % label)
        else:
            am = enc["adapt_metadata"]
            adapt_meta, _n0, _label = ge.build_adapt_meta(
                H_t, hf_t, py["n_electrons"], nq, meta["generators"], meta["paulixops"], meta["sectors"],
                gradient_threshold=am["gradient_threshold"], max_operators=am["max_operators"])
            pool = adapt_meta["operator_pool"]
            if len(pool) != am["n_operators_pool"]:
                raise RuntimeError("ADAPT pool size %d differs from stored %d"
                                   % (len(pool), am["n_operators_pool"]))
            selected = [pool[i] for i in am["selected_operator_indices"]]
            n_params = len(selected)

            def circuit_fn(p, wires=wires, _sel=selected, _hf=hf_t):
                import pennylane as qml
                qml.BasisState(_hf, wires=wires)
                for i, op in enumerate(_sel):
                    ge._apply_tapered_op(op, p[i])
            checks["adapt_pool_size"] = len(pool)
    else:
        raise RuntimeError("unknown ansatz_type %r" % ansatz)

    if n_params != len(params):
        raise RuntimeError("parameter count %d differs from stored %d" % (n_params, len(params)))
    checks["n_params"] = int(n_params)
    return circuit_fn, params, H_t, wires, shift, checks


# ── tape preparation ──────────────────────────────────────────────────────────

def _split_commuting_exponentials(tape):
    """Replace every Exp whose base is a sum of Pauli words by the product of the
    exponentials of its terms. Exact when the terms commute pairwise, which is
    verified for every term pair; raises otherwise."""
    import pennylane as qml
    new_ops = []
    for op in tape.operations:
        if op.name != "Exp":
            new_ops.append(op)
            continue
        coeffs, terms = op.base.terms()
        if len(terms) == 1:
            new_ops.append(op)
            continue
        for a in range(len(terms)):
            for b in range(a + 1, len(terms)):
                if not qml.is_commuting(terms[a], terms[b]):
                    raise RuntimeError("Exp of non-commuting terms cannot be split exactly")
        for c, t in zip(coeffs, terms):
            new_ops.append(qml.exp(t, coeff=op.coeff * c))
    return qml.tape.QuantumScript(new_ops, tape.measurements, shots=tape.shots)


def prepare_tape(circuit_fn, params, H_t, wires):
    """The pipeline circuit as a tape over GATE_SET, with its gate counts."""
    import pennylane as qml

    def full(p):
        circuit_fn(p)
        return qml.expval(H_t)

    tape = qml.tape.make_qscript(full)(params)
    tape = _split_commuting_exponentials(tape)
    (decomposed,), _ = qml.transforms.decompose(tape, gate_set=GATE_SET)
    n1 = n2 = 0
    for op in decomposed.operations:
        if op.name in NOISELESS_OPS:
            continue
        if op.name not in GATE_SET:
            raise RuntimeError("decomposition left %s outside the gate set" % op.name)
        if len(op.wires) == 1:
            n1 += 1
        elif len(op.wires) == 2:
            n2 += 1
        else:
            raise RuntimeError("%s acts on %d wires" % (op.name, len(op.wires)))
    counts = {"n_1q": n1, "n_2q": n2, "n_ops_total": len(decomposed.operations)}
    return decomposed, counts


def noisy_tape(decomposed, after_1q, after_2q, scale=1):
    """Insert the model's channels after every gate, `scale` times each."""
    import pennylane as qml
    with qml.queuing.AnnotatedQueue() as q:
        for op in decomposed.operations:
            qml.apply(op)
            if op.name in NOISELESS_OPS:
                continue
            for _ in range(int(scale)):
                if len(op.wires) == 1:
                    after_1q(op.wires[0])
                else:
                    after_2q(list(op.wires))
        for m in decomposed.measurements:
            qml.apply(m)
    return qml.tape.QuantumScript.from_queue(q, shots=decomposed.shots)


def _count_channels(tape):
    return sum(1 for op in tape.operations if isinstance(op, __import__("pennylane").operation.Channel))


def _execute(tape, dev):
    import pennylane as qml
    (res,) = qml.execute([tape], dev, diff_method=None)
    return float(res)


# ── model mathematics ─────────────────────────────────────────────────────────

def eps_model(spec, counts):
    """Probability of at least one depolarizing event, PennyLane convention q = 4p/3.
    Defined only for pure depolarizing models."""
    p = spec["params"]
    if p.get("channels") != ["depolarizing"]:
        return None
    q1 = 4.0 * p["p_1q"] / 3.0
    q2 = 4.0 * p["p_2q"] / 3.0
    return 1.0 - (1.0 - q1) ** counts["n_1q"] * (1.0 - q2) ** (2 * counts["n_2q"])


def richardson(scales, energies):
    """Polynomial through (scale, energy) points evaluated at scale 0."""
    import numpy as np
    x = np.asarray(scales, dtype=float)
    y = np.asarray(energies, dtype=float)
    coeffs = np.polyfit(x, y, deg=len(x) - 1)
    return float(np.polyval(coeffs, 0.0))


# ── one entry ─────────────────────────────────────────────────────────────────

def measure_entry(entry, models, zne_model, zne_scales, out_dir=None, prior=None):
    """Measure one entry. With `out_dir`, a partial record is written after every model
    so an interrupted run resumes from the last completed evaluation; `prior` is such a
    record, whose evaluations are reused only if the rebuild reproduces its energy and
    gate counts exactly (the simulation is deterministic, so equality is the right test)."""
    import numpy as np
    import pennylane as qml
    from scipy.sparse.linalg import eigsh
    import noise_models as nm

    t0 = time.time()
    eid = entry["entry_id"]
    rec = {
        "record_version": RECORD_VERSION,
        "entry_id": eid,
        "molecule": entry["problem"]["name"],
        "basis": entry["problem"]["basis"],
        "orbital_optimization": entry["problem"]["orbital_optimization"],
        "mapping": entry["encoding"]["mapping"],
        "ansatz_type": entry["encoding"]["ansatz_type"],
        "optimizer": entry["results"]["vqe"]["optimizer"],
        "n_qubits_tapered": entry["artifacts"]["qubit_hamiltonian"]["num_qubits"],
        "status": "failed",
    }
    try:
        circuit_fn, params, H_t, wires, shift, checks = rebuild_circuit(entry)
        n = len(wires)

        # Gate 1: the pipeline circuit on the pipeline device reproduces the stored energy.
        dev_sv = qml.device("default.qubit", wires=wires)

        @qml.qnode(dev_sv)
        def q_sv(p):
            circuit_fn(p)
            return qml.expval(H_t)

        e_rebuild = float(q_sv(params)) + shift
        e_stored = float(entry["results"]["vqe"]["best_energy_hartree"])
        e_exact = float(entry["results"]["reference"]["exact_qubit_ground_energy_hartree"])
        dev_rebuild = abs(e_rebuild - e_stored)
        if dev_rebuild > REBUILD_TOL_HA:
            raise RuntimeError("rebuild energy %.10f differs from stored %.10f by %.3e Ha"
                               % (e_rebuild, e_stored, dev_rebuild))

        # Gate 2: the decomposed tape on the density-matrix device agrees with it.
        decomposed, counts = prepare_tape(circuit_fn, params, H_t, wires)
        dev_mx = qml.device("default.mixed", wires=wires)
        e_clean_mixed = _execute(decomposed, dev_mx) + shift
        dev_decomp = abs(e_clean_mixed - e_rebuild)
        if dev_decomp > 1e-8:
            raise RuntimeError("decomposed circuit differs from pipeline circuit by %.3e Ha" % dev_decomp)

        # Spectral quantities of the tapered Hamiltonian, computed from the matrix so
        # they do not depend on how the operator happens to be represented.
        Hs = H_t.sparse_matrix(wire_order=wires)
        c_I = float(Hs.diagonal().sum().real) / 2 ** n + shift
        if n <= 4:
            w = np.linalg.eigvalsh(Hs.toarray())
            lam_min, lam_max = float(w[0]) + shift, float(w[-1]) + shift
        else:
            lam_min = float(eigsh(Hs, k=1, which="SA", return_eigenvectors=False)[0]) + shift
            lam_max = float(eigsh(Hs, k=1, which="LA", return_eigenvectors=False)[0]) + shift
        if lam_min < e_exact - 1e-6:
            raise RuntimeError("tapered sector minimum %.10f lies below stored exact %.10f"
                               % (lam_min, e_exact))

        flags = []
        if abs(shift) > 0:
            flags.append("constant_correction_applied")
        if abs(c_I - e_rebuild) <= CONSTANT_H_TOL_HA:
            flags.append("constant_hamiltonian")
        rec.update({
            "flags": flags,
            "rebuild": {
                "E_stored_Ha": e_stored, "E_rebuild_Ha": e_rebuild,
                "rebuild_deviation_Ha": dev_rebuild,
                "E_decomposed_mixed_Ha": e_clean_mixed, "decomposition_deviation_Ha": dev_decomp,
                "E_exact_Ha": e_exact, "gap_Ha": abs(e_rebuild - e_exact),
                "constant_correction_Ha": shift,
                "checks": checks,
            },
            "hamiltonian": {
                "n_qubits": n, "c_I_Ha": c_I, "lambda_min_Ha": lam_min, "lambda_max_Ha": lam_max,
                "mixed_minus_E_Ha": c_I - e_rebuild,
                "tapered_sector_offset_Ha": shift,
            },
            "gate_counts": counts,
            "gate_set": sorted(GATE_SET),
            "state_preparation": "noiseless (BasisState), consistent with circuit_stats",
            "models": {},
        })

        reuse = (prior is not None and prior.get("record_version") == RECORD_VERSION
                 and prior.get("status") in ("ok", "partial")
                 and prior.get("rebuild", {}).get("E_rebuild_Ha") == e_rebuild
                 and prior.get("gate_counts") == counts)
        if reuse:
            rec["models"] = {k: v for k, v in prior.get("models", {}).items() if k in models}
            if prior.get("zne", {}).get("model") == zne_model and prior["zne"].get("scales") == list(zne_scales):
                rec["zne"] = prior["zne"]

        def checkpoint():
            if out_dir:
                rec["status"] = "partial"
                rec["seconds_total"] = round(time.time() - t0, 3)
                rec["provenance"] = provenance()
                _write_record(out_dir, rec)

        for name in models:
            if name in rec["models"]:
                continue
            t1 = time.time()
            dev_name, a1, a2, spec = nm.get(name)
            if dev_name != "default.mixed":
                continue
            tp = noisy_tape(decomposed, a1, a2, scale=1)
            e_noisy = _execute(tp, dev_mx) + shift
            penalty = e_noisy - e_rebuild
            eps = eps_model(spec, counts)
            # eps_eff is undefined when the ideal energy already equals the mixed energy,
            # which happens when the tapered Hamiltonian is a constant: noise then
            # cannot move the energy at all, and the record says so rather than dividing.
            denom = c_I - e_rebuild
            eps_eff = (penalty / denom) if abs(denom) > CONSTANT_H_TOL_HA else None
            m = {
                "params": spec["params"],
                "n_channels": _count_channels(tp),
                "E_noisy_Ha": e_noisy,
                "penalty_mHa": penalty * 1e3,
                "noisy_gap_mHa": (e_noisy - e_exact) * 1e3,
                "meets_threshold_under_noise": bool((e_noisy - e_exact) < THRESHOLD_HA),
                "eps_eff": eps_eff,
                "eps_model": eps,
                "eps_ratio": (eps_eff / eps) if (eps and eps_eff is not None) else None,
                "bound_mHa": (eps * (lam_max - e_rebuild) * 1e3) if eps is not None else None,
                "full_mixing_estimate_mHa": (eps * (c_I - e_rebuild) * 1e3) if eps is not None else None,
                "seconds": round(time.time() - t1, 3),
            }
            if m["bound_mHa"] is not None and m["penalty_mHa"] > m["bound_mHa"] + 1e-9:
                raise RuntimeError("penalty exceeds the rigorous bound under %s" % name)
            rec["models"][name] = m
            checkpoint()

        if zne_model and zne_model in rec["models"] and "zne" not in rec:
            t1 = time.time()
            _, a1, a2, spec = nm.get(zne_model)
            energies = []
            for s in zne_scales:
                if s == 1:
                    energies.append(rec["models"][zne_model]["E_noisy_Ha"])
                else:
                    energies.append(_execute(noisy_tape(decomposed, a1, a2, scale=s), dev_mx) + shift)
            e_lin = richardson(zne_scales[:2], energies[:2]) if len(energies) >= 2 else None
            e_quad = richardson(zne_scales[:3], energies[:3]) if len(energies) >= 3 else None
            e_zne = e_quad if e_quad is not None else e_lin
            rec["zne"] = {
                "model": zne_model,
                "scaling": "each channel applied lambda times in succession (exact composition)",
                "scales": list(zne_scales),
                "energies_Ha": energies,
                "E_linear_Ha": e_lin,
                "E_quadratic_Ha": e_quad,
                "E_zne_Ha": e_zne,
                "residual_mHa": (e_zne - e_rebuild) * 1e3,
                "zne_gap_mHa": (e_zne - e_exact) * 1e3,
                "meets_threshold_after_zne": bool(abs(e_zne - e_exact) < THRESHOLD_HA),
                "seconds": round(time.time() - t1, 3),
            }
        rec["status"] = "ok"
    except Exception as exc:  # recorded, never hidden
        rec["status"] = "failed"
        rec["reason"] = "%s: %s" % (type(exc).__name__, exc)
    rec["seconds_total"] = round(time.time() - t0, 3)
    rec["provenance"] = provenance()
    return rec


def provenance():
    import numpy, scipy, pennylane
    try:
        import pyscf
        pyscf_v = pyscf.__version__
    except Exception:
        pyscf_v = None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                         stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        commit = None
    with open(os.path.join(ROOT, "tools", "noise_models.py"), "rb") as fh:
        nm_hash = hashlib.sha256(fh.read()).hexdigest()
    return {
        "computed_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "noise_models_sha256": nm_hash,
        "tool_versions": {"python": platform.python_version(), "numpy": numpy.__version__,
                          "scipy": scipy.__version__, "pennylane": pennylane.__version__,
                          "pyscf": pyscf_v},
        "blas_threads": os.environ.get("OMP_NUM_THREADS"),
        "simulator": "pennylane default.mixed (density matrix, no sampling)",
    }


# ── driver ────────────────────────────────────────────────────────────────────

def _record_path(out_dir, eid):
    return os.path.join(out_dir, eid + ".json")


def _write_record(out_dir, rec):
    os.makedirs(out_dir, exist_ok=True)
    path = _record_path(out_dir, rec["entry_id"])
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rec, fh, indent=1)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def _worker(args):
    entry, models, zne_model, zne_scales, out_dir = args
    prior = None
    path = _record_path(out_dir, entry["entry_id"])
    if os.path.exists(path):
        with open(path) as fh:
            prior = json.load(fh)
    rec = measure_entry(entry, models, zne_model, zne_scales, out_dir=out_dir, prior=prior)
    _write_record(out_dir, rec)
    return rec


def _one_line(rec):
    if rec["status"] != "ok":
        return "%-62s FAILED  %s" % (rec["entry_id"][:62], rec.get("reason", "")[:80])
    cur = rec["models"].get("depolarizing-current/v1", {})
    z = rec.get("zne", {})
    nan = float("nan")
    return ("%-62s %2dq 1q=%4d 2q=%4d  penalty %8.2f mHa  gap %8.2f  eps %.3f/%.3f"
            "  zne %+7.2f  %6.0fs"
            % (rec["entry_id"][:62], rec["n_qubits_tapered"], rec["gate_counts"]["n_1q"],
               rec["gate_counts"]["n_2q"], cur.get("penalty_mHa", nan),
               cur.get("noisy_gap_mHa", nan),
               cur.get("eps_eff") if cur.get("eps_eff") is not None else nan,
               cur.get("eps_model") or nan, z.get("residual_mHa", nan),
               rec["seconds_total"]))


def summarise(out_dir):
    recs = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith(".json"):
            with open(os.path.join(out_dir, fn)) as fh:
                recs.append(json.load(fh))
    rows = []
    for r in recs:
        row = {"entry_id": r["entry_id"], "molecule": r["molecule"], "mapping": r["mapping"],
               "ansatz_type": r["ansatz_type"], "n_qubits": r["n_qubits_tapered"],
               "status": r["status"]}
        if r["status"] == "ok":
            row.update({"flags": ";".join(r.get("flags", [])),
                        "n_1q": r["gate_counts"]["n_1q"], "n_2q": r["gate_counts"]["n_2q"],
                        "gap_mHa": r["rebuild"]["gap_Ha"] * 1e3,
                        "c_I_minus_E_Ha": r["hamiltonian"]["mixed_minus_E_Ha"]})
            for name, m in r["models"].items():
                key = name.replace("depolarizing-", "").replace("/v1", "")
                row["penalty_%s_mHa" % key] = m["penalty_mHa"]
                row["noisy_gap_%s_mHa" % key] = m["noisy_gap_mHa"]
                row["meets_%s" % key] = m["meets_threshold_under_noise"]
                row["eps_eff_%s" % key] = m["eps_eff"]
                row["eps_model_%s" % key] = m["eps_model"]
            if "zne" in r:
                row["zne_residual_mHa"] = r["zne"]["residual_mHa"]
                row["zne_gap_mHa"] = r["zne"]["zne_gap_mHa"]
                row["meets_after_zne"] = r["zne"]["meets_threshold_after_zne"]
        else:
            row["reason"] = r.get("reason")
        rows.append(row)
    base = os.path.dirname(out_dir)
    with open(os.path.join(base, "summary.json"), "w") as fh:
        json.dump({"record_version": RECORD_VERSION, "n_records": len(rows), "rows": rows},
                  fh, indent=1)
        fh.write("\n")
    keys = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with open(os.path.join(base, "summary.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    for r in recs:
        print(_one_line(r))
    ok = [r for r in recs if r["status"] == "ok"]
    print("\n  %d records, %d ok, %d failed -> %s" % (len(recs), len(ok), len(recs) - len(ok), base))
    return rows


def markdown_table(out_dir):
    """The results table in docs/NOISY_TIER.md, generated from the records so the
    document cannot drift from the data."""
    recs = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith(".json"):
            with open(os.path.join(out_dir, fn)) as fh:
                recs.append(json.load(fh))
    mapping = {"jordan_wigner": "JW", "parity": "PAR", "bravyi_kitaev": "BK"}
    ansatz = {"hea": "HEA", "uccsd_tapered": "UCCSD", "adapt": "ADAPT"}
    lines = ["| entry | q | 1q | 2q | gap | opt | **current** | pess | device-sc | ε_eff/ε | ZNE resid. | under noise | after ZNE |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    ok = [r for r in recs if r["status"] == "ok"]
    ok.sort(key=lambda r: (r["n_qubits_tapered"], r["molecule"], r["ansatz_type"], r["mapping"]))
    for r in ok:
        m = r["models"]
        cur = m["depolarizing-current/v1"]
        z = r.get("zne", {})
        label = "%s %s %s" % (r["molecule"], mapping.get(r["mapping"], r["mapping"]), ansatz.get(r["ansatz_type"], r["ansatz_type"]))
        if r["ansatz_type"] == "hea":
            label += " r%d" % ((r["gate_counts"]["n_1q"] // r["n_qubits_tapered"]) - 1) if r["n_qubits_tapered"] else ""
        if "constant_correction_applied" in r.get("flags", []):
            label += " ‡"
        if "constant_hamiltonian" in r.get("flags", []):
            # nothing can move a constant: not measurable, and not evidence of robustness
            lines.append("| %s † | %d | %d | %d | %.3f | — | — | — | — | — | — | n/a | n/a |" % (
                label, r["n_qubits_tapered"], r["gate_counts"]["n_1q"], r["gate_counts"]["n_2q"],
                r["rebuild"]["gap_Ha"] * 1e3))
            continue
        ratio = ("%.2f" % cur["eps_ratio"]) if cur.get("eps_ratio") is not None else "—"
        lines.append("| %s | %d | %d | %d | %.3f | %.1f | **%.1f** | %.1f | %.1f | %s | %+.2f | %s | %s |" % (
            label, r["n_qubits_tapered"], r["gate_counts"]["n_1q"], r["gate_counts"]["n_2q"],
            r["rebuild"]["gap_Ha"] * 1e3,
            m["depolarizing-opt/v1"]["penalty_mHa"], cur["penalty_mHa"],
            m["depolarizing-pessimistic/v1"]["penalty_mHa"], m["device-sc/v1"]["penalty_mHa"],
            ratio, z.get("residual_mHa", float("nan")),
            "yes" if cur["meets_threshold_under_noise"] else "no",
            "yes" if z.get("meets_threshold_after_zne") else "no"))
    failed = [r for r in recs if r["status"] != "ok"]
    if failed:
        lines.append("")
        lines.append("Not measured (rebuild gate failed):")
        for r in failed:
            lines.append("- `%s`: %s" % (r["entry_id"], r.get("reason")))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--entries", nargs="*", default=[], help="substrings of entry ids to run")
    ap.add_argument("--max-qubits", type=int, default=10)
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--zne-model", default=DEFAULT_ZNE_MODEL)
    ap.add_argument("--zne-scales", default="1,2,3")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="recompute existing records")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--table", action="store_true", help="print the docs/NOISY_TIER.md results table")
    a = ap.parse_args(argv)

    if a.summarise:
        summarise(a.out)
        return 0
    if a.table:
        print(markdown_table(a.out))
        return 0

    scales = [int(s) for s in a.zne_scales.split(",")]
    entries = _load_entries(a.max_qubits, a.entries)

    def _done(e):
        """Complete only when every requested model and the extrapolation are present;
        failed and partial records are retried (partial ones resume from their checkpoint)."""
        p = _record_path(a.out, e["entry_id"])
        if not os.path.exists(p):
            return False
        with open(p) as fh:
            rec = json.load(fh)
        if rec.get("status") != "ok":
            return False
        if any(m not in rec.get("models", {}) for m in a.models if m != "ideal/v1"):
            return False
        return not (a.zne_model in a.models and "zne" not in rec)

    todo = [e for e in entries if a.force or not _done(e)]
    print("  %d entries <= %d qubits, %d to compute, models: %s, zne: %s x %s"
          % (len(entries), a.max_qubits, len(todo), ", ".join(a.models), a.zne_model, scales))
    sys.stdout.flush()
    jobs = [(e, a.models, a.zne_model, scales, a.out) for e in todo]
    if a.workers > 1 and len(jobs) > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.workers) as pool:
            for rec in pool.imap_unordered(_worker, jobs):
                print(_one_line(rec)); sys.stdout.flush()
    else:
        for job in jobs:
            print(_one_line(_worker(job))); sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
