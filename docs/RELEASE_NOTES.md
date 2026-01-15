# Release Notes — qencode-db

## v2.0.0-alpha
Status: **Alpha** (schema v2 is validated and generated from v1; API/layout may evolve)

### What this release includes
- **Schema v2**: `schema/schema_v2.json`
- **Deterministic v1 → v2 migration**:
  - Script: `scripts/migrate_v1_to_v2.py`
  - Output: `releases/v2/db/`
- **v2 tooling**
  - Validate: `scripts/validate_schema_v2.py`
  - Index: `scripts/build_index_v2.py` → `releases/v2/db/index.json`
  - Benchmarks: `scripts/report_benchmarks_v2.py --csv` → `releases/v2/db/benchmarks.csv`
  - Audit: `scripts/audit_db_v2.py`
- **Unified repo check**
  - Script: `scripts/check_all.py`
  - Runs: v1 validate/index/bench/audit + v2 migrate/validate/index/bench/audit

### Canonical fields (v2)
- Canonical VQE: `results.vqe`
- Reference energies: `results.reference`
- Quality/trust metadata: `results.quality`
  - `trusted` indicates benchmark-grade entries
  - gap threshold is controlled by the migration/check scripts (default `0.01`)

### Known limitations (alpha)
- Some entries are **valid but incomplete** (e.g., missing VQE or missing exact); these are marked as not trusted.
- Legacy fields may exist for traceability; legacy is non-canonical.

### How to use
Generate + validate + index + benchmarks:
```bash
python3 scripts/check_all.py --gap-threshold 0.01

