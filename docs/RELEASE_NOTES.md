# Release Notes

This repository contains a small benchmark database for quantum encoding / VQE experiments, stored as JSON entries with validation tooling, indexes, CSV reports, and (v2) provenance + supply-chain artifacts.

---

## v1.0.0

### Highlights
- Validated all v1 entries against the v1 schema (`schema_v1.json`).
- Rebuilt `releases/v1/db/index.json` and `releases/v1/db/benchmarks.csv`.
- Added auditing checks to flag missing fields, legacy fields, and large VQE-vs-exact gaps.
- Canonicalization policy applied where appropriate (e.g., remove/clean inconsistent or non-authoritative values rather than guessing).

### What’s included
- `releases/v1/db/` entries (JSON)
- `releases/v1/db/index.json`
- `releases/v1/db/benchmarks.csv`
- Tooling: schema validator, index builder, benchmarks report, audit script

---

## v2.0.0-alpha

### Highlights
- Introduced schema v2 (`schema/schema_v2.json`).
- Added v1 → v2 migration tooling.
- Added v2-specific tooling:
  - v2 schema validator
  - v2 index builder
  - v2 benchmarks reporter (with `trusted` + flags)
  - v2 audit script
- Added provenance stamping into v2 entries (environment fingerprint) to improve reproducibility.
- Added “trusted” export pipeline to produce a strict benchmark subset.

### Trusted benchmark set (v2)
A v2 entry is considered **trusted** when it satisfies the trust policy rules (see `docs/TRUST_POLICY.md`). The trusted export produces:
- `releases/v2/trusted/` JSON entries (trusted subset)
- `releases/v2/trusted/trusted_index.json`
- `releases/v2/trusted/trusted_benchmarks.csv`

### Supply-chain artifacts (v2)
To support integrity verification and reproducible distribution:
- `releases/v2/db/manifest.json`  
  A snapshot manifest with hashes over files under `releases/v2/db`.
- `releases/v2/db/entry_content_hashes.json`  
  Canonical content hashes for each v2 entry, with verification tooling.

### Recommended verification command
From repo root:

```bash
python3 scripts/check_all.py --gap-threshold 0.01 \
  --stamp-env \
  --export-trusted --trusted-out-dir releases/v2/trusted \
  --trusted-require-gap-check --trusted-clean-out-dir \
  --supply-chain --manifest-only-json-entries --verify-entry-hashes

