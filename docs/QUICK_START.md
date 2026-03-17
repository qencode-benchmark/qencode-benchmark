# Quick Start — Run the official QEncode benchmark

This quick start runs the **official Standard Benchmark Suite v1** and produces the **official leaderboard dataset** in one command.

If you haven't installed dependencies yet, see `docs/GETTING_STARTED.md` first.

At minimum, Standard Suite v1 requires **PyYAML**:

```powershell
python -m pip install pyyaml
```

---

## One command (recommended)

From the repo root:

```powershell
python scripts/run_qencode_benchmark.py
```

This runs:

1. Standard Suite v1 (`scripts/run_standard_suite.py`)
2. Leaderboard CSV generation (`scripts/generate_leaderboard.py`)
3. Leaderboard Markdown report (`scripts/generate_leaderboard_report.py`)
4. Leaderboard audit (`scripts/audit_leaderboard.py`)
5. Public dataset release (`scripts/release_leaderboard_v1.py`)

Outputs:

- `datasets/leaderboard/` (internal CSVs)
- `artifacts/benchmark_leaderboard.md`
- `artifacts/leaderboard_audit_v1.md`
- `datasets/qencode_leaderboard_v1/` (public release snapshot)

---

## Run a single molecule

```powershell
python scripts/run_qencode_benchmark.py --molecule H2
```

---

## Run with workers (parallel suite execution)

```powershell
python scripts/run_qencode_benchmark.py --workers 8
```

---

## Skip the audit

```powershell
python scripts/run_qencode_benchmark.py --skip-audit
```

---

## Don’t resume (force re-run suite jobs)

```powershell
python scripts/run_qencode_benchmark.py --no-resume
```

---

## Advanced (paths and scoring)

```powershell
python scripts/run_qencode_benchmark.py `
  --db-dir releases/v2/db `
  --leaderboard-dir datasets/leaderboard `
  --gap-key gap_ideal
```

