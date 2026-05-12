# Getting Started — QEncode Benchmark Suite v3.1

Step-by-step setup to reproduce benchmark entries or run the full suite locally.

---

## Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11 recommended | Run scripts |
| Conda | any | Manage environment |
| Git | any | Clone repo |

---

## 1. Clone the repository

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark.git
cd qencode-benchmark
```

---

## 2. Create the environment

### Linux / macOS (recommended)

```bash
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt
```

Verify:

```bash
python -c "import pyscf, pennylane, scipy; print('OK')"
```

### Windows

PySCF does not build natively on Windows. Use **WSL + Ubuntu**:

```powershell
# Install WSL if needed (PowerShell, one-time)
wsl --install -d Ubuntu
```

Then inside Ubuntu:

```bash
cd /mnt/c/Users/<you>/Documents/qencode-benchmark
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt
```

---

## 3. Reproduce a single entry

Pick any entry from the [live leaderboard](https://www.qencode-benchmark.org/leaderboard)
and click its Details link to see the exact reproduce command. For example:

```bash
python scripts/generate_entry_v3.py \
  --molecule H2O \
  --basis 6-31g \
  --mapping jw \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

The `entry_hash_sha256` in the output must match the artifact JSON in `releases/v3.1/db/`.

---

## 4. Run the full certified suite

```bash
python scripts/run_suite_v3.py \
  --basis 6-31g \
  --out-dir releases/v3.1/db \
  --skip-research
```

---

## 5. Project layout

```
qencode-benchmark/
├── benchmarks/v3/          # Suite v3 YAML molecule definitions
├── releases/
│   ├── v3/db/              # Suite v3 (STO-3G) entry JSONs
│   └── v3.1/db/            # Suite v3.1 (6-31G) entry JSONs
├── scripts/
│   ├── run_suite_v3.py     # Full suite runner
│   ├── generate_entry_v3.py # Single-entry generator
│   ├── export_leaderboard_v3.py
│   └── publish_leaderboard.py
├── website/                # Next.js 15 site (Vercel)
└── schema/schema_v3.json   # Entry JSON schema
```

---

## 6. Troubleshooting

**PySCF fails on Windows native**
Use WSL + Ubuntu as described above. PySCF does not have Windows wheels.

**`conda: command not found`**
Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) and restart your terminal.

**Hash mismatch on reproduce**
Ensure you are using the exact `--seed 42 --multistart 10` flags and the same tool versions
listed in the artifact's `provenance.tool_versions`.
