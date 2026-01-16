
# Release Notes

## Overview
This release introduces the **v2 database format** and a **full, reproducible supply-chain verification pipeline** for the qencode-db release artifacts. It adds deterministic build steps for indexes, reporting, auditing, trusted exports, and integrity verification (manifest + per-entry content hashes).

---

## Highlights
- **v2 schema + v2 DB artifacts**
  - v2 entries validated against `schema/schema_v2.json`.
  - Migration pipeline from v1 → v2 supported and automated.

- **Environment stamping**
  - v2 entries are stamped with environment metadata to make provenance clearer and builds easier to reproduce/inspect.

- **Trusted set export**
  - Automatically exports a **trusted subset** of v2 entries based on the configured gap threshold and required checks.
  - Produces a trusted index + trusted benchmarks CSV.

- **Supply-chain integrity**
  - Generates `manifest.json` (optionally only JSON entries) and verifies it.
  - Generates `entry_content_hashes.json` and verifies per-entry hashes.
  - Ensures the pipeline runs in the correct order so manifests reflect the current content hashes.

- **Makefile pipeline**
  - Adds a `make check` end-to-end target to run the full pipeline consistently.

---

## What’s Included
### v1
- Schema validation
- Index generation
- Benchmark reporting (CSV)
- Audit reporting (gap checks)

### v2
- Migration from v1 → v2
- Environment stamping (`--write`)
- Schema validation against `schema/schema_v2.json`
- Index generation
- Benchmark reporting (CSV)
- Audit reporting (trusted flags + gap checks)

### Trusted export (v2)
- Exports the trusted subset into `releases/v2/trusted/`
- Writes:
  - `trusted_index.json`
  - `trusted_benchmarks.csv`
  - trusted JSON entries

### Supply-chain outputs (v2)
- `releases/v2/db/entry_content_hashes.json`
- `releases/v2/db/manifest.json`
- Verification steps for both.

---

## How to Run (Quick)
From repo root:

```bash
make check



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

