# Leaderboard Rules v1

This document defines the **official rules** used to generate the QEncode benchmark leaderboard. The leaderboard ranks algorithm configurations based on standardized benchmark experiments defined by the **QEncode Standard Benchmark Suite v1**.

Only results that satisfy the eligibility criteria described below are included.

---

## Purpose

- Define which results qualify for the leaderboard.
- Define ranking categories, sorting rules, and tie-breaking.
- Document dataset versioning and the official leaderboard dataset location.

This rulebook should be referenced by the benchmark specification, the leaderboard documentation, and (when published) the whitepaper.

---

## Eligibility Criteria

A benchmark entry **qualifies for the leaderboard** if **all** of the following conditions are satisfied:

1. **Suite match** — The entry matches the Standard Benchmark Suite v1 configuration (molecule, basis, mapping, ansatz, and execution settings defined in `benchmarks/standard/suite_v1.yaml`).

2. **Trust level** — The entry has `trust_level = certified`. Trust level is assigned by the QEncode certification pipeline (`scripts/assign_trust_levels.py`); manual overrides are not allowed for official leaderboard entries.

3. **Required metrics** — All of the following metrics are present and non-missing:
   - **gap** — Energy gap (difference between VQE and exact ground-state energy; leaderboard v1 uses `gap_ideal`).
   - **circuit_depth** — Reported as `depth` in leaderboard CSVs.
   - **two_qubit_gates** — Reported as `2q_gates` in leaderboard CSVs.

4. **Schema validation** — The entry passes benchmark schema validation (e.g. `scripts/validate_benchmark_core.py` / standard suite validation).

Entries that do not satisfy these conditions are **excluded** from the leaderboard.

---

## Ranking Scope

Leaderboard rankings are computed **per molecule**.

- Example: H2 leaderboard, BeH2 leaderboard.
- **Cross-molecule rankings are not defined** in version 1.

---

## Leaderboard Categories

The leaderboard contains **three** ranking categories.

### Category 1 — Best Accuracy

| Item | Rule |
|------|------|
| **Primary metric** | Lowest energy gap |
| **Sorting** | Sort by `gap` ascending (lower is better). |
| **Tie-breaking** | 1) Lowest circuit depth (`depth`). 2) Lowest two-qubit gates (`2q_gates`). 3) If still tied, earlier timestamp or lexicographic entry identifier. |

### Category 2 — Lowest Hardware Cost

| Item | Rule |
|------|------|
| **Primary metric** | Two-qubit gate count |
| **Sorting** | Sort by `two_qubit_gates` (CSV column `2q_gates`) ascending. |
| **Tie-breaking** | 1) Lowest circuit depth. 2) Lowest energy gap. 3) If still tied, earlier timestamp or lexicographic entry identifier. |

### Category 3 — Balanced Score

| Item | Rule |
|------|------|
| **Formula** | `balanced_score = gap × depth` (lower is better). |
| **Sorting** | Sort by `balanced_score` ascending. |
| **Tie-breaking** | 1) Lowest two-qubit gates. 2) Lowest gap. 3) If still tied, earlier timestamp or lexicographic entry identifier. |

The balanced-score formula is implemented in `qencode.leaderboard.model.compute_balanced_score`.

---

## Leaderboard Versioning

Leaderboard **rules** are versioned independently of the benchmark suite.

- **Current version:** Leaderboard Rules **v1**.
- Changes to ranking formulas, eligibility criteria, or tie-breaking rules **must** create a new rules version (e.g. `LEADERBOARD_RULES_V2.md`).

---

## Leaderboard Dataset

Leaderboard results are generated from **certified** benchmark entries and exported to the following dataset files:

| File | Description |
|------|--------------|
| `datasets/leaderboard/leaderboard_accuracy.csv` | Best-accuracy rankings (per molecule). |
| `datasets/leaderboard/leaderboard_hardware_cost.csv` | Lowest hardware-cost rankings (per molecule). |
| `datasets/leaderboard/leaderboard_balanced.csv` | Best balanced-score rankings (per molecule). |

These files are produced by:

```bash
python scripts/generate_leaderboard.py
```

They are considered the **internal** leaderboard dataset. A versioned **public** release is published under `datasets/qencode_leaderboard_v1/` (see Phase 26 / release script).

---

## References

- **Benchmark specification:** `docs/BENCHMARK_SPECIFICATION_V1.md`
- **Benchmark suite:** `docs/STANDARD_SUITE_V1.md`, `benchmarks/standard/suite_v1.yaml`
- **Trust levels:** `docs/TRUST_LEVELS.md`
- **Leaderboard usage:** `docs/leaderboard.md`
- **Audit:** `scripts/audit_leaderboard.py` → `artifacts/leaderboard_audit_v1.md`
