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
