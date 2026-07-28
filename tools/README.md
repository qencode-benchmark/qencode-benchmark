# QEncode reproducibility checker

A tiny, dependency-light tool that answers one question: **will your VQE give the
same answer if you run it again?**

## Why

Threaded BLAS (the linear algebra under NumPy/SciPy) sums floating-point numbers in
whatever order the CPU cores finish. That perturbs an energy in its last bits. A
gradient-free optimizer — COBYLA, Nelder-Mead, Powell, SPSA — chooses its next step
by *comparing* energies, so that noise can push it into a different local minimum of
a multi-modal landscape. The result: the same command, same seed, same code returns
a different number on a different machine, or under different load. **Fixing your
random seed does not protect you**, because the non-determinism is in the arithmetic,
not the RNG.

We found this in our own published benchmark numbers, traced it, and fixed the whole
suite. The story:
https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug

## Use

```bash
python check_vqe_reproducibility.py          # instant: checks your config, gives a verdict + the fix
python check_vqe_reproducibility.py --live   # also attempts a live reproduction on your machine
```

Needs only NumPy and SciPy. `pip install threadpoolctl` gives a precise BLAS thread
count instead of an inferred one.

## What it does and does not claim

- The **verdict is configuration-based** (is your BLAS multi-threaded?), which is
  always answerable and reliable.
- The **`--live` check is an attempt**, not a proof either way: whether the failure
  reproduces on a given machine depends on the BLAS build, core count, problem size,
  and load. It may show nothing even when your configuration is at risk — so a quiet
  `--live` run is **not** a clean bill of health. The tool says so.

## The fix

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
