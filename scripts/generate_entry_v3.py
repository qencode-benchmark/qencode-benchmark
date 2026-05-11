#!/usr/bin/env python3
"""
Phase 1: QEncode v3 Entry Generator
=====================================
Pipeline:
  PySCF  -> HF + MP2 + CCSD + CCSD(T) + CASCI (active-space FCI)
  PennyLane -> qubit Hamiltonian + Z2 symmetry tapering + VQE (COBYLA)

Usage:
  python scripts/generate_entry_v3.py --molecule H2
  python scripts/generate_entry_v3.py --molecule LiH --mapping bravyi_kitaev
  python scripts/generate_entry_v3.py --molecule H2 --ansatz-type hardware_efficient
  python scripts/generate_entry_v3.py --molecule H2O --multistart 5 --max-iter 800
  python scripts/generate_entry_v3.py --molecule H2 --dry-run

Exit codes: 0 = entry written, 1 = pipeline error.

Critical design decisions (see spec):
  - Reference energy is CASCI active-space FCI, NOT full-system FCI.
  - VQE gap = |E_VQE - E_CASCI|. Certified if gap < 0.01 Ha.
  - CASCI nelec MUST be tuple (n_alpha, n_beta), not int.
  - PennyLane coords MUST be numpy array (not list).
  - Tapered HF state via qchem.taper_hf() -- standard |1..10..0> is WRONG after tapering.
  - Parity mapping deferred to Phase 2 (PL 0.44 does not support it in molecular_hamiltonian).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

REPO = Path(__file__).resolve().parent.parent

ANG_TO_BOHR = 1.8897259886  # 1 Angstrom in Bohr

# ─── Colour helpers (ASCII-safe for Windows cp1252) ───────────────────────────
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
    """
    Load molecule config from molecules_v3.json and normalise key names.

    The catalog uses 'v3_active_space' and 'geometry'; this function adds
    the aliases 'active_space' and 'geometry_pyscf' so the rest of the
    pipeline can use consistent names regardless of catalog version.
    """
    catalog_path = REPO / "molecules_v3.json"
    if not catalog_path.exists():
        raise FileNotFoundError(f"Molecule catalog not found: {catalog_path}")
    catalog = json.loads(catalog_path.read_text())
    for raw in catalog.get("entries", []):
        if raw["molecule"].upper() == name.upper():
            entry = dict(raw)
            # Normalise active space key
            if "active_space" not in entry:
                entry["active_space"] = entry.get("v3_active_space",
                                                   entry.get("active_electrons_orbitals"))
            # Normalise geometry key
            if "geometry_pyscf" not in entry:
                entry["geometry_pyscf"] = entry.get("geometry",
                                                     entry.get("geometry_angstrom"))
            return entry
    available = [e["molecule"] for e in catalog.get("entries", [])]
    raise KeyError(f"Molecule '{name}' not found. Available: {available}")


def pyscf_geom_to_symbols_coords(atom_str: str):
    """
    Parse PySCF atom string (Angstrom) into symbols list and flat coords_bohr array.

    Input:  "H 0 0 0; H 0 0 0.735"
    Output: (["H","H"], np.array([0,0,0, 0,0,1.3889]))
    """
    atoms = [a.strip() for a in atom_str.strip().split(";") if a.strip()]
    symbols = []
    coords_ang = []
    for a in atoms:
        parts = a.split()
        symbols.append(parts[0])
        coords_ang.extend(float(x) for x in parts[1:4])
    coords_bohr = np.array(coords_ang) * ANG_TO_BOHR
    return symbols, coords_bohr


# ─── PySCF: classical comparison + CASCI reference ────────────────────────────

def run_pyscf_suite(mol_config: dict, basis: str, run_classical: bool = True) -> dict:
    """
    Run the full PySCF suite for a molecule:
      HF -> MP2 -> CCSD -> CCSD(T) -> CASCI (active-space FCI)

    Returns a flat dict with all energies and metadata.

    CRITICAL: CASCI nelec is a tuple (n_alpha, n_beta), NOT an integer.
    The CASCI energy is the VQE comparison point (active-space FCI).
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
        # MP2
        try:
            from pyscf import mp
            mymp = mp.MP2(mf).run()
            e_mp2 = float(mymp.e_tot)
            print(_ok(f"MP2:      {e_mp2:.10f} Ha"))
        except Exception as ex:
            print(_warn(f"MP2 failed: {ex}"))

        # CCSD + CCSD(T)
        try:
            from pyscf import cc
            mycc = cc.CCSD(mf).run()
            e_ccsd   = float(mycc.e_tot)
            e_ccsd_t = float(mycc.e_tot + mycc.ccsd_t())
            print(_ok(f"CCSD:     {e_ccsd:.10f} Ha"))
            print(_ok(f"CCSD(T):  {e_ccsd_t:.10f} Ha"))
        except Exception as ex:
            print(_warn(f"CCSD failed: {ex}"))

    # CASCI: active-space FCI -- THIS is the VQE reference energy
    # CRITICAL: nelec must be tuple (n_alpha, n_beta)
    mc = mcscf.CASCI(mf, n_orb, (n_alpha, n_beta))
    mc.run()
    e_casci = float(mc.e_tot)
    print(_ok(f"CASCI:    {e_casci:.10f} Ha  ({n_elec}e, {n_orb}o active space)"))

    # First excited state (optional)
    e_casci_ex = None
    try:
        mc2 = mcscf.CASCI(mf, n_orb, (n_alpha, n_beta))
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
        "e_hf":          e_hf,
        "e_mp2":         e_mp2,
        "e_ccsd":        e_ccsd,
        "e_ccsd_t":      e_ccsd_t,
        "e_casci":       e_casci,
        "e_casci_ex":    e_casci_ex,
        "pyscf_version": pyscf_ver,
        "computed_utc":  now_utc,
        "basis":         basis,
        "n_electrons":   n_elec,
        "n_orbitals":    n_orb,
    }


