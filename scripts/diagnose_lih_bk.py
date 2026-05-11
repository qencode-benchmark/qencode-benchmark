#!/usr/bin/env python3
"""
Diagnostic: why does LiH BK tapering produce the wrong energy offset?

Run this on Ubuntu:
  conda activate qencode
  python scripts/diagnose_lih_bk.py

Expected outcome if healthy:
  - Full BK ground state  ≈ -7.863 Ha  (same as JW)
  - Tapered BK min eigen  ≈ -7.863 Ha
  - sector_search_energy  ≈ -7.863 Ha

If any of those diverge, the output will tell us exactly where the
constant energy offset is being dropped.
"""
from __future__ import annotations
import itertools
import numpy as np
import pennylane as qml
from pennylane import qchem

ANG_TO_BOHR = 1.8897259886

# ── LiH geometry (same as molecules_v3.json) ─────────────────────────────────
SYMBOLS = ["Li", "H"]
COORDS  = np.array([0.0, 0.0, 0.0,
                    0.0, 0.0, 1.6]) * ANG_TO_BOHR   # Angstrom → Bohr
ACTIVE_ELECTRONS = 4
ACTIVE_ORBITALS  = 4
BASIS = "sto-3g"

SEP = "─" * 65

def identity_coeff(H) -> float:
    """Extract the coefficient of the identity term from a PL Hamiltonian."""
    for pw, coeff in H.pauli_rep.items():
        if not pw:          # empty PauliWord == identity
            return float(np.real(coeff))
    return 0.0              # no identity term found


def ground_energy(H, label: str) -> float:
    wires = sorted(H.wires)
    mat   = qml.matrix(H, wire_order=wires)
    e0    = float(np.linalg.eigvalsh(mat)[0])
    print(f"  Ground state (exact diag):  {e0:.10f} Ha   [{label}]")
    return e0


