# Standard Benchmark Suite v1

**One official benchmark suite** — small, stable, reproducible, easy to explain.

---

## What it is

The Standard Benchmark Suite v1 is a **frozen definition** of canonical chemistry benchmarks. It answers:

> “What is your official standard benchmark suite?”

- **Definition:** `benchmarks/standard/suite_v1.yaml`
- **Run:** `python scripts/run_standard_suite.py`
- **Validate:** `python scripts/validate_standard_suite.py`

---

## One-sentence pitch

**Our Standard Benchmark Suite v1 contains 36 entry runs (54 cells) across H2 and BeH2, evaluated across Jordan–Wigner, Bravyi–Kitaev, and Parity mappings with UCCSD and hardware-efficient ansatzes under ideal (statevector), shot-based, and noisy settings.**

---

## What the suite includes

| Dimension   | Values |
|------------|--------|
| Molecules  | H2, BeH2 |
| Basis      | sto3g |
| Mappings   | jordan_wigner, bravyi_kitaev, parity |
| Ansatzes   | UCCSD (reps=1), hardware_efficient (reps=2) |
| Backends   | ideal (statevector), shots (8192), noisy |
| Optimizer  | COBYLA, max_iter=200 |
| Measurement| grouped |
| Mitigation | none |

- **Entry runs:** 2 × 3 × 2 = **36** (each run uses `--backend all` and fills ideal, shots, noisy).
- **Cells:** 36 × 3 = **54** (entry × backend for reporting).

---

## How to run

```bash
# Run full suite (all 36 entry runs)
python scripts/run_standard_suite.py --suite benchmarks/standard/suite_v1.yaml

# Run only one molecule
python scripts/run_standard_suite.py --molecule H2

# Dry run (list jobs only)
python scripts/run_standard_suite.py --dry-run
```

Results are written to `releases/v2/db/` (or `--out-dir`). Each run uses the existing pipeline: generate entry if needed, run VQE with `--backend all`, fill `results.benchmark_core`.

---

## How to validate

After running the suite, verify that every expected entry exists and has all required metrics:

```bash
python scripts/validate_standard_suite.py --suite benchmarks/standard/suite_v1.yaml --db-dir releases/v2/db
```

Checks:

- Every (molecule, mapping, ansatz) combination has an entry in the db dir.
- Each entry has required metrics filled: `vqe_energy`, `exact_energy`, `gap_ideal`, `gap_shots`, `gap_noisy`, `depth`, `num_2q_gates`, `terms`, `groups`.

---

## Outputs

- **Summary (stdout):** Molecules, mappings, ansatzes, backends, total runs, completed, missing.
- **Report file:** `artifacts/standard_suite_v1_report.md` (or `--report <path>`) — what the suite includes, completion status, where results live.

---

## Why it matters

- **Clean startup story** — one suite, one command.
- **Fixed benchmark identity** — no ambiguity about “the” standard set.
- **Manageable compute** — 36 runs (not hundreds).
- **Easier certification** — Phase 9 certified suite can align with this grid.
- **Easier caching and demos** — deterministic, reproducible.

For managed execution and official certification intake, use:

- https://www.qencode-benchmark.org/pricing
- https://www.qencode-benchmark.org/apply

---

## Customizing the suite

Edit `benchmarks/standard/suite_v1.yaml` to change molecules, mappings, ansatzes, backends, or required metrics. Keep a copy or tag for “v1” so the official set stays frozen; use a new file (e.g. `suite_v2.yaml`) for a new standard version.
