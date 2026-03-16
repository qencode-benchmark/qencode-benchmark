# Result Trust Levels (Phase 15)

Benchmark entries are labeled with a **trust level**: **Experimental**, **Validated**, or **Certified**. Use this to filter results in the dashboard and to restrict official rankings to certified results only.

---

## The three levels

| Level | When it applies | Use case |
|-------|------------------|----------|
| **Experimental** | Default for any entry that doesn’t meet validated or certified criteria. | Exploratory runs, incomplete data, one-off experiments. |
| **Validated** | Entry has a complete benchmark core (molecule, basis, mapping, ansatz, vqe_energy, exact_energy, at least one gap), and all required fields are present. | Internal comparison, “good enough” for analysis. |
| **Certified** | Validated **and** `results.quality.trusted` true, gap within threshold, **and** (if a standard suite is used) the entry is part of the official suite grid. | Official rankings, reports, citations. |

Determination is done by `src/qencode/trust.py`: `validate_for_validated()`, `validate_for_certified()`, and `determine_trust_level()`. The standard suite is used to decide “in suite” via `certification.is_entry_in_standard_suite()`.

---

## Assigning trust levels

After running benchmarks (e.g. `run_standard_suite.py` or `run_benchmark.py`), assign trust levels so the **`trust`** block is written into each entry JSON:

```bash
python scripts/assign_trust_levels.py --db-dir releases/v2/db
```

Options: `--file` (single file), `--suite` (suite YAML path), `--gap-threshold` (for certified gap check). The script writes `trust.level`, `trust.reason`, `trust.suite_version`, `trust.assigned_at` into each entry.

Sync from db-dir to SQLite (e.g. when opening the dashboard or running compare/rank) copies **trust_level** into the `benchmarks` table so filtering works.

---

## Dashboard filtering

In the Streamlit dashboard, the **Trust** sidebar filter:

- **All** — Show all entries (default).
- **Validated** — Only entries with `trust_level` in `validated` or `certified`.
- **Certified** — Only entries with `trust_level == certified`.

Use **Certified** when you want to see only official-suite, trusted results.

---

## Certified-only for official rankings

For **comparison** and **ranking**, use certified results only so that official recommendations are based on trusted, suite-aligned data:

```bash
python scripts/compare.py --molecule H2 --certified-only
python scripts/rank.py --molecule H2 --certified-only
```

- **`compare.py --certified-only`** — Passes `trust_level="certified"` into `full_comparison()`; only certified rows are used for mapping/ansatz rankings and derived metrics.
- **`rank.py --certified-only`** — Passes `trust_level="certified"` into `full_ranking()`; best mapping per ansatz, best ansatz per mapping, and noise resilience use only certified entries.

If no certified entries exist for the molecule, the comparison/ranking will be empty or minimal; run the standard suite and `assign_trust_levels.py` first.

---

## Audit

To see how many standard-suite jobs are validated vs certified and why some fail certification:

```bash
python scripts/audit_certified_results.py --db-dir releases/v2/db
```

This writes **`artifacts/certification_audit_v1.md`** with counts and failure reasons (e.g. missing trusted flag, gap over threshold, not in suite).

---

## Summary

- **Experimental** — default; no guarantee of completeness.
- **Validated** — complete benchmark core; suitable for internal use.
- **Certified** — validated + trusted + in suite (when applicable); use for **official rankings** with `--certified-only`.

See `src/qencode/trust.py` and `src/qencode/certification.py` for the exact rules and suite checks.
