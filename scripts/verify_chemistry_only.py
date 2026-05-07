#!/usr/bin/env python3
"""
QEncode — Chemistry Reference Script (Part 1 of 2)
===================================================
Runs ONLY PySCF classical chemistry for CO, LiF, NH3.
No Qiskit. No VQE. Just the ground-truth energy values.

This takes ~2 minutes and tells you:
  - HF / CCSD / FCI energies
  - Real active space size
  - Whether my gap estimates were correct

Run:
    python verify_chemistry_only.py

Cross-check: Google "CO STO-3G Hartree-Fock" — the HF energy
should match published values within 1e-6 Ha.
"""

import sys
print("Loading PySCF...", flush=True)
try:
    from pyscf import gto, scf, fci, cc, mcscf
except ImportError:
    print("ERROR: pip install pyscf")
    sys.exit(1)

import numpy as np

# Claude's gap estimates (what I claimed for the leaderboard)
ESTIMATES = {
    "CO":  {"uccsd_gap": 8.0e-7,  "note": "I assumed [6e,6o] active space"},
    "LiF": {"uccsd_gap": 4.2e-5,  "note": "I assumed [6e,6o] active space"},
    "NH3": {"uccsd_gap": 1.1e-6,  "note": "I assumed [6e,6o] active space"},
}

MOLECULES = {
    "CO":  "C 0 0 0; O 0 0 1.128",
    "LiF": "Li 0 0 0; F 0 0 1.5639",
    "NH3": "N 0 0 0.1173; H 0 0.9345 -0.3910; H 0.8094 -0.4672 -0.3910; H -0.8094 -0.4672 -0.3910",
}

results = {}

for name, atom_str in MOLECULES.items():
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")

    mol = gto.Mole(atom=atom_str, basis="sto-3g", charge=0, spin=0, verbose=0)
    mol.build()

    # Hartree-Fock
    mf = scf.RHF(mol)
    e_hf = mf.kernel()
    print(f"  HF energy:   {e_hf:.8f} Ha")

    # CCSD (classical reference for UCCSD quality)
    mycc = cc.CCSD(mf)
    mycc.verbose = 0
    mycc.kernel()
    e_ccsd = e_hf + mycc.e_corr
    print(f"  CCSD energy: {e_ccsd:.8f} Ha")

    # Full FCI (exact ground truth for this basis)
    print("  FCI...      ", end="", flush=True)
    ci = fci.FCI(mf)
    ci.verbose = 0
    e_fci, _ = ci.kernel()
    print(f"{e_fci:.8f} Ha")

    # Gaps
    ccsd_gap = abs(e_ccsd - e_fci)
    hf_gap   = abs(e_hf   - e_fci)
    print(f"  CCSD→FCI gap:  {ccsd_gap:.4e} Ha  (real UCCSD upper bound)")
    print(f"  HF→FCI gap:    {hf_gap:.4e} Ha  (correlation energy)")

    # Active space
    n_heavy  = sum(1 for a in mol.atom_charges() if a > 1)
    n_frozen = n_heavy
    n_ao     = mol.nao_nr()
    n_active_o = n_ao - n_frozen
    n_active_e = mol.nelectron - 2 * n_frozen
    print(f"  Active space:  [{n_active_e}e, {n_active_o}o]  "
          f"→ {2*n_active_o} qubits (JW)")

    # CAS-FCI in the active space
    print("  CAS-FCI...  ", end="", flush=True)
    mc = mcscf.CASCI(mf, n_active_o, n_active_e)
    mc.verbose = 0
    e_cas, _ = mc.kernel()[:2]
    cas_gap = abs(e_cas - e_fci)
    print(f"{e_cas:.8f} Ha  (gap to FCI: {cas_gap:.4e})")

    est = ESTIMATES[name]["uccsd_gap"]
    ratio = ccsd_gap / est if est else None
    verdict = "WRONG" if ratio and ratio > 10 else ("CLOSE" if ratio and ratio < 3 else "OFF")
    print(f"\n  My estimate:   {est:.4e} Ha")
    print(f"  Real proxy:    {ccsd_gap:.4e} Ha  → estimate was {ratio:.0f}x {'too small' if ratio>1 else 'too large'} [{verdict}]")

    results[name] = dict(
        e_hf=e_hf, e_ccsd=e_ccsd, e_fci=e_fci,
        ccsd_gap=ccsd_gap, hf_gap=hf_gap,
        n_active_e=n_active_e, n_active_o=n_active_o,
        n_qubits_jw=2*n_active_o,
        my_estimate=est,
    )

# ── Summary table ─────────────────────────────────────────────────────────────
print("\n\n" + "="*75)
print("  SUMMARY — Were Claude's gap estimates correct?")
print("="*75)
print(f"  {'Mol':<6} {'My estimate':>12} {'Real (CCSD)':>13} {'Error':>8}  {'Active space':<15} {'Qubits'}")
print("  " + "-"*70)
for name, r in results.items():
    ratio = r["ccsd_gap"] / r["my_estimate"]
    print(f"  {name:<6} {r['my_estimate']:>12.4e} {r['ccsd_gap']:>13.4e} "
          f"{ratio:>7.0f}x  "
          f"[{r['n_active_e']}e, {r['n_active_o']}o]  {' '*8}"
          f"{r['n_qubits_jw']} qubits")

print()
print("  NOTE: 'Real' gap is the CCSD→FCI correlation energy — the best")
print("  classical proxy for how close UCCSD VQE can get to exact.")
print()
print("  If error >> 1x, my leaderboard estimates are wrong and must be")
print("  removed until real VQE runs are submitted by users.")

import json
with open("chemistry_reference.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved: chemistry_reference.json")
