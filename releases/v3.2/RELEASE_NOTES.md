# QEncode Suite v3.2 — Research+ Tier Release

> **Status: In preparation.** Entries will be generated and committed when ready.

---

## What's new in v3.2

Suite v3.2 adds a **Research+ tier** — larger, strongly-correlated molecules that
are beyond reliable UCCSD convergence but valuable for hardware demonstrations and
for tracking algorithmic progress as methods improve.

All v3.1 certified entries (30 entries, 6 molecules) carry forward unchanged.

---

## New molecules (Research+ tier)

| Molecule | Formula | Active Space | Qubits (est.) | Basis | Tier |
|----------|---------|-------------|--------------|-------|------|
| Ethylene | C₂H₄ | [4e, 4o] | 8–10 | 6-31G | Research+ |

**Why Research+, not Certified:**
Ethylene's π bond introduces strong correlation that UCCSD cannot reliably capture
within the 0.01 Ha certification threshold. The benchmark value is in demonstrating
the circuit, tracking the gap as algorithms improve, and providing a reference point
for hardware demonstrations of 8–10 qubit systems.

---

## Certification criterion (unchanged from v3.1)

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

Research+ entries are validated but not expected to meet this criterion.

---

## Pipeline (unchanged from v3.1)

```
PySCF (CASCI reference, 6-31G basis)
  → PennyLane (qubit Hamiltonian, JW / Parity / BK mapping)
  → Z2 symmetry tapering
  → COBYLA VQE (10 multistart runs, seed=42)
  → SHA-256 provenance hash
```

---

## Reproduce

```bash
python scripts/generate_entry_v3.py \
  --molecule C2H4 \
  --basis 6-31g \
  --mapping jordan_wigner \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

---

## Version roadmap

| Suite | Basis | Molecules | Status |
|-------|-------|-----------|--------|
| v3 | STO-3G | H₂ HF LiH BeH₂ H₂O NH₃ N₂ | Released |
| v3.1 | 6-31G | same | Released — current |
| v3.2 | 6-31G | + C₂H₄ (Research+) | In preparation |
| v4 | TBD | TBD | Planned — new basis or pipeline |