# ─── PennyLane: Hamiltonian + Z2 tapering ────────────────────────────────────

def build_pl_hamiltonian(symbols: list, coords_bohr: np.ndarray, basis: str,
                         mapping: str, n_electrons: int, n_orbitals: int):
    """
    Build qubit Hamiltonian via PennyLane qchem.

    CRITICAL: coords_bohr must be a numpy array (PL 0.44 requirement).
    Supported mappings: jordan_wigner, bravyi_kitaev.
    Parity mapping deferred to Phase 2.
    """
    from pennylane import qchem

    _MAPPING_ALIASES = {
        "jordan_wigner": "jordan_wigner",
        "jw":            "jordan_wigner",
        "bravyi_kitaev": "bravyi_kitaev",
        "bk":            "bravyi_kitaev",
    }
    pl_mapping = _MAPPING_ALIASES.get(mapping.lower())
    if pl_mapping is None:
        raise ValueError(f"Unsupported mapping '{mapping}'. Supported: jordan_wigner, bravyi_kitaev")

    # coords must be numpy array -- Python list causes AttributeError in PL 0.44
    if not isinstance(coords_bohr, np.ndarray):
        coords_bohr = np.array(coords_bohr)

    H, n_qubits = qchem.molecular_hamiltonian(
        symbols,
        coords_bohr,
        basis=basis,
        mapping=pl_mapping,
        active_electrons=n_electrons,
        active_orbitals=n_orbitals,
    )
    # PL 0.36+ returns Sum; older versions return Hamiltonian with .ops
    n_terms = len(getattr(H, "operands", None) or getattr(H, "ops", []))
    print(_ok(f"PL Hamiltonian: {n_qubits} qubits, {n_terms} terms  ({pl_mapping})"))
    return H, n_qubits