def main():
    print(SEP)
    print("  LiH BK tapering energy-offset diagnostic")
    print(SEP)

    # ── 1. Build JW Hamiltonian (reference) ──────────────────────────────────
    print("\n[1] Jordan-Wigner Hamiltonian (reference)")
    H_jw, n_q_jw = qchem.molecular_hamiltonian(
        SYMBOLS, COORDS, basis=BASIS,
        mapping="jordan_wigner",
        active_electrons=ACTIVE_ELECTRONS,
        active_orbitals=ACTIVE_ORBITALS,
    )
    print(f"  JW: {n_q_jw} qubits, identity coeff = {identity_coeff(H_jw):.6f} Ha")
    e_jw = ground_energy(H_jw, "JW untapered")

    # ── 2. Build BK Hamiltonian ───────────────────────────────────────────────
    print("\n[2] Bravyi-Kitaev Hamiltonian (full, untapered)")
    H_bk, n_q_bk = qchem.molecular_hamiltonian(
        SYMBOLS, COORDS, basis=BASIS,
        mapping="bravyi_kitaev",
        active_electrons=ACTIVE_ELECTRONS,
        active_orbitals=ACTIVE_ORBITALS,
    )
    print(f"  BK: {n_q_bk} qubits, identity coeff = {identity_coeff(H_bk):.6f} Ha")
    e_bk_full = ground_energy(H_bk, "BK untapered")
    print(f"  JW vs BK offset: {abs(e_jw - e_bk_full):.2e} Ha")

    # ── 3. Z2 symmetry analysis ───────────────────────────────────────────────
    print("\n[3] Z2 symmetry analysis (BK)")
    generators = qchem.symmetry_generators(H_bk)
    paulixops  = qchem.paulix_ops(generators, n_q_bk)
    n_sym      = len(generators)
    print(f"  Symmetries found: {n_sym}  →  {n_q_bk} - {n_sym} = {n_q_bk - n_sym} tapered qubits")

    # ── 4. Brute-force sector search ──────────────────────────────────────────
    print(f"\n[4] Sector search ({2**n_sym} combinations):")
    results = []
    for sectors in itertools.product([1, -1], repeat=n_sym):
        try:
            H_t  = qchem.taper(H_bk, generators, paulixops, list(sectors))
            wt   = sorted(H_t.wires)
            if not wt:
                continue
            mat  = qml.matrix(H_t, wire_order=wt)
            e0   = float(np.linalg.eigvalsh(mat)[0])
            idc  = identity_coeff(H_t)
            results.append((e0, list(sectors), idc, len(wt)))
        except Exception as ex:
            results.append((np.inf, list(sectors), None, None))

    results.sort()
    for e0, sec, idc, nq in results:
        marker = "  <<< BEST" if results.index((e0, sec, idc, nq)) == 0 else ""
        idc_s  = f"{idc:.6f}" if idc is not None else "N/A"
        print(f"  sectors={sec}  e0={e0:.6f} Ha  identity={idc_s} Ha  nq={nq}{marker}")

    best_e, best_sec, best_idc, best_nq = results[0]

    # ── 5. Inspect the best-sector tapered Hamiltonian ────────────────────────
    print(f"\n[5] Best sector: {best_sec}")
    H_tapered = qchem.taper(H_bk, generators, paulixops, best_sec)
    wires_t   = sorted(H_tapered.wires)
    mat_t     = qml.matrix(H_tapered, wire_order=wires_t)
    evals_t   = np.linalg.eigvalsh(mat_t)
    print(f"  Tapered identity coeff:    {identity_coeff(H_tapered):.10f} Ha")
    print(f"  Tapered min eigenvalue:    {evals_t[0]:.10f} Ha")
    print(f"  Expected (CASCI):          -7.8630610955 Ha")
    print(f"  Offset (tapered - CASCI):  {evals_t[0] - (-7.8630610955):.6e} Ha")

    # ── 6. Tapered HF state ───────────────────────────────────────────────────
    print(f"\n[6] Tapered HF state (taper_hf)")
    hf_tap = qchem.taper_hf(generators, paulixops, best_sec,
                             num_electrons=ACTIVE_ELECTRONS,
                             num_wires=n_q_bk)
    print(f"  hf_tapered = {hf_tap.tolist()}")

    # Energy at the HF initial state
    dev = qml.device("default.qubit", wires=wires_t)

    @qml.qnode(dev)
    def hf_energy():
        qml.BasisState(hf_tap, wires=wires_t)
        return qml.expval(H_tapered)

    e_hf_init = float(hf_energy())
    print(f"  Energy at HF initial state: {e_hf_init:.10f} Ha")
    print(f"  Gap from ground state:      {abs(e_hf_init - evals_t[0]):.6e} Ha")

    # ── 7. Summary ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  DIAGNOSIS SUMMARY")
    print(SEP)
    print(f"  JW full ground state:         {e_jw:.10f} Ha")
    print(f"  BK full ground state:         {e_bk_full:.10f} Ha")
    print(f"  BK tapered ground state:      {evals_t[0]:.10f} Ha")
    print(f"  BK tapered HF init energy:    {e_hf_init:.10f} Ha")

    if abs(e_bk_full - e_jw) > 1e-4:
        print("\n  >>> ISSUE: BK full Hamiltonian has wrong ground state energy!")
        print("             PennyLane's BK molecular_hamiltonian is incorrect for LiH.")
    elif abs(evals_t[0] - e_jw) > 1e-4:
        print("\n  >>> ISSUE: Tapering drops the constant energy offset!")
        missing = e_jw - evals_t[0]
        print(f"             Missing constant: {missing:.6f} Ha")
        print("             Fix: add constant correction after tapering.")
    elif abs(e_hf_init - evals_t[0]) > 1.0:
        print("\n  >>> ISSUE: HF initial state has very poor overlap with ground state.")
        print("             The tapered Hamiltonian is correct but taper_hf produces")
        print("             a bad initial state — VQE cannot converge from it.")
    else:
        print("\n  All checks passed. The issue may be optimizer-related.")

    print(SEP)


if __name__ == "__main__":
    main()
