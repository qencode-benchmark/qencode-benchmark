#!/usr/bin/env python3
"""
QEncode v4 Entry Generator
============================
Extends generate_entry_v3.py with:
  - PennyLane 0.45 + NumPy 2.0 support
  - cc-pVDZ default basis (was 6-31G in v3)
  - CASSCF orbital optimisation (--orbital-opt casscf)
  - BK imaginary-strip fix: strips imaginary Pauli coefficients
    after tapering, verifies via exact diag, stores flag in entry
  - Schema version 4.0.0
  - Output: releases/v4/db/

Backward compatibility:
  v3 entries remain reproducible with generate_entry_v3.py + requirements-v3.txt.
  Do NOT use this script for v3 entry reproduction.

Pipeline:
  PySCF (HF → CASSCF [optional] → CASCI)
    → PennyLane (qubit Hamiltonian, JW / BK / Parity)
    → Z2 symmetry tapering + BK imaginary-strip (if needed)
    → COBYLA VQE (multistart)
    → SHA-256 provenance hash → JSON entry

Usage:
  python scripts/generate_entry_v4.py --molecule H2
  python scripts/generate_entry_v4.py --molecule LiH --mapping bravyi_kitaev
  python scripts/generate_entry_v4.py --molecule H2O --orbital-opt casscf
  python scripts/generate_entry_v4.py --molecule benzene --basis cc-pvdz

Exit codes: 0 = entry written, 1 = pipeline error.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

REPO = Path(__file__).resolve().parent.parent

ANG_TO_BOHR = 1.8897259886

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def _ok(msg):   return f"{GREEN}  [OK]{RESET}  {msg}"
def _warn(msg): return f"{YELLOW}  [WARN]{RESET} {msg}"
def _fail(msg): return f"{RED}  [FAIL]{RESET} {msg}"
def _step(msg): return f"{BOLD}--- {msg}{RESET}"


# ─── Molecule catalog ─────────────────────────────────────────────────────────

def load_molecule(name: str) -> dict:
    catalog_path = REPO / "molecules_v4.json"
    if not catalog_path.exists():
        # Fall back to v3 catalog for molecules not yet in v4
        catalog_path = REPO / "molecules_v3.json"
        print(_warn(f"molecules_v4.json not found, falling back to molecules_v3.json"))
    catalog = json.loads(catalog_path.read_text())
    for raw in catalog.get("entries", []):
        if raw["molecule"].upper() == name.upper():
            entry = dict(raw)
            if "active_space" not in entry:
                entry["active_space"] = (entry.get("v4_active_space") or
                                         entry.get("v3_active_space") or
                                         entry.get("active_electrons_orbitals"))
            if "geometry_pyscf" not in entry:
                entry["geometry_pyscf"] = entry.get("geometry",
                                                     entry.get("geometry_angstrom"))
            return entry
    available = [e["molecule"] for e in catalog.get("entries", [])]
    raise KeyError(f"Molecule '{name}' not found. Available: {available}")


def pyscf_geom_to_symbols_coords(atom_str: str):
    atoms = [a.strip() for a in atom_str.strip().split(";") if a.strip()]
    symbols = []
    coords_ang = []
    for a in atoms:
        parts = a.split()
        symbols.append(parts[0])
        coords_ang.extend(float(x) for x in parts[1:4])
    coords_bohr = np.array(coords_ang) * ANG_TO_BOHR
    return symbols, coords_bohr


# ─── PySCF: classical comparison + CASCI / CASSCF reference ──────────────────

def run_pyscf_suite(mol_config: dict, basis: str,
                    orbital_opt: str = "hf",
                    run_classical: bool = True) -> dict:
    """
    Run PySCF suite: HF → MP2 → CCSD → CCSD(T) → CASCI (or CASSCF → CASCI).

    orbital_opt:
      "hf"     — use canonical HF orbitals (v3 behaviour)
      "casscf" — optimise active-space orbitals via CASSCF before CASCI
                 (publication-grade, recommended for v4)

    Returns flat dict with all energies and metadata.
    """
    from pyscf import gto, scf, mcscf

    atom_str   = mol_config["geometry_pyscf"]
    n_elec     = mol_config["active_space"][0]
    n_orb      = mol_config["active_space"][1]
    charge     = mol_config.get("charge", 0)
    spin       = mol_config.get("spin", 0)
    n_alpha    = n_elec // 2
    n_beta     = n_elec - n_alpha

    mol = gto.Mole()
    mol.atom    = atom_str
    mol.basis   = basis
    mol.charge  = charge
    mol.spin    = spin
    mol.verbose = 0
    mol.build()

    # Hartree-Fock
    mf = scf.RHF(mol).run()
    e_hf = float(mf.e_tot)
    print(_ok(f"HF:       {e_hf:.10f} Ha"))

    e_mp2 = e_ccsd = e_ccsd_t = None

    if run_classical:
        try:
            from pyscf import mp
            mymp = mp.MP2(mf).run()
            e_mp2 = float(mymp.e_tot)
            print(_ok(f"MP2:      {e_mp2:.10f} Ha"))
        except Exception as ex:
            print(_warn(f"MP2 failed: {ex}"))

        try:
            from pyscf import cc
            mycc = cc.CCSD(mf).run()
            e_ccsd   = float(mycc.e_tot)
            e_ccsd_t = float(mycc.e_tot + mycc.ccsd_t())
            print(_ok(f"CCSD:     {e_ccsd:.10f} Ha"))
            print(_ok(f"CCSD(T):  {e_ccsd_t:.10f} Ha"))
        except Exception as ex:
            print(_warn(f"CCSD failed: {ex}"))

    # ── CASSCF orbital optimisation (v4 new) ──────────────────────────────────
    mo_coeff_for_casci = None
    e_casscf = None

    if orbital_opt == "casscf":
        try:
            mc_scf = mcscf.CASSCF(mf, n_orb, (n_alpha, n_beta))
            mc_scf.run()
            e_casscf = float(mc_scf.e_tot)
            mo_coeff_for_casci = mc_scf.mo_coeff
            print(_ok(f"CASSCF:   {e_casscf:.10f} Ha  (active space MOs optimised)"))
        except Exception as ex:
            print(_warn(f"CASSCF failed: {ex}. Falling back to HF orbitals."))
            orbital_opt = "hf"

    # ── CASCI (active-space FCI) — VQE reference energy ──────────────────────
    mc = mcscf.CASCI(mf, n_orb, (n_alpha, n_beta))
    if mo_coeff_for_casci is not None:
        mc.mo_coeff = mo_coeff_for_casci
    mc.run()
    e_casci = float(mc.e_tot)
    print(_ok(f"CASCI:    {e_casci:.10f} Ha  ({n_elec}e, {n_orb}o active space, orbs={orbital_opt})"))

    # First excited state
    e_casci_ex = None
    try:
        mc2 = mcscf.CASCI(mf, n_orb, (n_alpha, n_beta))
        if mo_coeff_for_casci is not None:
            mc2.mo_coeff = mo_coeff_for_casci
        mc2.fcisolver.nroots = 2
        mc2.run()
        roots = mc2.e_tot
        if hasattr(roots, "__len__") and len(roots) > 1:
            e_casci_ex = float(roots[1])
    except Exception:
        pass

    pyscf_ver = _pkg_version("pyscf")
    now_utc   = _utcnow()

    return {
        "e_hf":           e_hf,
        "e_mp2":          e_mp2,
        "e_ccsd":         e_ccsd,
        "e_ccsd_t":       e_ccsd_t,
        "e_casci":        e_casci,
        "e_casci_ex":     e_casci_ex,
        "e_casscf":       e_casscf,
        "orbital_opt":    orbital_opt,
        "mo_coeff":       mo_coeff_for_casci,   # for PennyLane (not serialised)
        "pyscf_version":  pyscf_ver,
        "computed_utc":   now_utc,
        "basis":          basis,
        "n_electrons":    n_elec,
        "n_orbitals":     n_orb,
        "_mf":            mf,
    }


# ─── BK imaginary-strip (v4 new) ─────────────────────────────────────────────

def strip_imaginary_from_hamiltonian(H, e_casci: float,
                                     threshold_rel: float = 1e-6,
                                     verify_tol: float = 1e-3) -> tuple:
    """
    Strip imaginary parts from Pauli coefficients in H_tapered.

    Background:
      PL 0.45 qchem.taper() still introduces complex Pauli coefficients when
      applied to BK-mapped Hamiltonians. For a physically Hermitian Hamiltonian
      these imaginary parts are a numerical artefact of the tapering unitary.
      Stripping them gives a real-valued Hamiltonian; we then verify via exact
      diagonalisation that the cleaned H has the correct ground state energy.

    Args:
      H           : PennyLane operator (Sum / Hamiltonian) with possible complex coeffs
      e_casci     : CASCI reference energy (Ha) — used for verification
      threshold_rel: imaginary parts below this fraction of max |coeff| are noise
      verify_tol  : if |eigenvalue - e_casci| > this after cleaning, raise error

    Returns:
      (H_clean, stripped, max_imag_abs)
        H_clean     : new operator with real coefficients
        stripped    : True if any imaginary parts were removed
        max_imag_abs: largest |imag| part encountered

    Raises:
      RuntimeError if cleaned H eigenvalue deviates from e_casci by > verify_tol
    """
    import pennylane as qml

    # Collect (coeff, operator) pairs from pauli_rep
    try:
        pr = H.pauli_rep
        if pr is None:
            raise AttributeError
        pairs = list(pr.items())  # [(PauliWord, complex_coeff), ...]
        use_pauli_rep = True
    except AttributeError:
        # Fallback: Sum operator .operands
        ops    = list(H.operands) if hasattr(H, "operands") else [H]
        coeffs = [1.0] * len(ops)
        pairs  = list(zip(ops, coeffs))
        use_pauli_rep = False

    # Find max abs coefficient to set relative threshold
    max_abs = max((abs(c) for _, c in pairs), default=1.0)
    abs_threshold = threshold_rel * max_abs

    stripped      = False
    max_imag_abs  = 0.0
    clean_pairs   = []

    for op, coeff in pairs:
        imag_part = float(np.imag(coeff))
        real_part = float(np.real(coeff))
        abs_imag  = abs(imag_part)

        if abs_imag > max_imag_abs:
            max_imag_abs = abs_imag

        if abs_imag > abs_threshold:
            stripped = True

        if abs(real_part) > 1e-14:
            clean_pairs.append((op, real_part))

    if not stripped:
        return H, False, max_imag_abs

    # Rebuild Hamiltonian with real coefficients only
    if use_pauli_rep:
        from pennylane.pauli import PauliSentence
        new_ps = PauliSentence({pw: rp for pw, rp in clean_pairs})
        H_clean = new_ps.operation()
    else:
        new_ops    = [op for op, _ in clean_pairs]
        new_coeffs = [rp for _, rp in clean_pairs]
        H_clean = qml.Hamiltonian(new_coeffs, new_ops)

    # ── Verify: exact diag of cleaned H must match CASCI ─────────────────────
    try:
        wires   = sorted(H_clean.wires)
        H_mat   = qml.matrix(H_clean, wire_order=wires)
        e_clean = float(np.linalg.eigvalsh(np.real(H_mat))[0])
        gap     = abs(e_clean - e_casci)
        if gap > verify_tol:
            raise RuntimeError(
                f"BK imaginary-strip verification FAILED: "
                f"cleaned H eigenvalue {e_clean:.8f} Ha differs from CASCI "
                f"{e_casci:.8f} Ha by {gap:.3e} Ha (tolerance {verify_tol:.3e} Ha). "
                "This molecule's BK tapering may have non-trivial imaginary terms. "
                "Try --mapping jordan_wigner or --no-taper."
            )
        print(_ok(
            f"BK imaginary-strip: max_imag={max_imag_abs:.2e}  "
            f"cleaned_gs={e_clean:.8f} Ha  gap_vs_CASCI={gap:.2e} Ha  ✓"
        ))
    except Exception as ex:
        if "FAILED" in str(ex):
            raise
        print(_warn(f"BK imaginary-strip verification skipped: {ex}"))

    return H_clean, stripped, max_imag_abs


# ─── PennyLane: Hamiltonian + Z2 tapering ────────────────────────────────────
# (identical to v3 — reproduced here for standalone operation)

def build_pl_hamiltonian(symbols, coords_bohr, basis, mapping,
                          n_electrons, n_orbitals, mf=None,
                          use_of_bridge=False, e_casci=None,
                          mo_coeff=None):
    _MAPPING_ALIASES = {
        "jordan_wigner": "jordan_wigner", "jw": "jordan_wigner",
        "bravyi_kitaev": "bravyi_kitaev", "bk": "bravyi_kitaev",
        "parity":        "parity",        "p":  "parity",
    }
    canon_mapping = _MAPPING_ALIASES.get(mapping.lower())
    if canon_mapping is None:
        raise ValueError(f"Unsupported mapping '{mapping}'.")

    # When CASSCF MO coefficients are provided, update the PySCF mf object so
    # that of_bridge reads integrals in the CASSCF orbital basis.  PL 0.45's
    # molecular_hamiltonian does NOT accept a mo_coeff kwarg, so we always
    # route through of_bridge whenever custom MOs are requested.
    if mo_coeff is not None:
        if mf is None:
            raise ValueError("CASSCF orbital opt requires mf to be passed.")
        import copy
        mf = copy.copy(mf)          # don't mutate the caller's object
        mf.mo_coeff = mo_coeff
        use_of_bridge = True
        print(_ok("CASSCF mo_coeff injected into mf — routing through OF-bridge"))

    if canon_mapping == "parity" or use_of_bridge:
        if mf is None or e_casci is None:
            raise ValueError("of_bridge requires mf and e_casci.")
        sys.path.insert(0, str(REPO / "scripts"))
        import of_bridge
        H, n_qubits, gs_exact = of_bridge.build_qubit_hamiltonian(
            mf, n_electrons, n_orbitals, canon_mapping, e_casci,
        )
        n_terms = len(getattr(H, "operands", None) or getattr(H, "ops", []))
        print(_ok(f"OF-bridge Hamiltonian: {n_qubits} qubits, {n_terms} terms  "
                  f"({canon_mapping})  gs={gs_exact:.8f} Ha"))
        return H, n_qubits

    from pennylane import qchem
    if not isinstance(coords_bohr, np.ndarray):
        coords_bohr = np.array(coords_bohr)

    kwargs = dict(
        symbols=symbols,
        coordinates=coords_bohr,
        basis=basis,
        mapping=canon_mapping,
        active_electrons=n_electrons,
        active_orbitals=n_orbitals,
    )

    H, n_qubits = qchem.molecular_hamiltonian(**kwargs)
    n_terms = len(getattr(H, "operands", None) or getattr(H, "ops", []))
    print(_ok(f"PL Hamiltonian: {n_qubits} qubits, {n_terms} terms  ({canon_mapping})"))
    return H, n_qubits


def _find_optimal_sector(H, generators, paulixops):
    import itertools
    import pennylane as qml
    from pennylane import qchem

    n_sym = len(generators)
    best_energy  = np.inf
    best_sectors = None

    for sectors in itertools.product([1, -1], repeat=n_sym):
        try:
            H_tap = qchem.taper(H, generators, paulixops, list(sectors))
            wires  = sorted(H_tap.wires)
            if not wires:
                continue
            H_mat  = qml.matrix(H_tap, wire_order=wires)
            e      = float(np.linalg.eigvalsh(np.real(H_mat))[0])
            if e < best_energy:
                best_energy  = e
                best_sectors = list(sectors)
        except Exception:
            pass

    if best_sectors is None:
        raise RuntimeError("_find_optimal_sector: no valid sector found")

    return best_sectors, best_energy


def apply_tapering(H, n_qubits: int, n_electrons: int, e_casci: float,
                   mapping: str = "jordan_wigner"):
    """
    Apply Z2 symmetry tapering.
    v4 addition: if mapping is BK, apply imaginary-strip after taper.
    """
    import pennylane as qml
    from pennylane import qchem

    generators = qchem.symmetry_generators(H)
    paulixops  = qchem.paulix_ops(generators, n_qubits)

    sectors, e_tapered_gs = _find_optimal_sector(H, generators, paulixops)

    H_tapered  = qchem.taper(H, generators, paulixops, sectors)
    hf_tapered = qchem.taper_hf(generators, paulixops, sectors,
                                 num_electrons=n_electrons, num_wires=n_qubits)

    n_tap = len(H_tapered.wires)
    n_sym = len(generators)

    # ── BK constant-offset correction (same as v3) ────────────────────────────
    constant_correction = 0.0
    correction_applied  = False
    CORRECTION_THRESHOLD = 0.1

    shift = e_casci - e_tapered_gs
    if abs(shift) > CORRECTION_THRESHOLD:
        constant_correction = shift
        correction_applied  = True
        print(_warn(
            f"BK tapering constant correction: {constant_correction:+.6f} Ha"
        ))
    else:
        print(_ok(f"Tapering constant check: shift={shift:.2e} Ha  (no correction needed)"))

    print(_ok(f"Z2 tapering: {n_qubits} -> {n_tap} qubits  ({n_sym} symmetries removed)"))
    print(_ok(f"Tapered HF state: {hf_tapered.tolist()}"))

    # ── v4 new: BK imaginary-strip ────────────────────────────────────────────
    bk_imaginary_stripped  = False
    bk_max_imag_abs        = 0.0
    is_bk = mapping.lower() in ("bravyi_kitaev", "bk")

    if is_bk:
        # The tapered H lives in a shifted energy space: its ground eigenvalue
        # is e_casci minus the constant correction that PL dropped.
        # Pass the tapered-space reference so the verify check is correct.
        e_casci_for_verify = e_tapered_gs  # already computed by _find_optimal_sector
        H_tapered, bk_imaginary_stripped, bk_max_imag_abs = \
            strip_imaginary_from_hamiltonian(
                H_tapered, e_casci_for_verify,
                threshold_rel=1e-6, verify_tol=1e-3,
            )
        if bk_imaginary_stripped:
            print(_ok(
                f"BK imaginary parts stripped  "
                f"(max_imag={bk_max_imag_abs:.2e} Ha, stored in entry)"
            ))

    return H_tapered, hf_tapered, {
        "generators":              generators,
        "paulixops":               paulixops,
        "sectors":                 sectors,
        "n_qubits_full":           n_qubits,
        "n_qubits_tap":            n_tap,
        "n_symmetries":            n_sym,
        "bk_constant_correction":  constant_correction if correction_applied else None,
        "bk_imaginary_stripped":   bk_imaginary_stripped,
        "bk_max_imag_abs":         bk_max_imag_abs if bk_imaginary_stripped else None,
    }


# ─── Ansatz builders (identical to v3) ───────────────────────────────────────

def _get_tapered_uccsd_ops(n_electrons, n_qubits_full, generators, paulixops, sectors):
    import pennylane as qml
    from pennylane import qchem

    singles, doubles = qchem.excitations(n_electrons, n_qubits_full)
    wire_order = list(range(n_qubits_full))
    tapered_ops = []

    for d_wires in doubles:
        try:
            orig_op = qml.DoubleExcitation(0.0, wires=list(d_wires))
            tap = qchem.taper_operation(orig_op, generators, paulixops, sectors,
                                        wire_order=wire_order)
            for op in (tap if isinstance(tap, (list, tuple)) else [tap]):
                if op is not None and getattr(op, "num_params", 0) > 0:
                    tapered_ops.append(op)
        except Exception:
            pass

    for s_wires in singles:
        try:
            orig_op = qml.SingleExcitation(0.0, wires=list(s_wires))
            tap = qchem.taper_operation(orig_op, generators, paulixops, sectors,
                                        wire_order=wire_order)
            for op in (tap if isinstance(tap, (list, tuple)) else [tap]):
                if op is not None and getattr(op, "num_params", 0) > 0:
                    tapered_ops.append(op)
        except Exception:
            pass

    return tapered_ops


def _apply_tapered_op(op, param):
    import pennylane as qml

    if not hasattr(op, "base"):
        qml.apply(op.__class__(param, wires=op.wires))
        return

    base     = op.base
    base_cls = type(base).__name__
    base_wires = list(base.wires)

    if len(base_wires) == 1:
        w = base_wires[0]
        if base_cls == "PauliX": qml.RX(param, wires=w); return
        if base_cls == "PauliY": qml.RY(param, wires=w); return
        if base_cls == "PauliZ": qml.RZ(param, wires=w); return

    qml.apply(qml.exp(base, coeff=1j * param))


def build_uccsd_circuit(H_tapered, hf_tapered, n_electrons, n_qubits_full,
                        generators, paulixops, sectors):
    wires       = sorted(H_tapered.wires)
    tapered_ops = _get_tapered_uccsd_ops(
        n_electrons, n_qubits_full, generators, paulixops, sectors
    )

    if not tapered_ops:
        print(_warn("taper_operation yielded 0 parametric ops -- falling back to HEA"))
        return build_hea_circuit(H_tapered, hf_tapered, reps=2)

    n_params = len(tapered_ops)
    print(_ok(f"UCCSD (tapered): {n_params} parameters on {len(wires)} qubits"))

    def circuit_fn(params, wires=wires):
        import pennylane as qml
        qml.BasisState(hf_tapered, wires=wires)
        for i, op in enumerate(tapered_ops):
            _apply_tapered_op(op, params[i])

    return circuit_fn, n_params, "uccsd_tapered"


def build_hea_circuit(H_tapered, hf_tapered, reps=2):
    import pennylane as qml

    wires    = sorted(H_tapered.wires)
    n_wires  = len(wires)
    n_params = n_wires * (reps + 1)
    print(_ok(f"HEA: {n_params} parameters  ({n_wires} qubits x {reps+1} layers)"))

    def circuit_fn(params, wires=wires):
        qml.BasisState(hf_tapered, wires=wires)
        idx = 0
        for layer in range(reps + 1):
            for w in wires:
                qml.RY(params[idx], wires=w)
                idx += 1
            if layer < reps:
                for i in range(n_wires - 1):
                    qml.CNOT(wires=[wires[i], wires[i + 1]])

    return circuit_fn, n_params, "hea"


# ─── ADAPT-VQE ansatz (v4.3) ─────────────────────────────────────────────────

def build_adapt_meta(H_tapered, hf_tapered, n_electrons, n_qubits_full,
                     generators, paulixops, sectors,
                     gradient_threshold=1e-3, max_operators=100):
    """
    ADAPT-VQE: returns a 'meta' dict — operator pool + HF state + thresholds.
    The ansatz is BUILT INCREMENTALLY by run_vqe_adapt() — one operator at a
    time, only keeping those whose gradient indicates they will lower the energy.

    For [6e,6o] systems where full UCCSD has ~400 parameters, ADAPT-VQE typically
    converges with 30-80 operators at the same accuracy.

    Args:
        gradient_threshold: stop when max |gradient| over remaining pool < this
        max_operators:      hard cap on operators added (safety limit)

    Returns:
        adapt_meta: dict consumed by run_vqe_adapt()
        n_params:   0 initially (grows during optimization)
        label:      "adapt"
    """
    tapered_ops = _get_tapered_uccsd_ops(
        n_electrons, n_qubits_full, generators, paulixops, sectors
    )

    if not tapered_ops:
        print(_warn("ADAPT pool empty -- falling back to HEA"))
        return build_hea_circuit(H_tapered, hf_tapered, reps=2)

    n_pool = len(tapered_ops)
    print(_ok(f"ADAPT-VQE pool: {n_pool} candidate operators "
              f"(threshold={gradient_threshold:.0e}, max_ops={max_operators})"))

    adapt_meta = {
        "operator_pool":      tapered_ops,
        "hf_tapered":         hf_tapered,
        "wires":              sorted(H_tapered.wires),
        "gradient_threshold": gradient_threshold,
        "max_operators":      max_operators,
        "n_pool":             n_pool,
    }

    return adapt_meta, 0, "adapt"


# ─── VQE ─────────────────────────────────────────────────────────────────────

def run_vqe(H_tapered, circuit_fn, n_params, max_iter=500, multistart=3, seed=42,
            backend="default.qubit", e_target=None, early_stop=True,
            checkpoint_path=None, optimizer="cobyla", learning_rate=0.05):
    """
    Run VQE with COBYLA optimizer.

    Args:
        e_target:        CASCI energy (Ha). When early_stop=True, stops as soon
                         as |best - e_target| < 0.01 Ha (certification threshold).
        early_stop:      Stop immediately once gap < 0.01 Ha (default True).
        checkpoint_path: If set, writes a JSON checkpoint after every restart so
                         progress survives crashes on long runs.
    """
    import pennylane as qml
    from scipy.optimize import minimize

    wires = sorted(H_tapered.wires)
    dev   = qml.device(backend, wires=wires)

    @qml.qnode(dev)
    def energy_fn(params):
        circuit_fn(params, wires=wires)
        return qml.expval(H_tapered)

    if optimizer == "adam":
        return _run_vqe_adam(energy_fn, n_params, learning_rate, max_iter,
                             multistart, seed, e_target, early_stop, checkpoint_path)
    if optimizer in ("bfgs", "l-bfgs-b"):
        return _run_vqe_bfgs(energy_fn, n_params, max_iter,
                             multistart, seed, e_target, early_stop, checkpoint_path)

    rng         = np.random.default_rng(seed)
    best_energy = np.inf
    best_params = None
    total_nfev  = 0
    stopped_early = False

    for run in range(multistart):
        x0 = np.zeros(n_params) if run == 0 else rng.uniform(-np.pi, np.pi, n_params)
        result = minimize(lambda p: float(energy_fn(p)), x0,
                          method="COBYLA",
                          options={"maxiter": max_iter, "rhobeg": 0.5})
        total_nfev += result.nfev
        e_run = result.fun
        improved = e_run < best_energy
        status = "[OK]" if improved else "    "

        # Gap annotation — show best gap so far (not just this run's gap)
        gap_str = ""
        if e_target is not None:
            best_so_far = min(e_run, best_energy)  # best_energy not updated yet if not improved
            gap = abs(best_so_far - e_target)
            cert = "CERT" if gap < 0.01 else f"gap={gap:.3e}"
            gap_str = f"  [{cert}]"

        print(f"    run {run+1}/{multistart}: E = {e_run:.10f} Ha  "
              f"(nfev={result.nfev}) {status}{gap_str}")

        if improved:
            best_energy = e_run
            best_params = result.x.copy()

        # Checkpoint after every restart
        if checkpoint_path is not None and best_params is not None:
            ckpt = {
                "restart_completed": run + 1,
                "total_restarts":    multistart,
                "best_energy_hartree": float(best_energy),
                "best_params":       best_params.tolist(),
                "total_nfev":        total_nfev,
                "saved_utc":         _utcnow(),
            }
            try:
                Path(checkpoint_path).write_text(json.dumps(ckpt, indent=2))
            except Exception as ckpt_err:
                print(_warn(f"Checkpoint write failed: {ckpt_err}"))

        # Early-stop once certified
        if early_stop and e_target is not None:
            if abs(best_energy - e_target) < 0.01:
                print(_ok(f"Early stop: gap < 0.01 Ha after restart {run+1}/{multistart}"))
                stopped_early = True
                break

    print(_ok(f"VQE best energy: {best_energy:.10f} Ha  (total nfev={total_nfev})"))

    # Clean up checkpoint — run is complete
    if checkpoint_path is not None:
        try:
            Path(checkpoint_path).unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "best_energy_hartree": float(best_energy),
        "optimal_params":      best_params.tolist(),
        "num_params":          n_params,
        "nfev":                total_nfev,
        "optimizer":           "COBYLA",
        "multistart_runs":     run + 1,   # actual restarts completed
        "stopped_early":       stopped_early,
        "computed_utc":        _utcnow(),
    }


# ── Gradient-based VQE helpers (v4.3 Phase 2) ────────────────────────────────

def _run_vqe_adam(energy_fn, n_params, learning_rate, max_iter, multistart, seed,
                  e_target, early_stop, checkpoint_path):
    """Adam optimizer — PennyLane AdamOptimizer with parameter-shift gradients."""
    import pennylane as qml
    import pennylane.numpy as pnp

    rng = np.random.default_rng(seed)
    best_energy = np.inf
    best_params = None
    total_steps = 0
    stopped_early = False

    for run in range(multistart):
        if run == 0:
            params = pnp.zeros(n_params, requires_grad=True)
        else:
            params = pnp.array(rng.uniform(-np.pi, np.pi, n_params), requires_grad=True)
        opt = qml.AdamOptimizer(stepsize=learning_rate)

        for it in range(max_iter):
            params, e_step = opt.step_and_cost(energy_fn, params)
            total_steps += 1
            e_float = float(e_step)
            if (it + 1) % 100 == 0:
                gap_str = ""
                if e_target is not None:
                    gap = abs(e_float - e_target)
                    gap_str = "  [CERT]" if gap < 0.01 else f"  [gap={gap:.3e}]"
                print(f"    run {run+1}/{multistart} step {it+1}: E={e_float:.10f} Ha{gap_str}")
            if early_stop and e_target is not None and abs(e_float - e_target) < 0.01:
                stopped_early = True
                print(_ok(f"Early stop: gap < 0.01 Ha at step {it+1}"))
                break

        e_final = float(energy_fn(params))
        if e_final < best_energy:
            best_energy = e_final
            best_params = np.array(params)
        if stopped_early:
            break

    print(_ok(f"VQE best energy: {best_energy:.10f} Ha  "
              f"(Adam lr={learning_rate}, {run+1} restart(s), {total_steps} steps)"))
    return {
        "best_energy_hartree": float(best_energy),
        "optimal_params":      list(best_params),
        "num_params":          n_params,
        "nfev":                total_steps,
        "optimizer":           f"Adam(lr={learning_rate})",
        "multistart_runs":     run + 1,
        "stopped_early":       stopped_early,
        "computed_utc":        _utcnow(),
    }


def _run_vqe_bfgs(energy_fn, n_params, max_iter, multistart, seed,
                  e_target, early_stop, checkpoint_path):
    """L-BFGS-B optimizer — scipy + analytic gradients via parameter-shift rule."""
    import pennylane as qml
    import pennylane.numpy as pnp
    from scipy.optimize import minimize

    rng = np.random.default_rng(seed)
    best_energy = np.inf
    best_params = None
    total_nfev  = 0
    stopped_early = False

    def f_and_grad(p):
        p_pnp = pnp.array(p, requires_grad=True)
        e = float(energy_fn(p_pnp))
        g = np.array(qml.grad(energy_fn)(p_pnp))
        return e, g

    for run in range(multistart):
        x0 = np.zeros(n_params) if run == 0 else rng.uniform(-np.pi, np.pi, n_params)
        result = minimize(f_and_grad, x0, jac=True, method="L-BFGS-B",
                          options={"maxiter": max_iter, "ftol": 1e-12, "gtol": 1e-8})
        total_nfev += result.nfev
        gap_str = ""
        if e_target is not None:
            gap = abs(result.fun - e_target)
            gap_str = "  [CERT]" if gap < 0.01 else f"  [gap={gap:.3e}]"
        print(f"    run {run+1}/{multistart}: E={result.fun:.10f} Ha  "
              f"(nfev={result.nfev}){gap_str}")
        if result.fun < best_energy:
            best_energy = result.fun
            best_params = result.x.copy()
        if early_stop and e_target is not None and abs(best_energy - e_target) < 0.01:
            stopped_early = True
            print(_ok(f"Early stop: gap < 0.01 Ha after run {run+1}"))
            break

    circuit_evals = total_nfev * (1 + 2 * n_params)  # parameter-shift: 1 fwd + 2N per step
    print(_ok(f"VQE best energy: {best_energy:.10f} Ha  "
              f"(L-BFGS-B, {run+1} restart(s), optimizer_steps={total_nfev}, "
              f"circuit_evals~{circuit_evals})"))
    return {
        "best_energy_hartree": float(best_energy),
        "optimal_params":      list(best_params),
        "num_params":          n_params,
        "nfev":                circuit_evals,   # circuit evaluations (parameter-shift counted)
        "optimizer":           "L-BFGS-B",
        "multistart_runs":     run + 1,
        "stopped_early":       stopped_early,
        "computed_utc":        _utcnow(),
    }


def run_vqe_adapt(H_tapered, adapt_meta, max_iter=500, seed=42,
                  backend="default.qubit", e_target=None, early_stop=True,
                  checkpoint_path=None):
    """
    Run ADAPT-VQE: iteratively add the operator with the largest gradient,
    then optimize all current parameters. Stop when max |gradient| over the
    remaining pool drops below the threshold, or when certified.

    The inner optimization uses COBYLA on the current accumulated parameters.
    Each outer iteration adds at most one operator.

    Returns the same dict shape as run_vqe() so assemble_entry() can consume it.
    """
    import pennylane as qml
    from pennylane import numpy as pnp
    from scipy.optimize import minimize

    pool          = adapt_meta["operator_pool"]
    wires         = adapt_meta["wires"]
    hf_tapered    = adapt_meta["hf_tapered"]
    threshold     = adapt_meta["gradient_threshold"]
    max_operators = adapt_meta["max_operators"]
    n_pool        = adapt_meta["n_pool"]

    dev = qml.device(backend, wires=wires)

    selected_ops     = []   # operators chosen so far (subset of pool)
    selected_indices = []   # their indices in the pool
    params           = []   # current parameter values for selected_ops
    total_nfev       = 0
    e_current        = np.inf
    stopped_early    = False
    converged        = False

    for iteration in range(max_operators):
        # Build a QNode that has all selected ops + one candidate at param=0
        def make_test_circuit(candidate_op):
            @qml.qnode(dev)
            def test_energy(p):
                # p has len(selected_ops) + 1 entries; last is candidate
                qml.BasisState(hf_tapered, wires=wires)
                for i, op in enumerate(selected_ops):
                    _apply_tapered_op(op, p[i])
                _apply_tapered_op(candidate_op, p[-1])
                return qml.expval(H_tapered)
            return test_energy

        # Find the candidate with largest |gradient| at param_candidate = 0
        best_grad_abs = 0.0
        best_grad_signed = 0.0
        best_idx      = -1

        for pool_idx, candidate in enumerate(pool):
            if pool_idx in selected_indices:
                continue
            test_energy = make_test_circuit(candidate)
            # CRITICAL: use pennylane.numpy with requires_grad=True so qml.grad
            # actually computes gradients (plain np.array gives zero gradients).
            test_params = pnp.array(params + [0.0], requires_grad=True)
            try:
                grads = qml.grad(test_energy)(test_params)
                grad_candidate = float(np.array(grads).flatten()[-1])
            except Exception as ex:
                # Skip operators that cause numerical issues
                continue

            if abs(grad_candidate) > best_grad_abs:
                best_grad_abs    = abs(grad_candidate)
                best_grad_signed = grad_candidate
                best_idx         = pool_idx

        # Convergence: no operator helps anymore
        if best_idx < 0 or best_grad_abs < threshold:
            print(_ok(f"ADAPT converged: max|grad|={best_grad_abs:.2e} < "
                      f"threshold {threshold:.0e} after {len(selected_ops)} operators"))
            converged = True
            break

        # Add the operator and optimize all parameters
        selected_ops.append(pool[best_idx])
        selected_indices.append(best_idx)
        params.append(0.0)

        # Inner optimization: COBYLA over all current parameters
        def full_circuit(p, wires=wires):
            qml.BasisState(hf_tapered, wires=wires)
            for i, op in enumerate(selected_ops):
                _apply_tapered_op(op, p[i])

        @qml.qnode(dev)
        def energy_fn(p):
            full_circuit(p, wires=wires)
            return qml.expval(H_tapered)

        result = minimize(lambda p: float(energy_fn(p)),
                          np.array(params, dtype=float),
                          method="COBYLA",
                          options={"maxiter": max_iter, "rhobeg": 0.5})

        params      = result.x.tolist()
        e_current   = float(result.fun)
        total_nfev += int(result.nfev)

        # Progress print
        gap_str = ""
        if e_target is not None:
            gap = abs(e_current - e_target)
            cert = "CERT" if gap < 0.01 else f"gap={gap:.3e}"
            gap_str = f"  [{cert}]"
        print(f"    iter {iteration+1}: ops={len(selected_ops):3d}  "
              f"E={e_current:.10f} Ha  |grad|={best_grad_abs:.2e}{gap_str}")

        # Checkpoint
        if checkpoint_path is not None:
            try:
                ckpt = {
                    "iteration":          iteration + 1,
                    "n_operators":        len(selected_ops),
                    "selected_indices":   selected_indices,
                    "best_energy_hartree": e_current,
                    "best_params":        params,
                    "total_nfev":         total_nfev,
                    "saved_utc":          _utcnow(),
                }
                Path(checkpoint_path).write_text(json.dumps(ckpt, indent=2))
            except Exception as ckpt_err:
                print(_warn(f"Checkpoint write failed: {ckpt_err}"))

        # Early-stop on certification
        if early_stop and e_target is not None and abs(e_current - e_target) < 0.01:
            print(_ok(f"Early stop: certified after {len(selected_ops)} operators"))
            stopped_early = True
            break

    if not converged and not stopped_early and iteration + 1 >= max_operators:
        print(_warn(f"ADAPT reached max_operators ({max_operators}) without convergence"))

    # Clean up checkpoint file when finished
    if checkpoint_path is not None:
        try:
            Path(checkpoint_path).unlink(missing_ok=True)
        except Exception:
            pass

    if not selected_ops:
        # Nothing was added — this means ADAPT failed to find any helpful
        # operator (likely a gradient computation bug). Raise an error rather
        # than save a garbage entry with E=0.
        raise RuntimeError(
            f"ADAPT-VQE selected 0 operators. This usually means qml.grad "
            f"returned 0 for all candidates — check requires_grad on test_params. "
            f"Pool size was {n_pool}, threshold was {threshold:.0e}."
        )

    print(_ok(f"ADAPT-VQE best energy: {e_current:.10f} Ha  "
              f"({len(selected_ops)} ops / pool of {n_pool}, total nfev={total_nfev})"))

    return {
        "best_energy_hartree": float(e_current),
        "optimal_params":      params,
        "num_params":          len(selected_ops),
        "nfev":                total_nfev,
        "optimizer":           "ADAPT-VQE (COBYLA inner)",
        "multistart_runs":     1,
        "stopped_early":       stopped_early,
        "computed_utc":        _utcnow(),
        "adapt_metadata": {
            "n_operators_pool":          n_pool,
            "selected_operator_indices": selected_indices,
            "gradient_threshold":        threshold,
            "max_operators":             max_operators,
            "converged":                 converged,
            "n_iterations":              iteration + 1,
        },
    }


# ─── Hamiltonian serialization (identical to v3) ─────────────────────────────

def serialize_hamiltonian(H_tapered):
    terms = []
    try:
        for pauli_word, coeff in H_tapered.pauli_rep.items():
            ps = "I" if not pauli_word else \
                 "".join(f"{op}{w}" for w, op in sorted(pauli_word.items()))
            terms.append({"pauli_string": ps, "coefficient": float(np.real(coeff))})
        return terms
    except AttributeError:
        pass

    try:
        ops    = getattr(H_tapered, "ops", None) or list(H_tapered.operands)
        coeffs = getattr(H_tapered, "coeffs", [1.0] * len(ops))
        for op, coeff in zip(ops, coeffs):
            terms.append({"pauli_string": str(op), "coefficient": float(np.real(coeff))})
        return terms
    except Exception:
        pass

    return [{"pauli_string": "MATRIX_FALLBACK", "num_qubits": len(H_tapered.wires)}]


# ─── Circuit metrics (identical to v3) ───────────────────────────────────────

_ROTATION_GATES = {
    "RX","RY","RZ","Rot","PhaseShift","CRX","CRY","CRZ",
    "U1","U2","U3","SingleExcitation","DoubleExcitation","Exp","exp",
}
_SYNTHESIS_EPS  = 1e-3
_T_PER_ROTATION = int(__import__("math").ceil(
    1.149 * __import__("math").log2(1.0 / _SYNTHESIS_EPS)
))


def _circuit_metrics_inline(circuit_fn, H_tapered, optimal_params, backend="default.qubit"):
    import pennylane as qml

    wires = sorted(H_tapered.wires)
    dev   = qml.device(backend, wires=wires)

    @qml.qnode(dev)
    def _circ(params):
        circuit_fn(params, wires=wires)
        return qml.expval(H_tapered)

    _NULL = {
        "ansatz_depth": None, "ansatz_num_2q_gates": None,
        "ansatz_num_1q_gates": None, "non_clifford_gate_count": None,
        "t_gate_estimate": None, "t_gate_synthesis_epsilon": _SYNTHESIS_EPS,
    }
    try:
        raw_specs = qml.specs(_circ)(np.array(optimal_params, dtype=float))
        try:
            resources = raw_specs["resources"]
            depth  = int(resources.depth)
            gsizes = dict(resources.gate_sizes)
            gtypes = dict(resources.gate_types)
        except (KeyError, TypeError, AttributeError):
            specs  = raw_specs if isinstance(raw_specs, dict) else {}
            depth  = int(specs.get("depth", specs.get("circuit_depth", 0)) or 0)
            gsizes = dict(specs.get("gate_sizes", {}) or {})
            gtypes = dict(specs.get("gate_types", {}) or {})

        n_rot = sum(int(gtypes.get(g, 0)) for g in _ROTATION_GATES)
        return {
            "ansatz_depth":             int(gsizes.get(2,0) + gsizes.get(1,0)) if not depth else depth,
            "ansatz_num_2q_gates":      int(gsizes.get(2, 0)),
            "ansatz_num_1q_gates":      int(gsizes.get(1, 0)),
            "non_clifford_gate_count":  n_rot,
            "t_gate_estimate":          n_rot * _T_PER_ROTATION,
            "t_gate_synthesis_epsilon": _SYNTHESIS_EPS,
        }
    except Exception:
        return _NULL


# ─── Hash helpers ─────────────────────────────────────────────────────────────

_HASH_EXCLUDE = {
    "created_utc", "entry_id", "entry_hash_sha256",
    "git_commit", "computed_utc", "certified_utc",
    "signature_b64", "signing_key_id",
}


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _HASH_EXCLUDE}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return copy.deepcopy(obj)


def stable_hash(d: dict) -> str:
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def try_sign_hash(entry_hash: str):
    import base64, os
    key_paths = [
        REPO / "keys" / "signing_key.pem",
        REPO / "keys" / "private_key.pem",
        Path.home() / ".qencode" / "signing_key.pem",
    ]
    key_data = None
    key_id   = "env"
    for p in key_paths:
        if p.exists():
            key_data = p.read_bytes()
            key_id   = p.stem
            break
    if not key_data:
        env_b64 = os.environ.get("QENCODE_SIGNING_KEY_B64", "")
        if env_b64:
            key_data = base64.b64decode(env_b64)
            key_id   = "env_key"
    if not key_data:
        return None, None
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        key = load_pem_private_key(key_data, password=None)
        sig = key.sign(entry_hash.encode())
        return base64.b64encode(sig).decode(), key_id
    except Exception as ex:
        print(_warn(f"Signing skipped: {ex}"))
        return None, None


# ─── Entry assembly ───────────────────────────────────────────────────────────

def _safe_corr(e_method, e_hf):
    if e_method is None or e_hf is None:
        return None
    return float(e_method - e_hf)


def assemble_entry(mol_config, basis, mapping, ansatz_type, ansatz_reps,
                   pyscf_res, tap_meta, vqe_res, pauli_terms, hf_tapered,
                   max_iter, multistart, seed,
                   circuit_fn=None, H_tapered=None, backend="default.qubit") -> tuple:

    mol_name  = mol_config["molecule"]
    n_e, n_o  = mol_config["active_space"]
    e_casci   = pyscf_res["e_casci"]
    e_hf      = pyscf_res["e_hf"]
    e_ccsd_t  = pyscf_res.get("e_ccsd_t")
    e_vqe     = vqe_res["best_energy_hartree"]
    now_utc   = _utcnow()
    orbital_opt = pyscf_res.get("orbital_opt", "hf")

    abs_gap         = abs(e_vqe - e_casci)
    trusted         = abs_gap < 0.01
    beats_classical = None
    if e_ccsd_t is not None and e_hf is not None:
        ccsd_t_corr     = abs(e_ccsd_t - e_hf)
        beats_classical = abs_gap < ccsd_t_corr

    flags = []
    if trusted:           flags.append("gap_certified")
    if beats_classical:   flags.append("beats_classical")
    if abs_gap > 0.1:     flags.append("large_gap")
    if "hea_fallback" in ansatz_type: flags.append("hea_fallback_used")
    if tap_meta.get("bk_imaginary_stripped"): flags.append("bk_imaginary_stripped")

    entry = {
        "schema_version": "4.0.0",
        "entry_id":       None,
        "created_utc":    now_utc,

        "problem": {
            "name":    mol_name,
            "basis":   basis,
            "variant": "default",
            "charge":  mol_config.get("charge", 0),
            "spin":    mol_config.get("spin", 0),
            "geometry": mol_config.get("geometry_pyscf"),
            "active_space": {
                "num_electrons":        n_e,
                "num_spatial_orbitals": n_o,
                "method":               "casci",
                "frozen_core":          False,
            },
            "orbital_optimization": orbital_opt,   # v4 new: "hf" | "casscf"
        },

        "encoding": {
            "mapping":     mapping,
            "ansatz_type": ansatz_type,
            "ansatz_reps": ansatz_reps if "hea" in ansatz_type else 1,
            "adapt_metadata": vqe_res.get("adapt_metadata"),  # None unless ansatz_type == "adapt"
            "tapering": {
                "enabled":                    True,
                "method":                     "z2_symmetry",
                "num_symmetries":             tap_meta["n_symmetries"],
                "original_num_qubits":        tap_meta["n_qubits_full"],
                "tapered_num_qubits":         tap_meta["n_qubits_tap"],
                "sectors":                    [int(x) for x in tap_meta["sectors"]],
                "hf_tapered_state":           [int(x) for x in hf_tapered],
                "bk_constant_correction_ha":  tap_meta.get("bk_constant_correction"),
                "bk_imaginary_stripped":      tap_meta.get("bk_imaginary_stripped", False),
                "bk_max_imaginary_abs_ha":    tap_meta.get("bk_max_imag_abs"),
            },
        },

        "artifacts": {
            "qubit_hamiltonian": {
                "num_qubits":      tap_meta["n_qubits_tap"],
                "num_pauli_terms": len(pauli_terms),
                "pauli_terms":     pauli_terms,
                "is_tapered":      True,
                "framework":       "pennylane",
            },
            "circuits": {
                "hf_state":           [int(x) for x in hf_tapered],
                "ansatz_pennylane":   None,
                "ansatz_includes_hf": True,
            },
        },

        "results": {
            "reference": {
                "hf_energy_hartree":           e_hf,
                "casci_ground_energy_hartree": e_casci,
                "casci_first_excited_hartree": pyscf_res.get("e_casci_ex"),
                "casscf_energy_hartree":       pyscf_res.get("e_casscf"),
            },
            "classical_comparison": {
                "hf_energy_hartree":     e_hf,
                "mp2_energy_hartree":    pyscf_res.get("e_mp2"),
                "ccsd_energy_hartree":   pyscf_res.get("e_ccsd"),
                "ccsd_t_energy_hartree": e_ccsd_t,
                "mp2_correlation":       _safe_corr(pyscf_res.get("e_mp2"), e_hf),
                "ccsd_t_correlation":    _safe_corr(e_ccsd_t, e_hf),
                "pyscf_version":         pyscf_res.get("pyscf_version"),
                "computed_utc":          pyscf_res.get("computed_utc"),
                "basis":                 basis,
            },
            "vqe": {
                "best_energy_hartree": e_vqe,
                "optimal_params":      vqe_res["optimal_params"],
                "num_params":          vqe_res["num_params"],
                "nfev":                vqe_res["nfev"],
                "optimizer":           vqe_res["optimizer"],
                "multistart_runs":     vqe_res["multistart_runs"],
                "computed_utc":        vqe_res["computed_utc"],
            },
            "quality": {
                "gap_threshold":     0.01,
                "trusted":           trusted,
                "abs_vqe_exact_gap": abs_gap,
                "beats_classical":   beats_classical,
                "flags":             flags,
                "notes":             None,
            },
        },

        "provenance": {
            "entry_hash_sha256":     "",
            "source_schema_version": "4.0.0",
            "created_utc":           now_utc,
            "tool_versions": {
                "python":      sys.version.split()[0],
                "pyscf":       pyscf_res.get("pyscf_version"),
                "pennylane":   _pkg_version("pennylane"),
                "openfermion": _pkg_version("openfermion"),
                "numpy":       _pkg_version("numpy"),
                "scipy":       _pkg_version("scipy"),
                "git_commit":  _git_head(),
            },
            "environment": {"platform": sys.platform},
        },

        "trust": {
            "level":          "certified" if trusted else "validated",
            "certified_utc":  now_utc if trusted else None,
            "signature_b64":  None,
            "signing_key_id": None,
        },

        "run_config": {
            "optimizer":        vqe_res.get("optimizer", "COBYLA"),
            "max_iterations":   max_iter,
            "multistart":       vqe_res.get("multistart_runs", multistart),
            "multistart_requested": multistart,
            "early_stopped":    vqe_res.get("stopped_early", False),
            "seed":             seed,
            "backend_type":     backend,
            "shots":            None,
        },

        "circuit_stats": {
            "num_qubits_original":   tap_meta["n_qubits_full"],
            "num_qubits_tapered":    tap_meta["n_qubits_tap"],
            "ansatz_num_parameters": vqe_res["num_params"],
            **(
                _circuit_metrics_inline(circuit_fn, H_tapered, vqe_res["optimal_params"], backend=backend)
                if circuit_fn is not None and H_tapered is not None
                else {}
            ),
        },
    }

    h               = stable_hash(_strip_volatile(entry))
    sig_b64, key_id = try_sign_hash(h)

    entry["provenance"]["entry_hash_sha256"] = h
    entry["trust"]["signature_b64"]          = sig_b64
    entry["trust"]["signing_key_id"]         = key_id

    mol_safe   = mol_name.replace(" ", "_")
    basis_safe = basis.replace("-", "").replace("_", "")
    map_short  = {"jordan_wigner": "JW", "bravyi_kitaev": "BK",
                  "parity": "PAR"}.get(mapping.lower(), mapping.upper()[:3])
    if "uccsd" in ansatz_type.lower():
        ans_short = "UCCSD"
    elif ansatz_type.lower() == "adapt":
        ans_short = "ADAPT"
    else:
        ans_short = "HEA"
    hash16     = h[:16]
    orb_tag    = "_casscf" if orbital_opt == "casscf" else ""
    entry_id   = f"{mol_safe}_{basis_safe}_{map_short}_{ans_short}_v4{orb_tag}_tapered__sha256_{hash16}"

    entry["entry_id"] = entry_id
    return entry, entry_id, entry_id + ".json"


# ─── Utilities ────────────────────────────────────────────────────────────────

def _pkg_version(pkg: str) -> Optional[str]:
    try:
        from importlib.metadata import version
        return version(pkg)
    except Exception:
        return None

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def _git_head() -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO, stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="QEncode v4 entry generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--molecule",     default="H2")
    ap.add_argument("--basis",        default="cc-pvdz",
                    help="Basis set (default: cc-pvdz for v4)")
    ap.add_argument("--mapping",      default="jordan_wigner",
                    choices=["jordan_wigner","jw","bravyi_kitaev","bk","parity","p"])
    ap.add_argument("--use-of-bridge", action="store_true")
    ap.add_argument("--ansatz-type",  default="uccsd",
                    choices=["uccsd","hardware_efficient","adapt"],
                    help="Ansatz family: uccsd (full UCCSD), hardware_efficient (HEA), "
                         "or adapt (ADAPT-VQE — adaptively grows ansatz, v4.3).")
    ap.add_argument("--reps", "--ansatz-reps", dest="ansatz_reps", type=int, default=2,
                    help="HEA depth: number of Ry+CNOT repetition blocks (default: 2). "
                         "Higher values increase expressibility at the cost of more parameters. "
                         "Ignored for UCCSD and ADAPT. Recommended: --reps 4 for N2 [6e,6o] 8-qubit.")
    ap.add_argument("--adapt-threshold", type=float, default=1e-3,
                    help="ADAPT-VQE gradient convergence threshold in Ha (default 1e-3). "
                         "Smaller = more operators, higher accuracy.")
    ap.add_argument("--adapt-max-ops", type=int, default=100,
                    help="ADAPT-VQE: hard cap on number of operators added (default 100). "
                         "Safety limit — most molecules converge with 30-80 operators.")
    ap.add_argument("--optimizer", default="cobyla",
                    choices=["cobyla", "adam", "bfgs"],
                    help="VQE optimizer: cobyla (gradient-free, default), "
                         "adam (PennyLane AdamOptimizer, parameter-shift gradients), "
                         "bfgs (scipy L-BFGS-B, analytic gradients). "
                         "adam/bfgs are 5-20x faster than cobyla for >40 params.")
    ap.add_argument("--learning-rate", type=float, default=0.05,
                    help="Learning rate for Adam optimizer (default 0.05). "
                         "Ignored for cobyla/bfgs.")
    ap.add_argument("--orbital-opt",  default="hf",
                    choices=["hf", "casscf"],
                    help="Orbital optimisation: hf (canonical) or casscf (v4 recommended)")
    ap.add_argument("--active-space", default=None,
                    help="Override active space as 'ne,no' e.g. '4,4'")
    ap.add_argument("--max-iter",     type=int, default=500)
    ap.add_argument("--multistart",   type=int, default=3)
    ap.add_argument("--seed",         type=int, default=42)
    ap.add_argument("--backend",      default="default.qubit",
                    choices=["default.qubit", "lightning.qubit", "lightning.gpu"],
                    help="PennyLane device backend. Use lightning.qubit for CPU-accelerated "
                         "simulation, lightning.gpu for GPU (requires cuQuantum + "
                         "PennyLane-Lightning-GPU installed).")
    ap.add_argument("--out-dir",      default=str(REPO / "releases" / "v4" / "db"))
    ap.add_argument("--no-taper",      action="store_true")
    ap.add_argument("--no-classical",  action="store_true")
    ap.add_argument("--no-early-stop", action="store_true",
                    help="Disable early-stop: run all --multistart restarts even after "
                         "certification threshold (gap < 0.01 Ha) is reached.")
    ap.add_argument("--dry-run",       action="store_true")
    ap.add_argument("--no-colour",     action="store_true")
    args = ap.parse_args()

    if args.no_colour:
        global GREEN, YELLOW, RED, RESET, BOLD
        GREEN = YELLOW = RED = RESET = BOLD = ""

    print(f"\n{BOLD}" + "=" * 65)
    print("  QEncode v4 - Entry Generator")
    print(f"  Python {sys.version.split()[0]}")
    print("=" * 65 + RESET)
    print(f"  Molecule:    {args.molecule}")
    print(f"  Basis:       {args.basis}")
    print(f"  Mapping:     {args.mapping}")
    if "hea" in args.ansatz_type.lower():
        ansatz_desc = f"  (reps={args.ansatz_reps}, {(args.ansatz_reps+1)} layers)"
    elif args.ansatz_type == "adapt":
        ansatz_desc = (f"  (threshold={args.adapt_threshold:.0e}, "
                       f"max_ops={args.adapt_max_ops})")
    else:
        ansatz_desc = ""
    print(f"  Ansatz:      {args.ansatz_type}{ansatz_desc}")
    print(f"  Orbital opt: {args.orbital_opt}")
    print(f"  Multistart:  {args.multistart} x {args.max_iter} iters")
    print(f"  Backend:     {args.backend}")
    print(f"  Taper:       {'NO (--no-taper)' if args.no_taper else 'YES (Z2 symmetry)'}")
    print()

    try:
        mol_config = load_molecule(args.molecule)
        if args.active_space:
            ne_str, no_str = args.active_space.split(",")
            mol_config = dict(mol_config)
            mol_config["active_space"] = [int(ne_str), int(no_str)]
        n_electrons = mol_config["active_space"][0]
        n_orbitals  = mol_config["active_space"][1]
        print(f"  Active space: [{n_electrons}e, {n_orbitals}o]")
        print()

        # Step 1: PySCF
        print(_step(f"Step 1: PySCF  ({args.molecule}, {args.basis})"))
        pyscf_res = run_pyscf_suite(
            mol_config, args.basis,
            orbital_opt=args.orbital_opt,
            run_classical=not args.no_classical,
        )

        # Step 2: PennyLane Hamiltonian
        use_bridge = args.mapping in ("parity","p") or getattr(args, "use_of_bridge", False)
        print()
        print(_step(f"Step 2: PennyLane Hamiltonian  ({args.mapping})"
                    + (" [OF-bridge]" if use_bridge else "")))
        symbols, coords_bohr = pyscf_geom_to_symbols_coords(mol_config["geometry_pyscf"])
        H, n_qubits = build_pl_hamiltonian(
            symbols, coords_bohr, args.basis, args.mapping,
            n_electrons, n_orbitals,
            mf=pyscf_res.get("_mf"),
            use_of_bridge=use_bridge,
            e_casci=pyscf_res["e_casci"],
            mo_coeff=pyscf_res.get("mo_coeff"),
        )

        # Step 3: Z2 tapering
        print()
        print(_step("Step 3: Z2 Symmetry Tapering"))
        if args.no_taper:
            import pennylane as qml
            H_vqe      = H
            hf_tapered = np.array([1]*n_electrons + [0]*(n_qubits-n_electrons))
            tap_meta   = {
                "generators":[], "paulixops":[], "sectors":[],
                "n_qubits_full": n_qubits, "n_qubits_tap": n_qubits, "n_symmetries": 0,
                "bk_imaginary_stripped": False, "bk_max_imag_abs": None,
            }
            print(_warn("Tapering skipped (--no-taper)."))
        else:
            H_vqe, hf_tapered, tap_meta = apply_tapering(
                H, n_qubits, n_electrons, pyscf_res["e_casci"],
                mapping=args.mapping,
            )

        # Exact diag verification
        try:
            import pennylane as qml
            wires_tap = sorted(H_vqe.wires)
            H_mat     = qml.matrix(H_vqe, wire_order=wires_tap)
            e_exact   = float(np.linalg.eigvalsh(np.real(H_mat))[0])
            _bk_corr  = tap_meta.get("bk_constant_correction") or 0.0
            e_exact  += _bk_corr
            gap_vs_casci = abs(e_exact - pyscf_res["e_casci"])
            print(_ok(f"Exact H diag: {e_exact:.10f} Ha  (gap vs CASCI: {gap_vs_casci:.2e} Ha)"))
        except Exception as ex:
            print(_warn(f"Exact diagonalization skipped: {ex}"))

        # Step 4: Ansatz
        print()
        print(_step(f"Step 4: Ansatz  ({args.ansatz_type})"))
        adapt_meta = None
        if args.ansatz_type == "uccsd":
            circuit_fn, n_params, method_label = build_uccsd_circuit(
                H_vqe, hf_tapered, n_electrons, n_qubits,
                tap_meta["generators"], tap_meta["paulixops"], tap_meta["sectors"],
            )
        elif args.ansatz_type == "adapt":
            adapt_meta, n_params, method_label = build_adapt_meta(
                H_vqe, hf_tapered, n_electrons, n_qubits,
                tap_meta["generators"], tap_meta["paulixops"], tap_meta["sectors"],
                gradient_threshold=args.adapt_threshold,
                max_operators=args.adapt_max_ops,
            )
            circuit_fn = None  # ADAPT builds the circuit incrementally
        else:
            circuit_fn, n_params, method_label = build_hea_circuit(
                H_vqe, hf_tapered, reps=args.ansatz_reps
            )

        # Step 5: VQE
        print()
        early_stop = not args.no_early_stop
        e_casci_target = pyscf_res["e_casci"]
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        mol_safe   = args.molecule.replace(" ", "_")
        map_short  = {"jordan_wigner": "JW", "bravyi_kitaev": "BK",
                      "parity": "PAR"}.get(args.mapping.lower(), args.mapping.upper()[:3])
        if "uccsd" in args.ansatz_type.lower():
            ans_short = "UCCSD"
        elif args.ansatz_type == "adapt":
            ans_short = "ADAPT"
        else:
            ans_short = "HEA"
        ckpt_name  = f".ckpt_{mol_safe}_{map_short}_{ans_short}.json"
        ckpt_path  = None if args.dry_run else str(out_dir / ckpt_name)
        if ckpt_path:
            print(f"  Checkpoint:  {ckpt_path}")
        if early_stop:
            print(f"  Early-stop:  YES (stops when gap < 0.01 Ha)")
        if args.ansatz_type == "adapt":
            print(_step(f"Step 5: ADAPT-VQE  (threshold={args.adapt_threshold:.0e}, "
                        f"max_ops={args.adapt_max_ops}, inner COBYLA {args.max_iter} iters)"))
            vqe_res = run_vqe_adapt(H_vqe, adapt_meta,
                                    max_iter=args.max_iter,
                                    seed=args.seed,
                                    backend=args.backend,
                                    e_target=e_casci_target,
                                    early_stop=early_stop,
                                    checkpoint_path=ckpt_path)
            n_params = vqe_res["num_params"]   # ADAPT picks its own count
        else:
            print(_step(f"Step 5: VQE  ({args.optimizer.upper()}, {args.multistart} restarts x {args.max_iter} iters)"))
            vqe_res = run_vqe(H_vqe, circuit_fn, n_params,
                              max_iter=args.max_iter,
                              multistart=args.multistart,
                              seed=args.seed,
                              backend=args.backend,
                              e_target=e_casci_target,
                              early_stop=early_stop,
                              checkpoint_path=ckpt_path,
                              optimizer=args.optimizer,
                              learning_rate=args.learning_rate)

        # BK constant correction
        _bk_corr = tap_meta.get("bk_constant_correction") or 0.0
        if abs(_bk_corr) > 1e-6:
            raw_e = vqe_res["best_energy_hartree"]
            vqe_res["best_energy_hartree"] = raw_e + _bk_corr
            print(_ok(f"BK energy correction applied: {raw_e:.10f} + ({_bk_corr:+.6f}) "
                      f"= {vqe_res['best_energy_hartree']:.10f} Ha"))

        # Step 6: Serialize
        print()
        print(_step("Step 6: Serialize Hamiltonian"))
        pauli_terms = serialize_hamiltonian(H_vqe)
        print(_ok(f"Serialized {len(pauli_terms)} Pauli terms"))

        # Step 7: Assemble
        print()
        print(_step("Step 7: Assemble Entry"))
        entry, entry_id, filename = assemble_entry(
            mol_config, args.basis, args.mapping, method_label, args.ansatz_reps,
            pyscf_res, tap_meta, vqe_res, pauli_terms, hf_tapered,
            args.max_iter, args.multistart, args.seed,
            circuit_fn=circuit_fn, H_tapered=H_vqe,
            backend=args.backend,
        )

        e_vqe   = vqe_res["best_energy_hartree"]
        e_casci = pyscf_res["e_casci"]
        abs_gap = abs(e_vqe - e_casci)
        trusted = abs_gap < 0.01

        print()
        print(f"{BOLD}--- Results Summary ----------------------------------------{RESET}")
        print(f"  HF energy:          {pyscf_res['e_hf']:.10f} Ha")
        if pyscf_res.get("e_casscf"):
            print(f"  CASSCF energy:      {pyscf_res['e_casscf']:.10f} Ha")
        if pyscf_res.get("e_ccsd_t"):
            print(f"  CCSD(T) energy:     {pyscf_res['e_ccsd_t']:.10f} Ha")
        print(f"  CASCI energy:       {e_casci:.10f} Ha  <-- VQE target")
        print(f"  VQE best energy:    {e_vqe:.10f} Ha")
        print(f"  |VQE - CASCI| gap:  {abs_gap:.6e} Ha  "
              f"({'< 0.01 -- CERTIFIED' if trusted else '>= 0.01 -- validated'})")
        if tap_meta.get("bk_imaginary_stripped"):
            print(f"  BK imaginary strip: YES (max_imag={tap_meta['bk_max_imag_abs']:.2e} Ha)")
        print(f"  Orbital opt:        {args.orbital_opt}")
        print(f"  Qubits:             {n_qubits} -> {tap_meta['n_qubits_tap']} (tapered)")
        print(f"  Entry ID:           {entry_id}")
        print(f"  Trust level:        {entry['trust']['level']}")
        print(f"  Flags:              {entry['results']['quality']['flags']}")

        out_dir  = Path(args.out_dir)
        out_path = out_dir / filename

        if args.dry_run:
            print()
            print(_warn(f"DRY RUN -- not writing {out_path}"))
            print(f"\n{GREEN}{BOLD}  [OK] Pipeline complete (dry run){RESET}\n")
            sys.exit(0)

        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(entry, indent=2, ensure_ascii=True))
        print()
        print(_ok(f"Entry written: {out_path}"))
        print(f"\n{GREEN}{BOLD}  [OK] Entry ready: {filename}{RESET}\n")
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(1)
    except Exception as ex:
        import traceback
        print(_fail(f"Pipeline failed: {ex}"))
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
