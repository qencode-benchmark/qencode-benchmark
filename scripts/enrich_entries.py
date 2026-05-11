#!/usr/bin/env python3
"""
enrich_entries.py — Phase 3: add FCIDUMP + circuit metrics to existing v3 entries
===================================================================================
For each entry in releases/v3/db/:
  1. Generates active-space FCIDUMP (base64-encoded) → artifacts.fcidump
     Compatible with ORCA, MOLPRO, FCIQMC, and DARPA QB-GSEE pipelines.
  2. Computes circuit metrics at optimal VQE params:
       - ansatz_depth            : logical circuit depth
       - ansatz_num_2q_gates     : number of 2-qubit gates (CNOTs)
       - ansatz_num_1q_gates     : number of 1-qubit gates
       - non_clifford_gate_count : number of non-Clifford rotations (RX/RY/RZ)
       - t_gate_estimate         : approximate T-gate count (Ross-Selinger, eps=1e-3)
       - t_gate_synthesis_epsilon: synthesis precision used
  3. Updates provenance.entry_hash_sha256 to reflect enriched content.

No VQE is re-run — uses stored optimal_params from the existing entry.

Run on Ubuntu:
  conda activate qencode
  python scripts/enrich_entries.py               # process all entries
  python scripts/enrich_entries.py --all         # same
  python scripts/enrich_entries.py --entry releases/v3/db/H2_sto3g_JW_HEA_v3_tapered__sha256_XXXX.json
  python scripts/enrich_entries.py --dry-run     # preview without writing
  python scripts/enrich_entries.py --force       # re-enrich already-enriched entries
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ── Repo paths ─────────────────────────────────────────────────────────────────
REPO    = Path(__file__).resolve().parent.parent
DB_DIR  = REPO / "releases" / "v3" / "db"

# Allow importing helpers from generate_entry_v3
sys.path.insert(0, str(REPO / "scripts"))

# ── Phase 2 BK entries built via OF-bridge (detect by known entry IDs) ────────
BRIDGE_BK_ENTRY_IDS = {
    "LiH_sto3g_BK_HEA_v3_tapered__sha256_fbd201192f348dad",
    "LiH_sto3g_BK_UCCSD_v3_tapered__sha256_cb4952f1a1a73bd4",
    "H2O_sto3g_BK_UCCSD_v3_tapered__sha256_9d65eb106904b772",
}


# ── FCIDUMP generation ─────────────────────────────────────────────────────────

def generate_fcidump_b64(mf, n_electrons: int, n_orbitals: int) -> str:
    """
    Generate base64-encoded FCIDUMP for the CASCI active space.

    Uses PySCF h1eff (active 1e integrals + core contribution) and h2e (active
    2e integrals in chemist notation), plus e_core as nuclear repulsion.
    The resulting FCIDUMP is compatible with MOLPRO, ORCA, FCIQMC, and the
    DARPA QB-GSEE interface.
    """
    from pyscf import mcscf, ao2mo, tools

    cas = mcscf.CASCI(mf, n_orbitals, n_electrons)
    h1eff, e_core = cas.get_h1eff()                      # (norb, norb), scalar
    h2e = ao2mo.restore(1, cas.get_h2eff(), n_orbitals)  # (norb,)^4 chemist

    with tempfile.NamedTemporaryFile(suffix=".fcidump", delete=False, mode="w") as tmp:
        tmpname = tmp.name
    try:
        tools.fcidump.from_integrals(
            tmpname, h1eff, h2e, n_orbitals, n_electrons,
            nuc=float(e_core), ms=0,
        )
        with open(tmpname, "rb") as f:
            raw = f.read()
    finally:
        if os.path.exists(tmpname):
            os.unlink(tmpname)

    return base64.b64encode(raw).decode("ascii")


# ── Circuit metrics ────────────────────────────────────────────────────────────

# Non-Clifford gates that contribute to T-gate count
_ROTATION_GATES = {
    "RX", "RY", "RZ", "Rot", "PhaseShift",
    "CRX", "CRY", "CRZ",
    "U1", "U2", "U3",
    "SingleExcitation", "DoubleExcitation",
    "Exp", "exp",
}

# Ross-Selinger T-gate count per rotation: ceil(1.149 * log2(1/eps))
_SYNTHESIS_EPS = 1e-3
_T_PER_ROTATION = int(math.ceil(1.149 * math.log2(1.0 / _SYNTHESIS_EPS)))  # = 10


def compute_circuit_metrics(circuit_fn, H_tapered, optimal_params: list) -> dict:
    """
    Evaluate qml.specs() at optimal_params and return Phase 3 circuit metrics.

    Returns dict with:
      ansatz_depth, ansatz_num_2q_gates, ansatz_num_1q_gates,
      non_clifford_gate_count, t_gate_estimate, t_gate_synthesis_epsilon
    """
    import pennylane as qml

    wires = sorted(H_tapered.wires)
    dev   = qml.device("default.qubit", wires=wires)

    @qml.qnode(dev)
    def _circuit(params):
        circuit_fn(params, wires=wires)
        return qml.expval(H_tapered)

    try:
        specs = qml.specs(_circuit)(np.array(optimal_params, dtype=float))
    except Exception as ex:
        print(f"    [WARN] qml.specs failed: {ex}")
        return _fallback_metrics(len(optimal_params))

    # PL 0.44 specs dict keys (may vary by version — use .get with defaults)
    depth   = int(specs.get("depth", specs.get("circuit_depth", 0)))
    g_sizes = specs.get("gate_sizes", {})
    num_2q  = int(g_sizes.get(2, 0))
    num_1q  = int(g_sizes.get(1, 0))

    gate_types  = specs.get("gate_types", {})
    n_rot       = sum(int(gate_types.get(g, 0)) for g in _ROTATION_GATES)
    t_estimate  = n_rot * _T_PER_ROTATION

    return {
        "ansatz_depth":             depth,
        "ansatz_num_2q_gates":      num_2q,
        "ansatz_num_1q_gates":      num_1q,
        "non_clifford_gate_count":  n_rot,
        "t_gate_estimate":          t_estimate,
        "t_gate_synthesis_epsilon": _SYNTHESIS_EPS,
    }


def _fallback_metrics(n_params: int) -> dict:
    """Rough formula-based fallback when qml.specs() fails."""
    t_estimate = n_params * _T_PER_ROTATION
    return {
        "ansatz_depth":             None,
        "ansatz_num_2q_gates":      None,
        "ansatz_num_1q_gates":      None,
        "non_clifford_gate_count":  n_params,   # lower bound
        "t_gate_estimate":          t_estimate,
        "t_gate_synthesis_epsilon": _SYNTHESIS_EPS,
    }


# ── Entry utilities ────────────────────────────────────────────────────────────

def _detect_use_bridge(entry: dict) -> bool:
    """Return True if the entry was built via OF-bridge."""
    mapping  = entry["encoding"]["mapping"]
    entry_id = entry.get("entry_id", "")
    if mapping == "parity":
        return True
    if mapping == "bravyi_kitaev" and entry_id in BRIDGE_BK_ENTRY_IDS:
        return True
    return False


def _is_enriched(entry: dict) -> bool:
    """Return True if this entry already has Phase 3 data."""
    has_fcidump = entry.get("artifacts", {}).get("fcidump") is not None
    has_depth   = entry.get("circuit_stats", {}).get("ansatz_depth") is not None
    return has_fcidump and has_depth


def _mol_config_from_entry(entry: dict) -> dict:
    """Reconstruct the mol_config dict expected by run_pyscf_suite."""
    prob = entry["problem"]
    return {
        "geometry_pyscf": prob["geometry"],
        "active_space":   [
            prob["active_space"]["num_electrons"],
            prob["active_space"]["num_spatial_orbitals"],
        ],
        "charge": prob.get("charge", 0) or 0,
        "spin":   prob.get("spin", 0) or 0,
    }


# ── Main enrichment pipeline ───────────────────────────────────────────────────

SEP = "─" * 65


def enrich_entry(entry_path: Path, dry_run: bool = False) -> bool:
    """
    Enrich a single entry with FCIDUMP + circuit metrics.
    Returns True on success, False on error.
    """
    # ── Imports from generate_entry_v3 ────────────────────────────────────────
    try:
        from generate_entry_v3 import (
            run_pyscf_suite,
            pyscf_geom_to_symbols_coords,
            build_pl_hamiltonian,
            apply_tapering,
            build_uccsd_circuit,
            build_hea_circuit,
            stable_hash,
        )
    except ImportError as exc:
        print(f"  [FAIL] Cannot import generate_entry_v3: {exc}")
        return False

    print(f"\n{SEP}")
    print(f"  Enriching: {entry_path.name}")
    print(SEP)

    # ── Load entry ────────────────────────────────────────────────────────────
    with open(entry_path, encoding="utf-8") as f:
        entry = json.load(f)

    entry_id   = entry.get("entry_id", entry_path.stem)
    mapping    = entry["encoding"]["mapping"]
    ansatz_type= entry["encoding"]["ansatz_type"]
    basis      = entry["problem"]["basis"]
    n_electrons= entry["problem"]["active_space"]["num_electrons"]
    n_orbitals = entry["problem"]["active_space"]["num_spatial_orbitals"]
    e_casci    = entry["results"]["reference"]["casci_ground_energy_hartree"]
    opt_params = entry["results"]["vqe"]["optimal_params"]

    print(f"  Molecule:  {entry['problem']['name']}  |  Mapping: {mapping}"
          f"  |  Ansatz: {ansatz_type}")
    print(f"  Active space: [{n_electrons}e, {n_orbitals}o]  |  CASCI: {e_casci:.8f} Ha")

    # ── Step 1: PySCF (fast — no classical suite) ─────────────────────────────
    print("\n  [1] PySCF CASCI (for FCIDUMP + Hamiltonian)...")
    mol_config  = _mol_config_from_entry(entry)
    use_bridge  = _detect_use_bridge(entry)

    try:
        pyscf_res = run_pyscf_suite(mol_config, basis, run_classical=False)
        mf        = pyscf_res["_mf"]
    except Exception as exc:
        print(f"  [FAIL] PySCF failed: {exc}")
        return False

    # ── Step 2: FCIDUMP ───────────────────────────────────────────────────────
    print("\n  [2] Generating FCIDUMP (base64)...")
    try:
        fcidump_b64 = generate_fcidump_b64(mf, n_electrons, n_orbitals)
        print(f"  [OK]  FCIDUMP: {len(fcidump_b64)} chars (base64)")
    except Exception as exc:
        print(f"  [FAIL] FCIDUMP generation failed: {exc}")
        return False

    # ── Step 3: Build Hamiltonian + taper ─────────────────────────────────────
    print(f"\n  [3] Building Hamiltonian (mapping={mapping}, bridge={use_bridge})...")
    try:
        symbols, coords_bohr = pyscf_geom_to_symbols_coords(mol_config["geometry_pyscf"])
        H, n_qubits = build_pl_hamiltonian(
            symbols, coords_bohr, basis, mapping,
            n_electrons, n_orbitals,
            mf=mf, use_of_bridge=use_bridge, e_casci=e_casci,
        )
        print(f"  [OK]  Hamiltonian: {n_qubits} qubits")
    except Exception as exc:
        print(f"  [FAIL] Hamiltonian build failed: {exc}")
        return False

    print("\n  [4] Applying Z2 tapering...")
    try:
        H_tapered, hf_tapered, tap_meta = apply_tapering(H, n_qubits, n_electrons, e_casci)
        n_tap = len(sorted(H_tapered.wires))
        print(f"  [OK]  Tapered: {n_qubits} → {n_tap} qubits")
    except Exception as exc:
        print(f"  [FAIL] Tapering failed: {exc}")
        return False

    # ── Step 4: Build ansatz ──────────────────────────────────────────────────
    print(f"\n  [5] Building ansatz ({ansatz_type})...")
    try:
        if ansatz_type == "hea":
            circuit_fn, n_params, _ = build_hea_circuit(H_tapered, hf_tapered, reps=2)
        elif ansatz_type in ("uccsd", "uccsd_tapered"):
            circuit_fn, n_params, _ = build_uccsd_circuit(
                H_tapered, hf_tapered, n_electrons, n_qubits,
                tap_meta["generators"], tap_meta["paulixops"], tap_meta["sectors"],
            )
        else:
            print(f"  [WARN] Unknown ansatz_type '{ansatz_type}' — defaulting to HEA")
            circuit_fn, n_params, _ = build_hea_circuit(H_tapered, hf_tapered, reps=2)

        stored_n = len(opt_params)
        if n_params != stored_n:
            print(f"  [WARN] Param count mismatch: rebuilt={n_params}, stored={stored_n}"
                  "  — using stored count for T-estimate")
            n_params = stored_n
        print(f"  [OK]  Ansatz: {n_params} params")
    except Exception as exc:
        print(f"  [FAIL] Ansatz build failed: {exc}")
        return False

    # ── Step 5: Circuit metrics ───────────────────────────────────────────────
    print("\n  [6] Computing circuit metrics (qml.specs)...")
    try:
        metrics = compute_circuit_metrics(circuit_fn, H_tapered, opt_params)
        print(f"  [OK]  depth={metrics['ansatz_depth']}  "
              f"2q={metrics['ansatz_num_2q_gates']}  "
              f"non-Clifford={metrics['non_clifford_gate_count']}  "
              f"T-est={metrics['t_gate_estimate']}")
    except Exception as exc:
        print(f"  [WARN] Circuit metrics failed: {exc}  — using fallback")
        metrics = _fallback_metrics(n_params)

    # ── Step 6: Update entry dict ─────────────────────────────────────────────
    entry.setdefault("artifacts", {})["fcidump"] = fcidump_b64

    cs = entry.setdefault("circuit_stats", {})
    cs.update({
        "ansatz_depth":             metrics["ansatz_depth"],
        "ansatz_num_2q_gates":      metrics["ansatz_num_2q_gates"],
        "ansatz_num_1q_gates":      metrics["ansatz_num_1q_gates"],
        "non_clifford_gate_count":  metrics["non_clifford_gate_count"],
        "t_gate_estimate":          metrics["t_gate_estimate"],
        "t_gate_synthesis_epsilon": metrics["t_gate_synthesis_epsilon"],
    })

    # Mark enrichment
    entry.setdefault("provenance", {})["phase3_enriched_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    # Recompute hash (provenance.entry_hash_sha256 now covers Phase 3 data)
    new_hash = stable_hash(entry)
    entry["provenance"]["entry_hash_sha256"] = new_hash

    print(f"\n  [OK]  New hash: {new_hash[:16]}...")

    if dry_run:
        print("  [DRY-RUN] Would write updated entry (skipped)")
        return True

    with open(entry_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    print(f"  [OK]  Written: {entry_path.name}")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 3: enrich v3 entries with FCIDUMP + circuit metrics"
    )
    parser.add_argument("--entry",   help="Path to a single entry JSON file")
    parser.add_argument("--all",     action="store_true", help="Process all entries in db/")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force",   action="store_true",
                        help="Re-enrich entries that already have Phase 3 data")
    args = parser.parse_args()

    if args.entry:
        entry_files = [Path(args.entry)]
    else:
        entry_files = sorted(DB_DIR.glob("*.json"))
        if not entry_files:
            print(f"No JSON files found in {DB_DIR}")
            sys.exit(1)

    print(f"\n{'=' * 65}")
    print(f"  QEncode Phase 3 Enrichment — {len(entry_files)} entries")
    print(f"  DB: {DB_DIR}")
    if args.dry_run:
        print("  MODE: DRY-RUN (no files will be written)")
    print(f"{'=' * 65}")

    n_ok = n_skip = n_fail = 0

    for ep in entry_files:
        with open(ep, encoding="utf-8") as f:
            e = json.load(f)

        if not args.force and _is_enriched(e):
            print(f"\n  [SKIP] {ep.name}  (already enriched)")
            n_skip += 1
            continue

        ok = enrich_entry(ep, dry_run=args.dry_run)
        if ok:
            n_ok += 1
        else:
            n_fail += 1

    print(f"\n{'=' * 65}")
    print(f"  DONE — enriched: {n_ok}  skipped: {n_skip}  failed: {n_fail}")
    print(f"{'=' * 65}\n")

    if n_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
