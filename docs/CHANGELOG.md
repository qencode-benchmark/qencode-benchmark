# Changelog

Full version history. For the latest release summary only, see [RELEASE_NOTES.md](RELEASE_NOTES.md).

> This file was not kept up to date between v3.1.0 and v4.5.0. Rather than invent
> retrospective entries, the gap is stated: the v4 suite work is recorded in
> [`V4_PLAN.md`](V4_PLAN.md), [`RELEASE_NOTES.md`](RELEASE_NOTES.md), the dated amendments
> in [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md) and the git history.

---

## v4.5.0 — 2026-09-04 — first PyPI release

**The package version now moves independently of the suite version.** Suite v4.4 (the
data — molecules, basis, active spaces) is frozen until the paper it underpins is
published. The software is not frozen, so the two numbers part company here.

### Score a VQE result without running the pipeline

- `qencode.score(energy, molecule=..., optimizer=..., ansatz=...)` reports the gap to the
  exact ground state of the same active space, which of the two thresholds it clears, the
  certification margin, whether the (optimiser, ansatz) pair makes that margin fragile
  across machines, and where the number ranks among the published entries.
- The references for all 16 suite molecules ship inside the package as a 23 KB table, so
  **scoring imports no chemistry stack** — verified against the built wheel installed with
  no dependencies at all.
- It refuses rather than guesses: a mismatched active space raises, an energy below the
  variational minimum is reported before any gap, and nothing is ever called *certified*.
- `notebooks/score_your_vqe_result.ipynb` is the walkthrough, with executed outputs.

### Packaging

- Published to PyPI via **Trusted Publishing (OIDC)** — no API token exists anywhere.
- `.github/workflows/publish.yml` builds and `twine check --strict`s on every packaging
  change, and re-verifies zero-dependency scoring against the built wheel.

### Correctness and hygiene

- **Statevector ADAPT engine now verifies `B³ = -B` for every pool operator.** Fed a
  `taper_operation` pool its closed-form exponential is not exact and it reported energies
  *below* the exact ground state; it now raises. No published entry was affected — the two
  entries using this engine (H₈, H₁₀) use the generator pool, which is filtered on exactly
  this identity.
- One definition of *certified* across the repository, pinned by a test.
- Leaderboard shows certification margin, optimiser family, chemical accuracy and measured
  cross-environment robustness per row.
- The publish path verifies TLS and no longer forwards credentials across redirects.
- `scripts/` reduced from 63 files to 17; v1/v2 tooling moved to `scripts/legacy/`.
- Test suite runs in CI for the first time: 116 tests.

---

## v3.1.0 — 2026-05-12

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