def apply_tapering(H, n_qubits: int, n_electrons: int):
    """
    Apply Z2 symmetry tapering to the qubit Hamiltonian.

    Returns:
      H_tapered   - tapered PennyLane Hamiltonian (fewer qubits)
      hf_tapered  - tapered HF reference state (numpy array)
                    CRITICAL: must use qchem.taper_hf(), NOT standard |1..10..0>
      tap_meta    - dict with tapering metadata for schema

    Reduces qubit count by 2 per symmetry (typically 2 symmetries -> 2 qubits saved).
    """
    from pennylane import qchem

    generators  = qchem.symmetry_generators(H)
    paulixops   = qchem.paulix_ops(generators, n_qubits)
    sectors     = qchem.optimal_sector(H, generators, n_electrons)
    H_tapered   = qchem.taper(H, generators, paulixops, sectors)
    # CRITICAL: tapered HF state must be computed via taper_hf
    hf_tapered  = qchem.taper_hf(generators, paulixops, sectors,
                                  num_electrons=n_electrons, num_wires=n_qubits)

    n_tap = len(H_tapered.wires)
    n_sym = len(generators)
    print(_ok(f"Z2 tapering: {n_qubits} -> {n_tap} qubits  ({n_sym} symmetries removed)"))
    print(_ok(f"Tapered HF state: {hf_tapered.tolist()}"))

    return H_tapered, hf_tapered, {
        "generators":    generators,
        "paulixops":     paulixops,
        "sectors":       sectors,
        "n_qubits_full": n_qubits,
        "n_qubits_tap":  n_tap,
        "n_symmetries":  n_sym,
    }


# ─── Ansatz builders ──────────────────────────────────────────────────────────

def _get_tapered_uccsd_ops(n_electrons: int, n_qubits_full: int,
                            generators, paulixops, sectors):
    """
    Build tapered UCCSD operators using qchem.taper_operation.

    Returns list of tapered Operations (each with 1 trainable param).
    Returns empty list if taper_operation is unavailable or yields nothing.
    """
    import pennylane as qml
    from pennylane import qchem

    singles, doubles = qchem.excitations(n_electrons, n_qubits_full)
    wire_order = list(range(n_qubits_full))
    tapered_ops = []

    # Process doubles first (dominant UCCSD terms)
    for d_wires in doubles:
        try:
            orig_op = qml.DoubleExcitation(0.0, wires=list(d_wires))
            tap = qchem.taper_operation(orig_op, generators, paulixops, sectors,
                                        wire_order=wire_order)
            # tap may be a single op or list
            for op in (tap if isinstance(tap, (list, tuple)) else [tap]):
                if op is not None:
                    n_p = getattr(op, "num_params", 0)
                    if n_p > 0:
                        tapered_ops.append(op)
        except Exception:
            pass

    # Singles
    for s_wires in singles:
        try:
            orig_op = qml.SingleExcitation(0.0, wires=list(s_wires))
            tap = qchem.taper_operation(orig_op, generators, paulixops, sectors,
                                        wire_order=wire_order)
            for op in (tap if isinstance(tap, (list, tuple)) else [tap]):
                if op is not None:
                    n_p = getattr(op, "num_params", 0)
                    if n_p > 0:
                        tapered_ops.append(op)
        except Exception:
            pass

    return tapered_ops


def _apply_tapered_op(op, param: float) -> None:
    """
    Apply a tapered excitation operator with the given parameter value.

    taper_operation may return either:
      - A standard gate (e.g. SingleExcitation, RY): re-instantiate with
        (param, wires=op.wires)
      - A PennyLane Exp operator (exp(coeff * base)): re-instantiate with
        qml.Exp(op.base, coeff=param).  Exp does not accept a 'wires' kwarg.
    """
    import pennylane as qml

    # Exp / SProd / etc. are "composite" ops that carry a .base attribute.
    # Standard parametric gates (RY, DoubleExcitation …) do not have .base.
    if hasattr(op, "base"):
        # taper_operation returns Exp(base, coeff) -- use qml.exp (lowercase)
        # to rebuild with the new parameter.  qml.Exp does not exist in PL 0.44.
        qml.apply(qml.exp(op.base, coeff=param))
    else:
        qml.apply(op.__class__(param, wires=op.wires))


