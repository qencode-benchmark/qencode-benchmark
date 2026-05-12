# Changelog

Full version history. For the latest release summary only, see [RELEASE_NOTES.md](RELEASE_NOTES.md).

---

## v3.1.0 (current) — 2026-05-12

### Suite v3.1 — 6-31G Basis Release

- Upgraded basis set from STO-3G to 6-31G (split-valence)
- 42 benchmark entries: 30 certified + 12 research across 7 molecules
- All 30 certified entries satisfy `beats_ccsd_t = True`
- Per-entry verification pages at `/entry/<entry_id>` on the live site
- GitHub Release with artifact ZIP at `releases/tag/v3.1.0`
- Badge renamed "Beats CCSD(T)" with clarifying tooltip

---

## v3.0.0 — Suite v3 — STO-3G Basis

- Initial Suite v3 with STO-3G basis
- 3 mappings (JW, BK, Parity), 2 ansatze (UCCSD, HEA), 6 certified molecules
- Classical comparison (CCSD(T) correlation energy) added
- Public leaderboard launched at qencode-benchmark.org

---

## v2.0.x (legacy)

### Overview
v2 database format and full, reproducible supply-chain verification pipeline: indexes, reporting, auditing, trusted exports, manifest + per-entry content hashes.

### Highlights
- v2 schema + v2 DB artifacts; migration from v1 → v2.
- Environment stamping; trusted set export; supply-chain integrity (manifest, entry_content_hashes, verification).
- Makefile pipeline: `make check`, `make release-local`, etc.

See [RELEASE_NOTES.md](RELEASE_NOTES.md) for details.

---

## v2.0.0-alpha

### Highlights
- Introduced schema v2 (`schema/schema_v2.json`).
- Added v1 → v2 migration tooling.
- Added v2-specific tooling: v2 schema validator, index builder, benchmarks reporter (with `trusted` + flags), v2 audit script.
- Added provenance stamping into v2 entries (environment fingerprint).
- Added “trusted” export pipeline to produce a strict benchmark subset.

### Trusted benchmark set (v2)
A v2 entry is considered **trusted** when it satisfies the trust policy (see [TRUSTED_POLICY.md](TRUSTED_POLICY.md)). The trusted export produces:
- `releases/v2/trusted/` JSON entries (trusted subset)
- `releases/v2/trusted/trusted_index.json`
- `releases/v2/trusted/trusted_benchmarks.csv`

### Supply-chain artifacts (v2)
- `releases/v2/db/manifest.json` — snapshot manifest with hashes over files under `releases/v2/db`.
- `releases/v2/db/entry_content_hashes.json` — canonical content hashes per v2 entry, with verification tooling.

---

## v1.0.0

### Highlights
- Validated all v1 entries against the v1 schema (`schema_v1.json`).
- Rebuilt `releases/v1/db/index.json` and `releases/v1/db/benchmarks.csv`.
- Added auditing checks to flag missing fields, legacy fields, and large VQE-vs-exact gaps.
- Canonicalization policy applied where appropriate.

### What’s included
- `releases/v1/db/` entries (JSON)
- `releases/v1/db/index.json`
- `releases/v1/db/benchmarks.csv`
- Tooling: schema validator, index builder, benchmarks report, audit script
