# QEncode Benchmark Leaderboard

The QEncode leaderboard summarizes **certified** benchmark results across three categories. Official ranking rules and eligibility criteria are defined in **`docs/LEADERBOARD_RULES_V1.md`**.

Public leaderboard and onboarding:

- Leaderboard: https://www.qencode-benchmark.org/leaderboard
- Pricing / certification: https://www.qencode-benchmark.org/pricing
- Apply for access: https://www.qencode-benchmark.org/apply

Benchmark methodology (fixed suite, fixed constraints, required metrics, reproducibility) is defined in `docs/BENCHMARK_SPECIFICATION_V1.md`.

- **Best Accuracy** — lowest energy gap.
- **Lowest Hardware Cost** — lowest two-qubit gate count.
- **Best Balanced Score** — lowest `gap × depth` (accuracy × circuit cost).

All leaderboard entries are filtered to `trust_level = certified` (see `docs/TRUST_LEVELS.md`).

---

## Generating the leaderboard

1. Generate leaderboard datasets (CSV):

```bash
python scripts/generate_leaderboard.py
```

This writes:

- `datasets/leaderboard/leaderboard_accuracy.csv`
- `datasets/leaderboard/leaderboard_hardware_cost.csv`
- `datasets/leaderboard/leaderboard_balanced.csv`

2. Generate the Markdown report:

```bash
python scripts/generate_leaderboard_report.py
```

This writes:

- `artifacts/benchmark_leaderboard.md`

---

## Example (H2)

**Best Accuracy**

| Rank | Molecule | Mapping | Ansatz | Gap |
|------|----------|---------|--------|-----|
| 1 | H2 | BK | UCCSD | 0.002 (example) |

**Lowest Hardware Cost**

| Rank | Molecule | Mapping | Ansatz | 2Q Gates |
|------|----------|---------|--------|----------|
| 1 | H2 | Parity | HEA | 12 (example) |

**Best Balanced Score (gap × depth)**

| Rank | Molecule | Mapping | Ansatz | Score |
|------|----------|---------|--------|-------|
| 1 | H2 | BK | UCCSD | 0.14 (example) |

Actual values come from the generated CSV files.

---

## Dashboard view

The Streamlit app exposes a **Leaderboard** tab:

```bash
streamlit run scripts/streamlit_app.py
```

Open the **Leaderboard** page to:

- Filter by molecule.
- View accuracy, hardware cost, and balanced-score tables.

---

## API

Python-level API for programmatic access:

```python
from qencode.api.leaderboard_api import (
    get_accuracy_leaderboard,
    get_cost_leaderboard,
    get_balanced_leaderboard,
)

acc = get_accuracy_leaderboard(molecule="H2", limit=10)
```

Each function returns a JSON-serializable dict with a `rankings` list suitable for external tools or future HTTP endpoints.

---

## Public dataset release (v1)

To publish a versioned snapshot for external users:

```bash
python scripts/release_leaderboard_v1.py
```

This populates **`datasets/qencode_leaderboard_v1/`** with:

- `leaderboard_accuracy.csv`, `leaderboard_hardware_cost.csv`, `leaderboard_balanced.csv`
- `benchmark_leaderboard.md`
- `leaderboard_metadata.json` (suite_version, leaderboard_rules, generation_date, entries_included, trust_filter, provenance)

Optionally run the audit before release: `python scripts/audit_leaderboard.py` (writes `artifacts/leaderboard_audit_v1.md`).

