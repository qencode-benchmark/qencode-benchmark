# scripts/legacy — integrity tooling for the frozen v1 and v2 suites

These scripts validate, index, migrate and hash the **v1 (STO-3G)** and **v2** releases in
`releases/v1/` and `releases/v2/`. They are driven by the top-level `Makefile`
(`make v1`, `make v2`, `make trusted`, `make supplychain`) and by `check_all.py`, which
runs the same sequence from Python.

They are kept, not archived, because those releases are published and must stay
checkable. They are **not** part of the current pipeline: nothing under `src/`, nothing in
CI, and nothing on the website calls them. Suite v4 uses `scripts/generate_entry_v4.py`,
`scripts/verify_entry.py` and `scripts/export_leaderboard_v4.py`.

Two cautions:

- `make check` **writes** into `releases/v2/db` (`stamp_env_v2.py --write`, the content
  hashes, the manifest). Run it only when regenerating that release's integrity files.
- Schemas and catalogues for these suites are the repo-root `schema_v1.json`,
  `molecules_v1.json`, `molecules_v2.json` and `schema/schema_v2.json`.

Moved here from `scripts/` on 2026-09-04 so that `scripts/` shows the active surface.
