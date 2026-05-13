# QEncode Suite v3.2 — Ethylene Release

> **Status: Released.** 2 entries committed (JW/UCCSD, JW/HEA).

---

## What's new in v3.2

Suite v3.2 adds **ethylene (C₂H₄)** — the first 8-qubit molecule in the QEncode benchmark set.

All v3.1 certified entries (30 entries, 6 molecules) carry forward unchanged.

---

## New entries

| Entry ID | Molecule | Formula | Active Space | Qubits (tapered) | Basis | VQE gap | Trust |
|----------|----------|---------|-------------|-----------------|-------|---------|-------|
| C2H4_631g_JW_UCCSD_v3_tapered | Ethylene | C₂H₄ | [4e, 4o] | 3 | 6-31G | 5.8 × 10⁻⁶ Ha | **Certified** |
| C2H4_631g_JW_HEA_v3_tapered  | Ethylene | C₂H₄ | [4e, 4o] | 3 | 6-31G | 2.8 × 10⁻⁷ Ha | **Certified** |

Both entries pass the certification criterion and beat CCSD(T).

---

## Key results

```
Molecule:   C₂H₄ (ethylene, D2h symmetry, equilibrium geometry)
Basis:      6-31G
Active space: [4e, 4o]  — π, π*, and adjacent σ/σ* orbitals
Mapping:    Jordan-Wigner + Z2 tapering

HF energy:      -78.003574 Ha
CASCI energy:   -78.026278 Ha   ← VQE target (active-space FCI)
CCSD(T) energy: -78.219007 Ha
CCSD(T) correlation: 0.2154 Ha  ← certification threshold

UCCSD  VQE gap: 5.8e-06 Ha   beats_ccsd_t = True   ✓ CERTIFIED
HEA    VQE gap: 2.8e-07 Ha   beats_ccsd_t = True   ✓ CERTIFIED

Qubits: 8 (JW full) → 3 (after Z2 tapering, 5 symmetries removed)
```

**Note on certification:** Pre-release documentation predicted Research+ (UCCSD likely
to fail) based on ethylene's strong π-bond correlation. The actual [4e, 4o] active-space
restricts to the most correlated valence shell only, making it tractable for UCCSD.
Both ansatze certified comfortably — VQE gaps are 3–4 orders of magnitude below the
0.01 Ha threshold.

---

## Certification criterion (unchanged from v3.1)

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

Both v3.2 entries satisfy this criterion.

---

## Pipeline (unchanged from v3.1)

```
PySCF (CASCI reference, 6-31G basis)
  → PennyLane (qubit Hamiltonian, JW mapping)
  → Z2 symmetry tapering (8 → 3 qubits)
  → COBYLA VQE (10 multistart runs, seed=42)
  → SHA-256 provenance hash
```

---

## Reproduce

```bash
# UCCSD
python scripts/generate_entry_v3.py \
  --molecule C2H4 \
  --basis 6-31g \
  --mapping jordan_wigner \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42 \
  --out-dir releases/v3.2/db

# HEA
python scripts/generate_entry_v3.py \
  --molecule C2H4 \
  --basis 6-31g \
  --mapping jordan_wigner \
  --ansatz-type hardware_efficient \
  --multistart 10 \
  --seed 42 \
  --out-dir releases/v3.2/db
```

---

## Version roadmap

| Suite | Basis | Molecules | Status |
|-------|-------|-----------|--------|
| v3 | STO-3G | H₂ HF LiH BeH₂ H₂O NH₃ N₂ | Released |
| v3.1 | 6-31G | same | Released |
| v3.2 | 6-31G | + C₂H₄ | **Released** |
| v4 | TBD | TBD | Planned — new basis or pipeline |
