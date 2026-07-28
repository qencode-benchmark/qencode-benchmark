# QEncode reproducibility scorecard

A tiny, dependency-light tool that answers one question: **will your VQE give the
same answer if someone else runs it — or if you run it again?**

Reproducibility is not one property. It is four, and this tool checks the ones it
can see and is honest about the ones it can't:

1. **Deterministic arithmetic.** Threaded BLAS (the linear algebra under NumPy/SciPy)
   sums floating-point numbers in whatever order the CPU cores finish. That perturbs
   an energy in its last bits. A gradient-free optimizer — COBYLA, Nelder-Mead,
   Powell, SPSA — chooses its next step by *comparing* energies, so that noise can
   push it into a different local minimum of a multi-modal landscape. **Fixing your
   random seed does not protect you**, because the non-determinism is in the
   arithmetic, not the RNG. → checkable; this drives the verdict.
2. **Recorded package versions.** A result that only reproduces on your exact stack
   isn't reproducible unless that stack is written down. → the tool shows your
   installed versions and looks for a pin file.
3. **A recorded random seed.** → the tool can't see your code; this one is on you.
4. **A recorded code version.** A clean git commit means the code that ran can be
   recovered. → checkable if you're in a git repo.

We found #1 in our own published benchmark numbers, and #2 the hard way. The story:
https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug
The four-part checklist: https://www.qencode-benchmark.org/blog/vqe-reproducibility-scorecard

## Use

```bash
python check_vqe_reproducibility.py            # the scorecard for this setup
python check_vqe_reproducibility.py --record   # also write a provenance receipt (JSON)
python check_vqe_reproducibility.py --live      # also attempt a live reproduction
```

Needs only NumPy and SciPy. `pip install threadpoolctl` gives a measured BLAS thread
count instead of an inferred one.

## What it does and does not claim

- The **determinism verdict is configuration-based** (is your BLAS multi-threaded?),
  which is always answerable and reliable.
- The **provenance checks are honest about their limits**: the tool shows your exact
  installed versions and looks for a pin file, reports your git state, and for the
  seed simply reminds you — it can't read your code. It tells you which of the four
  conditions it can see, and flags the rest.
- **`--record`** writes `qencode_reproducibility.json` — platform, thread count, every
  detected package version, and the git commit — a provenance receipt to store
  alongside your results.
- **`--live`** is an *attempt*, not a proof either way: whether the failure reproduces
  on a given machine depends on the BLAS build, core count, problem size, and load. A
  quiet `--live` run is **not** a clean bill of health. The tool says so.

## The fix (condition 1)

```python
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
import numpy as np   # everything after this is deterministic
```

It must come **before** NumPy is imported — after that, BLAS has already built its
thread pool and the variables are ignored.