def build_uccsd_circuit(H_tapered, hf_tapered: np.ndarray,
                        n_electrons: int, n_qubits_full: int,
                        generators, paulixops, sectors):
    """
    Build UCCSD ansatz for tapered Hamiltonian.

    Tries taper_operation for each singles/doubles excitation.
    Falls back to hardware_efficient if taper_operation fails or yields 0 params.

    Returns: (circuit_fn, n_params, method_label)
    """
    wires = sorted(H_tapered.wires)

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


def build_hea_circuit(H_tapered, hf_tapered: np.ndarray, reps: int = 2):
    """
    Hardware-efficient ansatz: BasisState(HF) + RY layers + CX ladder, repeated reps times.

    n_params = n_wires * (reps + 1)
    """
    import pennylane as qml

    wires   = sorted(H_tapered.wires)
    n_wires = len(wires)
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


# ─── VQE optimizer ────────────────────────────────────────────────────────────

def run_vqe(H_tapered, circuit_fn, n_params: int,
            max_iter: int = 500, multistart: int = 3, seed: int = 42) -> dict:
    """
    Run VQE using COBYLA with multistart random restarts.

    Optimizer: scipy COBYLA (gradient-free, good for < 100 params).
    Returns dict with best_energy, optimal_params, nfev, etc.
    """
    import pennylane as qml
    from scipy.optimize import minimize

    wires = sorted(H_tapered.wires)
    dev   = qml.device("default.qubit", wires=wires)

    @qml.qnode(dev)
    def energy_fn(params):
        circuit_fn(params, wires=wires)
        return qml.expval(H_tapered)

    rng          = np.random.default_rng(seed)
    best_energy  = np.inf
    best_params  = None
    total_nfev   = 0

    for run in range(multistart):
        x0 = np.zeros(n_params) if run == 0 else rng.uniform(-np.pi, np.pi, n_params)

        result = minimize(
            lambda p: float(energy_fn(p)),
            x0,
            method="COBYLA",
            options={"maxiter": max_iter, "rhobeg": 0.5},
        )
        total_nfev += result.nfev
        e_run = result.fun

        status = "[OK]" if e_run <= best_energy else "    "
        print(f"    run {run + 1}/{multistart}: E = {e_run:.10f} Ha  (nfev={result.nfev}) {status}")

        if e_run < best_energy:
            best_energy = e_run
            best_params = result.x.copy()

    print(_ok(f"VQE best energy: {best_energy:.10f} Ha  (total nfev={total_nfev})"))

    return {
        "best_energy_hartree": float(best_energy),
        "optimal_params":      best_params.tolist(),
        "num_params":          n_params,
        "nfev":                total_nfev,
        "optimizer":           "COBYLA",
        "multistart_runs":     multistart,
        "computed_utc":        _utcnow(),
    }


# ─── Hamiltonian serialization ────────────────────────────────────────────────

def serialize_hamiltonian(H_tapered) -> list:
    """
    Convert tapered Hamiltonian to list of {pauli_string, coefficient} dicts.

    Uses H_tapered.pauli_rep (PauliSentence, PL 0.36+).
    Falls back to sparse matrix extraction if pauli_rep is unavailable.
    """
    terms = []
    try:
        for pauli_word, coeff in H_tapered.pauli_rep.items():
            if not pauli_word:
                ps = "I"
            else:
                # PauliWord is a dict[wire_index -> "X"/"Y"/"Z"]
                ps = "".join(f"{op}{w}" for w, op in sorted(pauli_word.items()))
            terms.append({
                "pauli_string": ps,
                "coefficient":  float(np.real(coeff)),
            })
        return terms
    except AttributeError:
        pass

    # Fallback: try .ops / .coeffs (older PennyLane Hamiltonian format)
    try:
        ops    = getattr(H_tapered, "ops", None) or list(H_tapered.operands)
        coeffs = getattr(H_tapered, "coeffs", [1.0] * len(ops))
        for op, coeff in zip(ops, coeffs):
            ps = str(op)  # e.g. "PauliZ(wires=[0])"
            terms.append({
                "pauli_string": ps,
                "coefficient":  float(np.real(coeff)),
            })
        return terms
    except Exception:
        pass

    # Last resort: record number of qubits only
    n_q = len(H_tapered.wires)
    return [{"pauli_string": "MATRIX_FALLBACK", "num_qubits": n_q}]


