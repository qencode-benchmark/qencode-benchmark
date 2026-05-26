# Quick Start — QEncode Suite v4

Run your first certified benchmark entry in a few minutes.

- Website: https://www.qencode-benchmark.org
- Live leaderboard: https://www.qencode-benchmark.org/leaderboard
- Benchmark spec: https://www.qencode-benchmark.org/benchmark
- Contact: support@qencode-benchmark.org

---

## 1. Install

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark.git
cd qencode-benchmark

# Conda (recommended)
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements-v4.txt
```

> **Windows:** Use WSL2 + Conda. PySCF does not install natively on Windows.  
> **GPU backend:** requires cuQuantum — pass `--backend lightning.gpu` when available.

---

## 2. Run a single entry

```bash
# H₂ — simplest molecule, 4 qubits → 1 after tapering
python scripts/generate_entry_v4.py \
  --molecule H2 \
  --mapping jordan_wigner \
  --ansatz-type uccsd \
  --out-dir releases/v4/db

# LiH — 8 qubits, moderate complexity
python scripts/generate_entry_v4.py \
  --molecule LiH \
  --mapping jordan_wigner \
  --ansatz-type hardware_efficient \
  --reps 4 --multistart 30 \
  --out-dir releases/v4/db

# N₂ — 12 qubits, CASSCF required, 404 UCCSD parameters
python scripts/generate_entry_v4.py \
  --molecule N2 \
  --mapping jordan_wigner \
  --ansatz-type uccsd \
  --orbital-opt casscf \
  --multistart 1 --max-iter 10000 \
  --out-dir releases/v4/db
```

The script prints a banner, runs PySCF → PennyLane → VQE, and writes a JSON entry to `releases/v4/db/`.

---

## 3. Key flags

| Flag | Default | Description |
|---|---|---|
| `--molecule` | required | Molecule name (H2, HF, LiH, BeH2, H2O, NH3, N2, H2CO, C4H6, benzene) |
| `--mapping` | required | jordan_wigner \| parity \| bravyi_kitaev |
| `--ansatz-type` | required | uccsd \| hardware_efficient |
| `--orbital-opt` | hf | hf \| casscf (casscf required for N₂ and benzene) |
| `--multistart` | 5 | Number of COBYLA random restarts |
| `--max-iter` | 500 | Max COBYLA iterations per restart |
| `--reps` | 4 | HEA layer count (hardware_efficient only) |
| `--backend` | default.qubit | default.qubit \| lightning.qubit \| lightning.gpu |
| `--out-dir` | releases/v4/db | Output directory for JSON entry |

---

## 4. Verify an entry

```bash
python scripts/verify_entry.py releases/v4/db/<entry_id>.json
```

The script re-runs the full pipeline and checks that the stored gap matches the recomputed gap within 1e-6 Ha.

---

## 5. Export and publish leaderboard

```bash
# Generate CSVs from all entries in releases/v4/db/
python scripts/export_leaderboard_v4.py

# Push to live Neon Postgres DB (requires LEADERBOARD_PUBLISH_SECRET)
python scripts/publish_leaderboard.py --secret $LEADERBOARD_PUBLISH_SECRET

# Commit updated CSV files
git add website/public/data/ && git commit -m "data: update leaderboard CSVs"
git push
```

---

## 6. Supported molecule/mapping/ansatz combinations

| Molecule | JW/HEA | JW/UCCSD | PAR/HEA | PAR/UCCSD | BK/HEA | BK/UCCSD |
|---|---|---|---|---|---|---|
| H₂ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HF | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LiH | ✅ | ✅ | ✅ | ❌ PAR/UCCSD | ❌ BK | ❌ BK |
| BeH₂ | ✅ | ✅ | ✅ | ✅ (D∞h exception) | ❌ BK | ❌ BK |
| H₂O | ✅ | ✅ | ✅ | ❌ PAR/UCCSD | ❌ BK | ❌ BK |
| NH₃ | ✅ | ✅ | ✅ | ❌ PAR/UCCSD | ❌ BK | ❌ BK |
| N₂ | ✅ | ✅ (casscf) | ✅ | ❌ PAR/UCCSD | ❌ BK | ❌ BK |

See [BENCHMARK_SPEC_V4.md](BENCHMARK_SPEC_V4.md) for full exclusion notes.

---

## 7. Long runs (WSL2 / Ubuntu)

For molecules requiring many iterations (N₂, benzene), use `nohup` with `tmux`:

```bash
nohup python scripts/generate_entry_v4.py \
  --molecule benzene --mapping jordan_wigner \
  --ansatz-type uccsd --orbital-opt casscf \
  --multistart 1 --max-iter 15000 \
  --backend lightning.qubit --out-dir releases/v4/db \
  > benzene_jw_uccsd.log 2>&1 &
echo "PID: $!"
tail -f benzene_jw_uccsd.log
```

> `systemd-inhibit` does not work in WSL2. Do not rely on it to prevent sleep.  
> Checkpoints are written to `.ckpt_*.json` after each restart and deleted on success.

---

## Environment details (requirements-v4.txt)

| Package | Version |
|---|---|
| PySCF | 2.5.0 |
| PennyLane | 0.45 |
| openfermion | 1.7.1 |
| NumPy | 1.26.4 |
| SciPy | pinned |

v3 entries remain reproducible using `requirements-v3.txt` and `scripts/verify_entry.py`.
