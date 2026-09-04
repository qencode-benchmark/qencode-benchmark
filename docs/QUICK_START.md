# Quick Start → moved

The quick start now lives at **[QUICKSTART.md](../QUICKSTART.md)** in the repository root.

This file is kept because the website, `docs/SUBMISSIONS.md` and outside links pointed at
this path. It is a pointer, not a second copy — there was previously a real document here
*and* at the root *and* at `docs/GETTING_STARTED.md`: three overlapping guides that
disagreed with each other and with the code.

The version that used to be here, last substantively edited on 2026-05-26, stated:

- the environment as *PySCF 2.5.0, PennyLane 0.45, openfermion 1.7.1, NumPy 1.26.4* —
  those are the **v3** pins. `requirements-v4.txt` is pyscf 2.6.2, pennylane 0.45.0,
  openfermion 1.6.1, numpy 2.2.6, scipy 1.13.1
- `--multistart` default 5 (actually 3) and `--reps` default 4 (actually 2)
- two ansatz choices, omitting `adapt` — which is what certifies H₆, H₈ and H₁₀
- a molecule table missing H₄, C₄H₄, H₆, H₈, H₁₀ and the water dimer
- a link to `BENCHMARK_SPEC_V4.md`, a file that does not exist in this repository

Corrected in the consolidated guide rather than patched here, so there is one document to
keep right. `tests/test_docs_integrity.py` now checks the CLI defaults quoted in the docs
against the actual argument parser, and that every relative link resolves.
