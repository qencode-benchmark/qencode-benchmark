"""Regression tests for the three places pipeline bugs actually lived, and hash pins.

The pipeline has had three real bugs, none of them in the arithmetic:

  sector search      the Z2 sector was found by brute-force diagonalising every sector
                     with a DENSE matrix; at 17-18 qubits the MemoryError was swallowed
                     by a bare except and resurfaced as "no valid sector found"
  ADAPT selection    operator screening moved from per-operator qml.grad to a sparse
                     commutator, then to a separate statevector engine above 12 qubits;
                     each step claimed equivalence with the last, verified by hand
  imaginary strip    tapering BK Hamiltonians leaves complex artefacts in the
                     coefficients; the strip is guarded by an exact diagonalisation that
                     must RAISE, not warn, if the cleaned operator is wrong -- and no
                     published entry has ever taken this path, so until now the guard had
                     only ever been exercised in the abstract

None of that was covered by a test, and a 2,449-line pipeline had two. These pin each of
the three against the smallest system that exercises it: H4 in cc-pVDZ, 8 qubits before
tapering, 5 after, an ADAPT pool of 64, and a published entry to compare against. The
fixtures build the Hamiltonian the way main() does -- through of_bridge -- because
operator indices and sector labels depend on term ordering, and the published entry
records [1, 1, 1] and operator 44.

The last group pins published numbers. Every stored entry's hash is recomputed from its
own contents, and a fixed set of fast entries is regenerated end to end through the real
verifier at the strict 1e-6 Ha tolerance. HEA/COBYLA entries are deliberately not in that
set: they have been measured to move by 1e-4 to 1e-2 Ha across environments, so pinning
them here would test the machine, not the code. The weekly CI job covers them in
certification mode.

    pytest tests/test_pipeline_regressions.py -v

Roughly two minutes. Requires the chemistry stack (pyscf, pennylane).
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "releases" / "v4" / "db"
sys.path.insert(0, str(REPO / "src"))

import qencode  # noqa: E402,F401  -- pins BLAS threads before anything imports numpy heavy paths
from qencode.pipeline import generate_entry_v4 as ge  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ── Fixtures: H4 built the way main() builds it ───────────────────────────────

@pytest.fixture(scope="module")
def h4():
    mol = ge.load_molecule("H4")
    py = ge.run_pyscf_suite(mol, "cc-pvdz", orbital_opt="hf", run_classical=False)
    symbols, coords = ge.pyscf_geom_to_symbols_coords(mol["geometry_pyscf"])
    H, nq = ge.build_pl_hamiltonian(
        symbols, coords, "cc-pvdz", "jordan_wigner",
        py["n_electrons"], py["n_orbitals"],
        mf=py["_mf"], use_of_bridge=True, e_casci=py["e_casci"], mo_coeff=py.get("mo_coeff"),
    )
    from pennylane import qchem
    gens = qchem.symmetry_generators(H)
    px = qchem.paulix_ops(gens, nq)
    published = json.loads(next(DB.glob("H4_ccpvdz_JW_ADAPT_*.json")).read_text())
    return {"H": H, "nq": nq, "ne": py["n_electrons"], "e_casci": py["e_casci"],
            "gens": gens, "px": px, "published": published}


@pytest.fixture(scope="module")
def h4_tapered(h4):
    H_t, hf_t, meta = ge.apply_tapering(h4["H"], h4["nq"], h4["ne"], h4["e_casci"],
                                        mapping="jordan_wigner")
    return H_t, hf_t, meta


@pytest.fixture(scope="module")
def h4_adapt(h4, h4_tapered):
    H_t, hf_t, meta = h4_tapered
    pub = h4["published"]["encoding"]["adapt_metadata"]
    am, n0, label = ge.build_adapt_meta(
        H_t, hf_t, h4["ne"], h4["nq"], meta["generators"], meta["paulixops"], meta["sectors"],
        gradient_threshold=pub["gradient_threshold"], max_operators=pub["max_operators"])
    assert label == "adapt" and n0 == 0
    return am


# ── 1. Sector search ──────────────────────────────────────────────────────────

def test_hf_sector_matches_brute_force_scan(h4):
    """The fast path derives the sector from the HF occupation without diagonalising.
    It must land on the same sector, at the same energy, as scanning every sector."""
    fast = ge._find_optimal_sector(h4["H"], h4["gens"], h4["px"], n_electrons=h4["ne"])
    brute = ge._find_optimal_sector(h4["H"], h4["gens"], h4["px"], n_electrons=None)
    assert list(fast[0]) == list(brute[0])
    assert abs(fast[1] - brute[1]) < 1e-10


def test_chosen_sector_contains_the_ground_state(h4):
    sectors, e_tap = ge._find_optimal_sector(h4["H"], h4["gens"], h4["px"], n_electrons=h4["ne"])
    e_full = ge._sector_ground_energy(h4["H"])          # 8 qubits, dense is fine
    assert abs(e_tap - e_full) < 1e-8, "tapering changed the ground energy"
    assert abs(e_tap - h4["e_casci"]) < 1e-6, "qubit Hamiltonian disagrees with CASCI"


def test_tapering_matches_the_published_entry(h4, h4_tapered):
    H_t, hf_t, meta = h4_tapered
    pub = h4["published"]["encoding"]["tapering"]
    assert list(meta["sectors"]) == pub["sectors"]
    assert meta["n_qubits_tap"] == pub["tapered_num_qubits"] == len(H_t.wires)
    assert meta["n_symmetries"] == pub["num_symmetries"]
    assert [int(b) for b in hf_t] == pub["hf_tapered_state"]


def test_sector_search_does_not_scan_when_the_hf_sector_is_available(h4, monkeypatch):
    """The H10 bug: 2^n_sym dense diagonalisations of a 2^17 matrix. With the HF-derived
    sector the search must diagonalise exactly once -- the check, not a scan."""
    calls = []
    real = ge._sector_ground_energy
    monkeypatch.setattr(ge, "_sector_ground_energy",
                        lambda H_tap: (calls.append(1), real(H_tap))[1])
    ge._find_optimal_sector(h4["H"], h4["gens"], h4["px"], n_electrons=h4["ne"])
    assert len(calls) == 1, "sector search diagonalised %d times" % len(calls)


def test_sector_search_fails_loudly_rather_than_returning_garbage(h4, monkeypatch):
    """When no sector can be tapered the answer is an error, never a silent default."""
    from pennylane import qchem

    def boom(*a, **k):
        raise MemoryError("simulated dense allocation failure")

    monkeypatch.setattr(qchem, "taper", boom)
    with pytest.raises(RuntimeError, match="no valid sector"):
        ge._find_optimal_sector(h4["H"], h4["gens"], h4["px"], n_electrons=h4["ne"])


# ── 2. ADAPT operator selection ───────────────────────────────────────────────

def _indices(res):
    return list(res["adapt_metadata"]["selected_operator_indices"])


def test_adapt_reproduces_the_published_first_operator_and_energy(h4, h4_tapered, h4_adapt):
    """The published H4/ADAPT entry: pool of 64, operator 44 selected, certified after
    one operator. Measured to move 3.4e-08 Ha across a drifted environment, so 1e-6 is a
    real bound, not a loose one."""
    H_t, _, _ = h4_tapered
    pub = h4["published"]
    res = ge.run_vqe_adapt(H_t, h4_adapt, max_iter=pub["run_config"]["max_iterations"],
                           seed=pub["run_config"]["seed"], e_target=h4["e_casci"], early_stop=True)
    assert h4_adapt["n_pool"] == pub["encoding"]["adapt_metadata"]["n_operators_pool"]
    assert _indices(res) == pub["encoding"]["adapt_metadata"]["selected_operator_indices"]
    assert abs(res["best_energy_hartree"] - pub["results"]["vqe"]["best_energy_hartree"]) < 1e-6


def test_commutator_screening_selects_what_gradient_screening_selects(h4_tapered, h4_adapt):
    """The ~100x faster sparse-commutator screening replaced per-operator qml.grad on the
    claim that it picks the same operators. Pinned on two ADAPT steps."""
    H_t, _, _ = h4_tapered
    am = dict(h4_adapt, max_operators=2)
    kw = dict(max_iter=200, seed=42, e_target=None, early_stop=False)
    fast = ge.run_vqe_adapt(H_t, am, grad_method="commutator", **kw)
    slow = ge.run_vqe_adapt(H_t, am, grad_method="legacy", **kw)
    assert _indices(fast) == _indices(slow)
    assert abs(fast["best_energy_hartree"] - slow["best_energy_hartree"]) < 1e-8


@pytest.fixture(scope="module")
def h4_generator_pool(h4, h4_tapered):
    """The pool the pipeline builds ABOVE 12 qubits: tapered excitation generators,
    filtered on B^3 = -B. Built here for H4 so the two engines can be compared on
    operators both are valid for."""
    H_t, hf_t, meta = h4_tapered
    am, _, label = ge.build_adapt_meta(
        H_t, hf_t, h4["ne"], h4["nq"], meta["generators"], meta["paulixops"], meta["sectors"],
        gradient_threshold=1e-3, max_operators=50, pool="generators")
    assert label == "adapt" and am["n_pool"] > 0
    return am


def test_statevector_engine_selects_what_the_qnode_engine_selects(h4_tapered, h4_generator_pool):
    """Above 12 qubits a separate sparse-statevector engine takes over. Its docstring
    records hand-verified equivalence; this makes the claim a test, on the generator
    pool it is actually used with, over two ADAPT steps."""
    H_t, _, _ = h4_tapered
    am = dict(h4_generator_pool, max_operators=2)
    kw = dict(max_iter=200, seed=42, e_target=None, early_stop=False)
    qnode = ge.run_vqe_adapt(H_t, am, **kw)
    sv = ge.run_vqe_adapt_statevector(H_t, am, inner_optimizer="cobyla", **kw)
    assert _indices(sv) == _indices(qnode)
    assert abs(sv["best_energy_hartree"] - qnode["best_energy_hartree"]) < 1e-6


def test_statevector_engine_refuses_a_pool_its_exponential_cannot_represent(h4_tapered, h4_adapt):
    """Found by the test above in its first form. The engine's closed-form exponential
    I + sin(t)B + (1-cos t)B^2 is exact only when B^3 = -B, which holds for tapered
    excitation generators and for NOTHING in a taper_operation pool (0 of 64 here: those
    are single Pauli words, B^2 = -4I). Fed such a pool it silently applied a non-unitary
    map -- energies on a theta grid went 0.78 Ha BELOW the exact ground state -- and
    would have written a certified-looking entry. No published entry took that path:
    the two statevector-engine entries (H8, H10) used the generator pool, which is
    filtered on exactly this identity. It must refuse, not guess."""
    H_t, _, _ = h4_tapered
    with pytest.raises(ValueError, match="B\\^3 = -B"):
        ge.run_vqe_adapt_statevector(H_t, h4_adapt, max_iter=10, seed=42,
                                     e_target=None, early_stop=False, inner_optimizer="cobyla")


def test_statevector_engine_energies_are_variational(h4, h4_tapered, h4_generator_pool):
    """With a valid pool the engine's state is normalised, so no energy it reports can
    fall below the exact ground state of the tapered Hamiltonian."""
    H_t, _, _ = h4_tapered
    am = dict(h4_generator_pool, max_operators=3)
    res = ge.run_vqe_adapt_statevector(H_t, am, max_iter=200, seed=42, e_target=None,
                                       early_stop=False, inner_optimizer="cobyla")
    e_exact = ge._sector_ground_energy(H_t)
    assert res["best_energy_hartree"] >= e_exact - 1e-10


def test_adapt_refuses_to_save_an_empty_ansatz(h4_tapered, h4_adapt):
    """If screening finds nothing, the run must raise rather than write E=0."""
    H_t, _, _ = h4_tapered
    am = dict(h4_adapt, gradient_threshold=1e9)
    with pytest.raises(RuntimeError, match="selected 0 operators"):
        ge.run_vqe_adapt(H_t, am, max_iter=10, seed=42, e_target=None, early_stop=False)


# ── 3. Imaginary-strip guard ──────────────────────────────────────────────────

_WORDS = [{}, {0: "Z"}, {1: "Z"}, {0: "Z", 1: "Z"}, {0: "X", 1: "X"}, {0: "Y", 1: "Y"}]
_REAL = [-1.05, 0.39, -0.39, -0.01, 0.18, 0.18]


def _ham(coeffs, words=_WORDS):
    from pennylane.pauli import PauliSentence, PauliWord
    return PauliSentence({PauliWord(w): c for w, c in zip(words, coeffs)}).operation()


def _gs(H):
    import pennylane as qml
    wires = sorted(H.wires)
    return float(np.linalg.eigvalsh(np.real(qml.matrix(H, wire_order=wires)))[0])


def test_strip_leaves_a_real_hamiltonian_untouched():
    H = _ham(_REAL)
    out, stripped, mx = ge.strip_imaginary_from_hamiltonian(H, _gs(H))
    assert out is H and stripped is False and mx == 0.0


def test_strip_ignores_imaginary_parts_below_the_relative_threshold():
    """Noise at 1e-9 of the largest coefficient is reported but not acted on."""
    H = _ham([c + 1e-9j for c in _REAL])
    out, stripped, mx = ge.strip_imaginary_from_hamiltonian(H, _gs(_ham(_REAL)))
    assert stripped is False and out is H
    assert abs(mx - 1e-9) < 1e-15


def test_strip_removes_the_artefact_and_preserves_the_spectrum():
    noise = [5e-7 * (i + 1) for i in range(len(_REAL))]          # up to 3e-6, above 1e-6*1.05
    H = _ham([c + 1j * n for c, n in zip(_REAL, noise)])
    e_ref = _gs(_ham(_REAL))
    out, stripped, mx = ge.strip_imaginary_from_hamiltonian(H, e_ref)
    assert stripped is True
    assert abs(mx - max(noise)) < 1e-15
    coeffs = list(out.pauli_rep.values())
    assert all(float(np.imag(c)) == 0.0 for c in coeffs), "cleaned coefficients are not real"
    assert sorted(np.round(np.real(coeffs), 12)) == sorted(np.round(_REAL, 12))
    assert abs(_gs(out) - e_ref) < 1e-12


def test_strip_drops_terms_whose_real_part_vanishes():
    """A term that was purely an artefact -- no real part at all -- must not survive as a
    zero-coefficient operator."""
    words = _WORDS + [{0: "X"}]
    H = _ham([c + 2e-6j for c in _REAL] + [1e-20 + 4e-6j], words)
    out, stripped, _ = ge.strip_imaginary_from_hamiltonian(H, _gs(_ham(_REAL)))
    assert stripped is True
    assert len(out.pauli_rep) == len(_REAL)


def test_strip_guard_raises_when_the_cleaned_hamiltonian_is_wrong():
    """The verification is the whole point. Give it a reference the cleaned operator
    cannot match and it must raise -- not print a warning and carry on."""
    H = _ham([c + 2e-6j for c in _REAL])
    with pytest.raises(RuntimeError, match="FAILED"):
        ge.strip_imaginary_from_hamiltonian(H, _gs(_ham(_REAL)) + 0.5, verify_tol=1e-3)


# ── 4. Pins on published numbers ──────────────────────────────────────────────

def test_every_published_entry_hash_recomputes_from_its_contents():
    """The hash is the tamper seal and the leaderboard key. Recompute it for every
    entry from the entry's own contents with the pipeline's own functions."""
    files = sorted(DB.glob("*.json"))
    assert len(files) >= 54
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        h = ge.stable_hash(ge._strip_volatile(d))
        assert h == d["provenance"]["entry_hash_sha256"], "%s: hash does not recompute" % f.name
        assert f.stem == d["entry_id"], "%s: filename and entry_id disagree" % f.name
        assert d["entry_id"].endswith(h[:16])


def test_verifier_and_pipeline_agree_on_which_fields_are_volatile():
    """scripts/verify_entry.py carries its own copy of _HASH_EXCLUDE. If the two sets
    drift, the verifier's tamper check silently checks a different hash."""
    tree = ast.parse((REPO / "scripts" / "verify_entry.py").read_text(encoding="utf-8"))
    found = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_HASH_EXCLUDE" for t in node.targets):
            found = ast.literal_eval(node.value)
    assert found is not None, "verify_entry.py no longer defines _HASH_EXCLUDE"
    assert set(found) == set(ge._HASH_EXCLUDE)


# Fast entries that cover all three mappings, both UCCSD and ADAPT, and tapering on a
# 1-qubit and a 5-qubit system. Each is a full regeneration through the real verifier.
PINNED = [
    "H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json",
    "H2_ccpvdz_BK_UCCSD_v4_tapered__sha256_d3f280f5c8f32ccc.json",
    "H2_ccpvdz_PAR_UCCSD_v4_tapered__sha256_b321a0331d6d13eb.json",
    "HF_ccpvdz_BK_UCCSD_v4_tapered__sha256_42ad3163dd5bcf87.json",
    "H4_ccpvdz_JW_ADAPT_v4_tapered__sha256_39f9134a722ad612.json",
]


@pytest.mark.parametrize("name", PINNED)
def test_pinned_entry_regenerates_to_its_stored_energy(name):
    env = dict(os.environ, QENCODE_REPO=str(REPO))
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "verify_entry.py"), str(DB / name),
         "--mode", "strict", "--allow-dirty", "--allow-env-drift"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1000:]
    assert "PASS" in proc.stdout
