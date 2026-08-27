"""The packaging must not change a single published number.

Entries are content-hashed and signed, and the leaderboard is keyed on those hashes. A
refactor that altered one output byte would invalidate every entry in the database, and
it would do so silently — the pipeline would still run, still print success, and still
write a plausible-looking file.

So this pins the H2 content hash and checks that every way of invoking the pipeline still
produces it: the compatibility shim at the documented path, the console entry point, and
the Python API.

    pytest tests/test_packaging.py -v

The environment guard is bypassed deliberately (--allow-dirty --allow-env-drift). This
test compares three code paths against each other in one interpreter, so a drifted stack
affects all of them identically; it is a packaging test, not a reproducibility test.
Reproducibility is what tools/check_vqe_reproducibility.py is for.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Recorded from the pipeline before it was moved into the package, in the same
# interpreter, and re-verified after. If this changes, something about the computation
# changed and not merely where the files live.
H2_HASH = "bf184258d3c03986821cc389bd1fc4e46ccc2680955def87e420520c3448f440"

COMMON = ["--molecule", "H2", "--allow-dirty", "--allow-env-drift"]


def _hash_of(out_dir: Path) -> str:
    files = sorted(out_dir.glob("*.json"))
    assert files, "the pipeline wrote no entry to %s" % out_dir
    entry = json.loads(files[-1].read_text(encoding="utf-8"))
    return entry["provenance"]["entry_hash_sha256"]


def _run(cmd, out_dir):
    env = dict(os.environ)
    env["QENCODE_REPO"] = str(REPO)
    proc = subprocess.run(cmd + COMMON + ["--out-dir", str(out_dir)],
                          cwd=str(REPO), env=env,
                          capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, "command failed: %s\n%s" % (cmd, proc.stdout[-2000:])


def test_shim_at_documented_path(tmp_path):
    """scripts/generate_entry_v4.py is referenced by the Dockerfile, CI, the QUICKSTART
    and several published posts, so it has to keep working."""
    _run([sys.executable, str(REPO / "scripts" / "generate_entry_v4.py")], tmp_path)
    assert _hash_of(tmp_path) == H2_HASH


def test_console_entry_point(tmp_path):
    _run([sys.executable, "-m", "qencode.cli", "run"], tmp_path)
    assert _hash_of(tmp_path) == H2_HASH


def test_python_api(tmp_path):
    import qencode

    entry = qencode.generate_entry(
        molecule="H2", out_dir=str(tmp_path), allow_dirty=True, allow_env_drift=True)
    assert qencode.entry_hash(entry) == H2_HASH
    assert qencode.gap_mha(entry) is not None


def test_threads_are_pinned_on_import():
    """Importing the package must pin BLAS before anything can import numpy."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import qencode, os; print(os.environ['OMP_NUM_THREADS'], qencode.threads_pinned())"],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["1", "True"]


def test_catalogue_is_reachable():
    """Both catalogues must resolve, so a wheel with no checkout can still generate."""
    from qencode._paths import data_file

    v4 = data_file("molecules_v4.json")
    assert v4 is not None and v4.is_file()
    entries = json.loads(v4.read_text())["entries"]
    assert len(entries) >= 16
    assert data_file("molecules_v3.json") is not None


def test_reading_an_entry_needs_no_chemistry_stack():
    """Importing qencode and reading an entry must not pull in pyscf or pennylane —
    otherwise a five-second leaderboard script costs a minute of imports."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys, qencode; "
         "print(any(m in sys.modules for m in ('pyscf', 'pennylane', 'openfermion')))"],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"