# ─── Entry assembly ───────────────────────────────────────────────────────────

def stable_hash(d: dict) -> str:
    """SHA-256 of canonical JSON (sorted keys, compact separators)."""
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def try_sign_hash(entry_hash: str):
    """
    Optional Ed25519 signing. Returns (sig_b64, key_id) or (None, None).
    Looks for key in: keys/signing_key.pem, keys/private_key.pem,
                      ~/.qencode/signing_key.pem, or QENCODE_SIGNING_KEY_B64 env var.
    """
    import base64
    import os

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


def assemble_entry(mol_config: dict, basis: str, mapping: str,
                   ansatz_type: str, ansatz_reps: int,
                   pyscf_res: dict, tap_meta: dict,
                   vqe_res: dict, pauli_terms: list,
                   hf_tapered: np.ndarray,
                   max_iter: int, multistart: int, seed: int) -> tuple:
    """
    Assemble the full v3 JSON entry dict and compute its SHA-256 hash.
    Returns (entry_dict, entry_id, filename).
    """
    mol_name  = mol_config["molecule"]
    n_e, n_o  = mol_config["active_space"]
    e_casci   = pyscf_res["e_casci"]
    e_hf      = pyscf_res["e_hf"]
    e_ccsd_t  = pyscf_res.get("e_ccsd_t")
    e_vqe     = vqe_res["best_energy_hartree"]
    now_utc   = _utcnow()

    # Quality metrics
    abs_gap       = abs(e_vqe - e_casci)
    trusted       = abs_gap < 0.01
    beats_classical = None
    if e_ccsd_t is not None and e_hf is not None:
        ccsd_t_corr     = abs(e_ccsd_t - e_hf)
        beats_classical = abs_gap < ccsd_t_corr

    flags = []
    if trusted:
        flags.append("gap_certified")
    if beats_classical:
        flags.append("beats_classical")
    if abs_gap > 0.1:
        flags.append("large_gap")
    if "hea_fallback" in ansatz_type:
        flags.append("hea_fallback_used")

    entry = {
        "schema_version": "3.0.0",
        "entry_id":       None,          # filled after hashing
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
        },

        "encoding": {
            "mapping":     mapping,
            "ansatz_type": ansatz_type,
            "ansatz_reps": ansatz_reps if "hea" in ansatz_type else 1,
            "tapering": {
                "enabled":             True,
                "method":              "z2_symmetry",
                "num_symmetries":      tap_meta["n_symmetries"],
                "original_num_qubits": tap_meta["n_qubits_full"],
                "tapered_num_qubits":  tap_meta["n_qubits_tap"],
                "sectors":             [int(x) for x in tap_meta["sectors"]],
                "hf_tapered_state":    [int(x) for x in hf_tapered],
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
                "ansatz_pennylane":   None,   # future: serialize QNode
                "ansatz_includes_hf": True,
            },
            "fcidump": None,               # future Phase 3
        },

        "results": {
            "reference": {
                "hf_energy_hartree":           e_hf,
                "casci_ground_energy_hartree":  e_casci,
                "casci_first_excited_hartree":  pyscf_res.get("e_casci_ex"),
                "exact_qubit_ground_energy_hartree_like": None,
            },
            "classical_comparison": {
                "hf_energy_hartree":     e_hf,
                "mp2_energy_hartree":    pyscf_res.get("e_mp2"),
                "ccsd_energy_hartree":   pyscf_res.get("e_ccsd"),
                "ccsd_t_energy_hartree": e_ccsd_t,
                "mp2_correlation":       (_safe_corr(pyscf_res.get("e_mp2"), e_hf)),
                "ccsd_t_correlation":    (_safe_corr(e_ccsd_t, e_hf)),
                "pyscf_version":         pyscf_res.get("pyscf_version"),
                "computed_utc":          pyscf_res.get("computed_utc"),
                "basis":                 basis,
            },
            "vqe": {
                "best_energy_hartree":  e_vqe,
                "optimal_params":       vqe_res["optimal_params"],
                "num_params":           vqe_res["num_params"],
                "nfev":                 vqe_res["nfev"],
                "optimizer":            vqe_res["optimizer"],
                "multistart_runs":      vqe_res["multistart_runs"],
                "computed_utc":         vqe_res["computed_utc"],
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
            "entry_hash_sha256":     "",   # filled below
            "source_schema_version": "3.0.0",
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
            "environment": {
                "platform": sys.platform,
            },
        },

        "trust": {
            "level":          "certified" if trusted else "validated",
            "certified_utc":  now_utc if trusted else None,
            "signature_b64":  None,   # filled after hashing
            "signing_key_id": None,
        },

        "run_config": {
            "optimizer":      "COBYLA",
            "max_iterations": max_iter,
            "multistart":     multistart,
            "seed":           seed,
            "backend_type":   "default.qubit",
            "shots":          None,
        },

        "circuit_stats": {
            "num_qubits_original":   tap_meta["n_qubits_full"],
            "num_qubits_tapered":    tap_meta["n_qubits_tap"],
            "ansatz_num_parameters": vqe_res["num_params"],
        },
    }

    # Hash the entry (without entry_id, signature, hash field itself)
    h               = stable_hash(entry)
    sig_b64, key_id = try_sign_hash(h)

    entry["provenance"]["entry_hash_sha256"] = h
    entry["trust"]["signature_b64"]          = sig_b64
    entry["trust"]["signing_key_id"]         = key_id

    # Build entry_id from molecule + basis + mapping + ansatz + hash prefix
    mol_safe   = mol_name.replace(" ", "_")
    basis_safe = basis.replace("-", "").replace("_", "")
    map_short  = {"jordan_wigner": "JW", "bravyi_kitaev": "BK", "parity": "PAR"}.get(
                     mapping.lower(), mapping.upper()[:3])
    ans_short  = "UCCSD" if "uccsd" in ansatz_type.lower() else "HEA"
    hash16     = h[:16]
    entry_id   = f"{mol_safe}_{basis_safe}_{map_short}_{ans_short}_v3_tapered__sha256_{hash16}"

    entry["entry_id"] = entry_id
    filename = entry_id + ".json"
    return entry, entry_id, filename


