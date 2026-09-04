# Getting Started → moved

Setup and first run now live at **[QUICKSTART.md](../QUICKSTART.md)** in the repository
root, which covers installation (pip, Docker, clone), Windows via WSL2, the first entry,
verification and troubleshooting in one place.

This file is a pointer. The document that used to be here described **Suite v3.1** and was
last substantively edited on 2026-05-12. It had not merely aged — following it failed:

- `pip install -r requirements.txt` — **there is no `requirements.txt` in this
  repository.** The pinned files are `requirements-v4.txt` (current suite) and
  `requirements-v3.txt` (frozen v3.1 suite)
- it drove `scripts/generate_entry_v3.py` and `scripts/run_suite_v3.py` against
  `releases/v3.1/db/` at the 6-31G basis; the current suite is v4 at cc-pVDZ
- its project layout showed only the v1–v3 tree

**Reproducing the frozen v3.1 suite is still supported**, and is the one thing that page
was right about. Use `requirements-v3.txt` with `scripts/generate_entry_v3.py`; those
entries remain in `releases/v3.1/db/` and are never modified. See [VERIFY.md](VERIFY.md)
for how verification works across both suites.
