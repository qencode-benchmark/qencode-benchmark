# Quick Start — Run a QEncode Suite v3.1 Benchmark

Reproduce any certified entry from Suite v3.1 (6-31G basis) locally in a few commands.

Official platform:

- Website: https://www.qencode-benchmark.org
- Live leaderboard: https://www.qencode-benchmark.org/leaderboard
- Certification / pricing: https://www.qencode-benchmark.org/pricing
- Contact: quencodebenchmark@gmail.com

---

## 1. Install

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark.git
cd qencode-benchmark
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt
```

> PySCF is required and installs cleanly on Linux/macOS via pip or conda-forge.
> On Windows, use WSL + Conda (see [GETTING_STARTED.md](GETTING_STARTED.md)).

---

## 2. Reproduce a single entry

```bash
python scripts/generate_entry_v3.py \
  --molecule HF \
  --basis 6-31g \
  --mapping parity \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

The SHA-256 hash in the output should match `entry_hash_sha256` in the corresponding
artifact JSON at `releases/v3.1/db/`.

---

## 3. Run the full certified suite

```bash
python scripts/run_suite_v3.py \
  --basis 6-31g \
  --out-dir releases/v3.1/db \
  --skip-research
```

Omit `--skip-research` to also run N₂ (research tier).

---

## 4. Regenerate leaderboard CSVs

```bash
python scripts/export_leaderboard_v3.py \
  --db-dir releases/v3.1/db \
  --suite-version 3.1
```

---

## Benchmark molecules (Suite v3.1)

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
