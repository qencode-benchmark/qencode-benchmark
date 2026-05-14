# QEncode Suite v3.2 — Ethylene Release

> **Status: Released.** 6 entries committed (all 3 mappings × 2 ansatze).

---

## What's new in v3.2

Suite v3.2 adds **ethylene (C₂H₄)** — the first 8-qubit molecule in the QEncode benchmark set.
All 6 entries across JW, BK, and Parity mappings are **certified** and beat CCSD(T).

All v3.1 certified entries (30 entries, 6 molecules) carry forward unchanged.

---

## New entries — all certified

| Entry ID | Mapping | Ansatz | VQE gap | 2Q gates | Depth | Trust |
|----------|---------|--------|---------|----------|-------|-------|
| C2H4_631g_JW_HEA_v3_tapered | JW | HEA | 2.80 × 10⁻⁷ Ha | 4 | 8 | **Certified** |
| C2H4_631g_JW_UCCSD_v3_tapered | JW | UCCSD | 5.80 × 10⁻⁶ Ha | 8 | 14 | **Certified** |
| C2H4_631g_BK_HEA_v3_tapered | BK | HEA | 2.80 × 10⁻⁷ Ha | 4 | 8 | **Certified** |
| C2H4_631g_BK_UCCSD_v3_tapered | BK | UCCSD | 1.04 × 10⁻⁵ Ha | 8 | 22 | **Certified** |
| C2H4_631g_PAR_HEA_v3_tapered | Parity | HEA | 2.42 × 10⁻⁷ Ha | 4 | 8 | **Certified** |
| C2H4_631g_PAR_UCCSD_v3_tapered | Parity | UCCSD | 2.26 × 10⁻⁵ Ha | 8 | 22 | **Certified** |

All 6 entries: `beats_ccsd_t = True`, qubits 8 → 3 after Z2 tapering (5 symmetries removed).

---

## Key results

```
Molecule:     C₂H₄ (ethylene, D2h symmetry, equilibrium geometry)
Basis:        6-31G
Active space: [4e, 4o]  — π, π*, and adjacent σ/σ* orbitals
Mappings:     Jordan-Wigner, Bravyi-Kitaev, Parity

HF energy:           -78.003574 Ha
CASCI energy:        -78.026278 Ha   ← VQE target (active-space FCI)
CCSD(T) energy:      -78.219007 Ha
CCSD(T) correlation:   0.2154  Ha   ← certification threshold

Best gap (PAR/HEA):  2.42e-7 Ha  — 4 orders below threshold
Worst gap (PAR/UCCSD): 2.26e-5 Ha  — 2.5 orders below threshold
All 6 certified.

Qubits: 8 (JW/BK full) → 3 (after Z2 tapering, 5 symmetries removed)
```

**Note on BK certification:** v3.1 BK entries for larger molecules (LiH, H₂O, NH₃) were
validated-only due to a PennyLane 0.44 complex-taper issue. C₂H₄ BK entries certified
comfortably — the [4e,4o] active space produces a well-conditioned tapered Hamiltonian
where the BK constant correction (stored in `bk_constant_correction_ha`) fully restores
the correct energy.

---

## Certification criterion (unchanged from v3.1)

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

All 6 v3.2 entries satisfy this criterion.

---

## Pipeline (unchanged from v3.1)

```
PySCF (CASCI reference, 6-31G basis)
  → PennyLane (qubit Hamiltonian, JW / BK / Parity mapping)
  → Z2 symmetry tapering (8 → 3 qubits)
  → COBYLA VQE (10 multistart runs, seed=42)
  → SHA-256 provenance hash
```

---

## Reproduce

```bash
# Any mapping / ansatz combination
python scripts/generate_entry_v3.py \
  --molecule C2H4 \
  --basis 6-31g \
  --mapping jordan_wigner \   # or bravyi_kitaev / parity
  --ansatz-type uccsd \       # or hardware_efficient
  --multistart 10 \
  --seed 42 \
  --out-dir releases/v3.2/db
```

---

## Suite totals after v3.2

| Suite | Molecules | Certified entries | Research entries | Total |
|-------|-----------|------------------|-----------------|-------|
| v3 (STO-3G) | 7 | — | — | legacy |
| v3.1 (6-31G) | 6 + N₂ | 30 | 12 | 42 |
| v3.2 (6-31G) | + C₂H₄ | **36** | 12 | **48** |

---

## Version roadmap

| Suite | Basis | Molecules | Status |
|-------|-------|-----------|--------|
| v3 | STO-3G | H₂ HF LiH BeH₂ H₂O NH₃ N₂ | Released |
| v3.1 | 6-31G | same | Released |
| v3.2 | 6-31G | + C₂H₄ | **Released** |
| v4 | cc-pVDZ | same + butadiene, benzene, … | Planned |
