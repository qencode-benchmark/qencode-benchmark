# QEncode Suite v3.1 — 6-31G Basis Release

**42 benchmark entries · 30 certified · 12 research · 7 molecules**

---

## What changed from Suite v3 (STO-3G)

Suite v3.1 upgrades the basis set from STO-3G to **6-31G (split-valence)**, which is the standard for NISQ-era VQE demonstrations in the literature. The 6-31G basis produces CCSD(T) correlation energies approximately 5× larger than STO-3G, making the classical comparison physically meaningful.

All benchmark definitions (molecules, active spaces, mappings, ansatz families, optimizer protocol) are identical to Suite v3. Only the basis set changed.

---

## Benchmark molecules

| Molecule | Formula | Active Space | Qubits (tapered) | Tier |
|----------|---------|-------------|-----------------|------|
| Hydrogen | H₂ | [2e, 2o] | 1 | Certified |
| Hydrogen Fluoride | HF | [2e, 2o] | 1 | Certified |
| Lithium Hydride | LiH | [4e, 4o] | 4 | Certified |
| Beryllium Hydride | BeH₂ | [4e, 4o] | 3 | Certified |
| Water | H₂O | [4e, 4o] | 4–5 | Certified |
| Ammonia | NH₃ | [4e, 4o] | 4–5 | Certified |
| Nitrogen | N₂ | [6e, 6o] | 8 | Research |

---

## Pipeline

```
PySCF (CASCI reference, 6-31G basis)
  → PennyLane (qubit Hamiltonian, JW / Parity / BK mapping)
  → Z2 symmetry tapering
  → COBYLA VQE (10 multistart runs, seed=42)
  → SHA-256 provenance hash
```

---

## Certified entries (30)

All 30 certified entries satisfy `beats_ccsd_t = True`:

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

This means the VQE simulation error is smaller than the CCSD(T) correlation energy — the best single-reference perturbative classical result for that molecule. This is not a claim that quantum computing beats classical computing overall; it is a precision comparison within the same molecular system.

---

## Research entries (12)

N₂ entries are validated but do not meet the 0.01 Ha certification threshold. N₂ has a strongly-correlated triple bond and 404 UCCSD variational parameters under 6-31G. Only 1 of 10 optimizer restarts converged to a meaningful minimum. Results are correct — the gap reflects the method's limitation on this system, not an implementation error.

---

## Download contents (`qencode-suite-v3.1-artifacts.zip`)

- `*_631g_*.json` — 42 full benchmark artifact files (30 certified + 12 research)
- `leaderboard_accuracy.csv` — ranked by |E_VQE − E_CASCI| gap
- `leaderboard_hardware_cost.csv` — ranked by 2-qubit gate count
- `leaderboard_balanced.csv` — equal-weight normalized rank score
- `leaderboard_research.csv` — validated research-tier entries
- `leaderboard_metadata.json` — suite version, generation date, counts
- `schema_v3.json` — JSON schema for entry artifacts

---

## Reproducing results

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
conda create -n qencode python=3.11 && conda activate qencode
pip install -r requirements.txt

# Reproduce a single entry
python scripts/generate_entry_v3.py \
  --molecule HF \
  --basis 6-31g \
  --mapping parity \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

The SHA-256 hash in the reproduced entry should match the `entry_hash_sha256` field in the corresponding artifact JSON.

---

## Live leaderboard

All entries are browsable at **[qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)**

Each leaderboard row links to a full verification page at `/entry/<entry_id>` showing geometry, all energies, circuit stats, tool versions, and the provenance hash.
