"""QEncode — reproducible VQE quantum chemistry benchmarking.

An *entry* is one quantum chemistry calculation run end to end, with every input recorded
so it can be rebuilt: Hamiltonian, ansatz, optimiser, seed, package versions and code
commit, all hashed and optionally signed.

Generate one::

    from qencode import generate_entry
    entry = generate_entry(molecule="H2")
    print(entry["provenance"]["entry_hash_sha256"])

or from the shell::

    qencode run --molecule H2

Reading entries needs nothing but the standard library::

    from qencode import load_entry, gap_mha
    e = load_entry("releases/v4/db/H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_....json")
    print(gap_mha(e))

One caveat worth stating here rather than in a docstring nobody reads: a result is only
reproducible if the arithmetic is deterministic, which means single-threaded BLAS, pinned
*before* NumPy is imported. Importing this package does that for you. If you import numpy
first, it is already too late — see ``qencode.check`` or
``tools/check_vqe_reproducibility.py``.
"""
from __future__ import annotations

import os as _os

# ── Determinism, before numpy can be imported by anything below ───────────────
#
# Threaded BLAS combines partial sums in whatever order threads finish, which perturbs an
# energy in its last bits. A gradient-free optimiser picks its next step by comparing
# energies, so that 1e-16 noise decides the direction whenever two candidates are close,
# and on a multi-modal landscape one different step lands in a different local minimum.
# The same LiH command returned 8.99 mHa or 0.53 mHa before this was pinned.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import json as _json
from pathlib import Path as _Path
from typing import Any, Dict, Optional, Union

from qencode._paths import default_out_dir, is_checkout, repo_root

__version__ = "4.4.0"

__all__ = [
    "__version__",
    "generate_entry",
    "load_entry",
    "gap_mha",
    "beats_classical",
    "entry_hash",
    "repo_root",
    "default_out_dir",
    "is_checkout",
    "threads_pinned",
]


def threads_pinned() -> bool:
    """True when BLAS is restricted to one thread, which is what makes a run repeatable.

    Only meaningful if checked before NumPy initialises its thread pool; this package
    sets the variables at import, so it is true unless something set them otherwise
    first.
    """
    return all(_os.environ.get(v) == "1" for v in
               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"))


def generate_entry(molecule: str = "H2", **kwargs: Any) -> Dict[str, Any]:
    """Run the pipeline and return the entry that was written.

    Keyword arguments map onto the command line flags with underscores for dashes, so
    ``mapping="parity"`` is ``--mapping parity`` and ``ansatz_type="hea"`` is
    ``--ansatz-type hea``. ``qencode run --help`` lists them all.

    The chemistry stack (pyscf, pennylane, openfermion) is imported lazily, so importing
    ``qencode`` to read an entry stays fast.
    """
    import sys

    from qencode.pipeline import generate_entry_v4

    argv = ["qencode", "--molecule", str(molecule)]
    for key, value in kwargs.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        else:
            argv += [flag, str(value)]

    out_dir = _Path(kwargs.get("out_dir") or default_out_dir())
    before = set(out_dir.glob("*.json")) if out_dir.is_dir() else set()

    saved = sys.argv
    try:
        sys.argv = argv
        generate_entry_v4.main()
    except SystemExit as exc:
        # The pipeline is a command line tool first and exits rather than returning.
        # A zero exit is the success path; anything else is a real failure.
        code = exc.code if exc.code is not None else 0
        if code != 0:
            raise RuntimeError("entry generation failed with exit code %s" % code) from exc
    finally:
        sys.argv = saved

    after = set(out_dir.glob("*.json")) if out_dir.is_dir() else set()
    new = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if not new:
        raise RuntimeError(
            "the pipeline reported success but wrote no entry to %s" % out_dir)
    return load_entry(new[-1])


def load_entry(path: Union[str, "_Path"]) -> Dict[str, Any]:
    """Read an entry JSON. Needs no dependencies beyond the standard library."""
    return _json.loads(_Path(path).read_text(encoding="utf-8"))


def entry_hash(entry: Dict[str, Any]) -> Optional[str]:
    """The content hash an entry was published under."""
    return entry.get("provenance", {}).get("entry_hash_sha256")


def gap_mha(entry: Dict[str, Any]) -> Optional[float]:
    """Absolute VQE-to-exact energy gap in millihartree.

    This is measured against exact diagonalisation of the *same* qubit Hamiltonian in the
    same active space, not against experiment. It isolates algorithm error from basis-set
    and active-space error. See https://www.qencode-benchmark.org/leaderboard/guide
    """
    q = entry.get("results", {}).get("quality", {})
    g = q.get("abs_vqe_exact_gap")
    return None if g is None else g * 1000.0


def beats_classical(entry: Dict[str, Any]) -> Optional[bool]:
    """Whether this run recovered more correlation energy than CCSD(T).

    Usually False, and that is the honest state of the field at these sizes.
    """
    return entry.get("results", {}).get("quality", {}).get("beats_classical")
