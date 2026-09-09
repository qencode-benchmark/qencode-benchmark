#!/usr/bin/env python
"""What is actually inside this environment, to the level that decides the last bits.

Package versions are the usual answer and they are not sufficient: two machines running
the identical pinned stack do not produce identical entries (docs/CROSS_MACHINE.md). This
reports the layer below — the C library, the BLAS kernel actually selected, and the
content hash of every shared object the numerical path goes through — so that two runs
can be compared on what matters rather than on what is convenient to record.

    python tools/reference_fingerprint.py
"""
import ctypes
import hashlib
import json
import os
import platform
import re
import sys


def _sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()[:16]


def _loaded_libraries():
    """Shared objects the process has mapped, filtered to the numerical ones."""
    interesting = ("openblas", "libm-", "libm.so", "libc.so", "libgomp",
                   "libquadmath", "libgfortran", "libstdc++")
    out = {}
    try:
        with open("/proc/self/maps") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 6:
                    continue
                path = parts[-1]
                if not path.startswith("/"):
                    continue
                base = os.path.basename(path)
                if any(k in base for k in interesting) and path not in out:
                    out[path] = _sha256(path)
    except OSError:
        pass
    return out


def _openblas_core():
    """The kernel OpenBLAS chose, asked of the library rather than inferred."""
    for line in open("/proc/self/maps"):
        if "openblas" in line.lower() and line.strip().endswith(".so"):
            path = line.split()[-1]
            try:
                lib = ctypes.CDLL(path)
            except OSError:
                continue
            for sym in ("scipy_openblas_get_corename64_", "scipy_openblas_get_corename",
                        "openblas_get_corename64_", "openblas_get_corename"):
                fn = getattr(lib, sym, None)
                if fn is None:
                    continue
                fn.restype = ctypes.c_char_p
                try:
                    return fn().decode()
                except Exception:
                    continue
    return None


def main():
    import numpy, scipy, pennylane
    try:
        import pyscf
        pyscf_v = pyscf.__version__
    except Exception:
        pyscf_v = None
    try:
        import openfermion
        of_v = openfermion.__version__
    except Exception:
        of_v = None

    # touch the numerical path so the libraries are mapped before we look
    numpy.linalg.eigh(numpy.eye(8) * 1.0)

    cpu, flags = None, set()
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name") and cpu is None:
                cpu = line.split(":", 1)[1].strip()
            elif line.startswith("flags"):
                flags = set(line.split(":", 1)[1].split())
    except OSError:
        pass

    report = {
        "python": platform.python_version(),
        "libc": " ".join(x for x in platform.libc_ver() if x) or None,
        "os": platform.platform(terse=True),
        "packages": {
            "numpy": numpy.__version__, "scipy": scipy.__version__,
            "pennylane": pennylane.__version__, "pyscf": pyscf_v, "openfermion": of_v,
        },
        "blas": {
            "openblas_core": _openblas_core(),
            "OPENBLAS_CORETYPE": os.environ.get("OPENBLAS_CORETYPE"),
            "NPY_DISABLE_CPU_FEATURES": os.environ.get("NPY_DISABLE_CPU_FEATURES"),
            "threads": os.environ.get("OMP_NUM_THREADS"),
        },
        # The host leaks through even inside a container: the kernel dispatches on the
        # real CPU. Recorded so that "same image, different processor" is visible.
        "host_cpu": cpu,
        "host_avx512": sorted(f for f in flags if f.startswith("avx512"))[:6],
        "libraries": _loaded_libraries(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