# ─── Utility helpers ──────────────────────────────────────────────────────────

def _pkg_version(pkg: str) -> Optional[str]:
    try:
        from importlib.metadata import version
        return version(pkg)
    except Exception:
        return None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_corr(e_method, e_hf) -> Optional[float]:
    if e_method is None or e_hf is None:
        return None
    return float(e_method - e_hf)


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
        description="QEncode v3 entry generator (Phase 1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--molecule",     default="H2",
                    help="Molecule name (must exist in molecules_v3.json)")
    ap.add_argument("--basis",        default="sto-3g",
                    help="Basis set (sto-3g, cc-pvdz, ...)")
    ap.add_argument("--mapping",      default="jordan_wigner",
                    choices=["jordan_wigner", "jw", "bravyi_kitaev", "bk"],
                    help="Qubit mapping")
    ap.add_argument("--ansatz-type",  default="uccsd",
                    choices=["uccsd", "hardware_efficient"],
                    help="VQE ansatz type")
    ap.add_argument("--ansatz-reps",  type=int, default=2,
                    help="Repetition layers for HEA (ignored for UCCSD)")
    ap.add_argument("--active-space", default=None,
                    help="Override active space as 'ne,no' e.g. '2,2'")
    ap.add_argument("--max-iter",     type=int, default=500,
                    help="COBYLA max iterations per restart")
    ap.add_argument("--multistart",   type=int, default=3,
                    help="Number of COBYLA random restarts")
    ap.add_argument("--seed",         type=int, default=42)
    ap.add_argument("--out-dir",      default=str(REPO / "releases" / "v3" / "db"),
                    help="Output directory for entries")
    ap.add_argument("--no-taper",     action="store_true",
                    help="Skip Z2 tapering (runs VQE on full qubit space)")
    ap.add_argument("--no-classical", action="store_true",
                    help="Skip MP2/CCSD/CCSD(T) (dev/speed mode)")
    ap.add_argument("--dry-run",      action="store_true",
                    help="Run full pipeline but do not write output file")
    ap.add_argument("--no-colour",    action="store_true",
                    help="Disable ANSI colour output")
    args = ap.parse_args()

    if args.no_colour:
        global GREEN, YELLOW, RED, RESET, BOLD
        GREEN = YELLOW = RED = RESET = BOLD = ""

    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}" + "=" * 65)
    print("  QEncode v3 - Phase 1 Entry Generator")
    print(f"  Python {sys.version.split()[0]}")
    print("=" * 65 + RESET)
    print(f"  Molecule:    {args.molecule}")
    print(f"  Basis:       {args.basis}")
    print(f"  Mapping:     {args.mapping}")
    print(f"  Ansatz:      {args.ansatz_type}")
    print(f"  Multistart:  {args.multistart} x {args.max_iter} iters")
    print(f"  Taper:       {'NO (--no-taper)' if args.no_taper else 'YES (Z2 symmetry)'}")
    print(f"  Classical:   {'NO (--no-classical)' if args.no_classical else 'YES (HF/MP2/CCSD/CCSD(T))'}")
    print()

    try:
        # ── Load molecule ─────────────────────────────────────────────────────
        mol_config = load_molecule(args.molecule)
        if args.active_space:
            ne_str, no_str = args.active_space.split(",")
            mol_config = dict(mol_config)
            mol_config["active_space"] = [int(ne_str), int(no_str)]
        n_electrons = mol_config["active_space"][0]
        n_orbitals  = mol_config["active_space"][1]
        print(f"  Active space: [{n_electrons}e, {n_orbitals}o]")
        print()

        # ── Step 1: PySCF classical suite + CASCI ─────────────────────────────
        print(_step(f"Step 1: PySCF  ({args.molecule}, {args.basis})"))
        pyscf_res = run_pyscf_suite(mol_config, args.basis,
                                    run_classical=not args.no_classical)

        # ── Step 2: PennyLane Hamiltonian ─────────────────────────────────────
        print()
        print(_step(f"Step 2: PennyLane Hamiltonian  ({args.mapping})"))
        symbols, coords_bohr = pyscf_geom_to_symbols_coords(mol_config["geometry_pyscf"])
        H, n_qubits = build_pl_hamiltonian(
            symbols, coords_bohr, args.basis,
            args.mapping, n_electrons, n_orbitals,
        )

        # ── Step 3: Z2 tapering ───────────────────────────────────────────────
        print()
        print(_step("Step 3: Z2 Symmetry Tapering"))
        if args.no_taper:
            import pennylane as qml
            # Untapered: use standard HF state and no tapering metadata
            H_vqe      = H
            hf_tapered = np.array([1] * n_electrons + [0] * (n_qubits - n_electrons))
            tap_meta   = {
                "generators": [], "paulixops": [], "sectors": [],
                "n_qubits_full": n_qubits,
                "n_qubits_tap":  n_qubits,
                "n_symmetries":  0,
            }
            print(_warn("Tapering skipped (--no-taper). Using full qubit space."))
        else:
            H_vqe, hf_tapered, tap_meta = apply_tapering(H, n_qubits, n_electrons)

        # Exact diagonalization for verification
        try:
            import pennylane as qml
            wires_tap = sorted(H_vqe.wires)
            H_mat     = qml.matrix(H_vqe, wire_order=wires_tap)
            e_exact   = float(np.linalg.eigvalsh(H_mat)[0])
            gap_vs_casci = abs(e_exact - pyscf_res["e_casci"])
            print(_ok(f"Exact H diag: {e_exact:.10f} Ha  (gap vs CASCI: {gap_vs_casci:.2e} Ha)"))
        except Exception as ex:
            print(_warn(f"Exact diagonalization skipped: {ex}"))

        # ── Step 4: Build ansatz ──────────────────────────────────────────────
        print()
        print(_step(f"Step 4: Ansatz  ({args.ansatz_type})"))
        if args.ansatz_type == "uccsd":
            circuit_fn, n_params, method_label = build_uccsd_circuit(
                H_vqe, hf_tapered, n_electrons, n_qubits,
                tap_meta["generators"], tap_meta["paulixops"], tap_meta["sectors"],
            )
        else:
            circuit_fn, n_params, method_label = build_hea_circuit(
                H_vqe, hf_tapered, reps=args.ansatz_reps
            )

        # ── Step 5: VQE ───────────────────────────────────────────────────────
        print()
        print(_step(f"Step 5: VQE  (COBYLA, {args.multistart} restarts x {args.max_iter} iters)"))
        vqe_res = run_vqe(
            H_vqe, circuit_fn, n_params,
            max_iter=args.max_iter,
            multistart=args.multistart,
            seed=args.seed,
        )

        # ── Step 6: Serialize Hamiltonian ─────────────────────────────────────
        print()
        print(_step("Step 6: Serialize Hamiltonian"))
        pauli_terms = serialize_hamiltonian(H_vqe)
        print(_ok(f"Serialized {len(pauli_terms)} Pauli terms"))

        # ── Step 7: Assemble + hash entry ─────────────────────────────────────
        print()
        print(_step("Step 7: Assemble Entry"))
        entry, entry_id, filename = assemble_entry(
            mol_config, args.basis, args.mapping, method_label, args.ansatz_reps,
            pyscf_res, tap_meta, vqe_res, pauli_terms, hf_tapered,
            args.max_iter, args.multistart, args.seed,
        )

        # ── Summary ───────────────────────────────────────────────────────────
        e_vqe   = vqe_res["best_energy_hartree"]
        e_casci = pyscf_res["e_casci"]
        abs_gap = abs(e_vqe - e_casci)
        trusted = abs_gap < 0.01

        print()
        print(f"{BOLD}--- Results Summary ----------------------------------------{RESET}")
        print(f"  HF energy:          {pyscf_res['e_hf']:.10f} Ha")
        if pyscf_res.get("e_mp2"):
            print(f"  MP2 energy:         {pyscf_res['e_mp2']:.10f} Ha")
        if pyscf_res.get("e_ccsd"):
            print(f"  CCSD energy:        {pyscf_res['e_ccsd']:.10f} Ha")
        if pyscf_res.get("e_ccsd_t"):
            print(f"  CCSD(T) energy:     {pyscf_res['e_ccsd_t']:.10f} Ha")
        print(f"  CASCI energy:       {e_casci:.10f} Ha  <-- VQE target")
        print(f"  VQE best energy:    {e_vqe:.10f} Ha")
        print(f"  |VQE - CASCI| gap:  {abs_gap:.6e} Ha  ({'< 0.01 -- CERTIFIED' if trusted else '>= 0.01 -- validated'})")
        print(f"  Qubits:             {n_qubits} -> {tap_meta['n_qubits_tap']} (tapered)")
        print(f"  Entry ID:           {entry_id}")
        print(f"  Trust level:        {entry['trust']['level']}")
        print(f"  Flags:              {entry['results']['quality']['flags']}")

        # ── Write output ──────────────────────────────────────────────────────
        out_dir = Path(args.out_dir)
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
        print()
        print(_fail(f"Pipeline failed: {ex}"))
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
