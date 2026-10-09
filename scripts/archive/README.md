# scripts/archive — retired one-off and exploratory scripts

Nothing in this directory is referenced by the pipeline, the Makefile, CI, the docs, or
the website. Each script was written for a task that is finished (v1-era entry
generators, migrations that have been run, diagnostics for bugs that have been fixed,
a full-pipeline shell script that calls generators which no longer exist).

They are kept in the tree rather than deleted so that the history of how an early entry
or a diagnosis was produced stays greppable without archaeology in `git log`. They are
**not maintained**, may not run against the current package, and should not be used as
a starting point: the current pipeline is `scripts/generate_entry_v4.py`, the verifier
is `scripts/verify_entry.py`, and the v3 reproduction path is `scripts/generate_entry_v3.py`
with `requirements-v3.txt`.

Moved here from `scripts/` (and one from the repo root) on 2026-09-04.

## 2026-10-09 — the v2 fulfilment and publish chain

`job_poller.py`, `generate_leaderboard.py` and `publish_leaderboard_live.py` were the
automated path from a paid order to a published result. By Suite v4 none of it worked, and
part of it was dangerous:

* `job_poller.py` ran `scripts/run_standard_suite.py` against the v2 suite. That script no
  longer exists, so every claimed order was marked failed, and the admin email said no
  action was required.
* Had a run succeeded, the next two steps would have rebuilt the leaderboard from
  `releases/v2/db` (STO-3G) and published it over the live v4 table, dropping the
  entry_id, margin, robustness, noise and stop columns. Three keys this chain wrote on an
  earlier run (`research_entries_included`, `certified_receipts_count`,
  `min_trust_level`) were still in the live metadata on 2026-10-08.

Paid checkout is paused and orders start with an application (`/certify`). The live
leaderboard is published only by `scripts/export_leaderboard_v4.py` followed by
`scripts/publish_leaderboard.py`.
