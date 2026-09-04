"""The packaging must not change a single published number.

Entries are content-hashed and signed, and the leaderboard is keyed on those hashes. A
refactor that altered one output byte would invalidate every entry in the database, and
it would do so silently — the pipeline would still run, still print success, and still
write a plausible-looking file.

So every way of invoking the pipeline — the compatibility shim at the documented path,
the console entry point, and the Python API — is run on H2 and checked three ways:

  * all three produce the same content hash as each other, in one interpreter
  * the energy matches the published H2 JW/UCCSD entry to 1e-6 Ha, on any machine
  * on the reference environment, the hash equals a pinned value

    pytest tests/test_packaging.py -v

The first version of this file pinned one hash unconditionally. The hash covers
provenance.tool_versions, so that value was specific to the environment it was recorded
in — the drifted development stack — and it failed the first time the suite ran on the
pinned reference stack in CI. The reference-environment pin is therefore gated on the
generated entry actually recording the reference versions, and the two checks that do
not depend on the environment always run.

The environment guard is bypassed deliberately (--allow-dirty --allow-env-drift). This is
a packaging test; reproducibility is what tools/check_vqe_reproducibility.py and
tests/test_pipeline_regressions.py are for.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# The hash the shim produces on the reference environment: Linux, and exactly the
# versions in requirements-v4.txt with Python 3.11.15. Measured in a venv built the way
# CI builds one. Only asserted when the generated entry records those versions.
REFERENCE_H2_HASH = "375960cd1eb599cba7452d036b850a85e468f5e0ae1b62c76dccc1447cedd77e"
REFERENCE_VERSIONS = {"python": "3.11.15", "pyscf": "2.6.2", "pennylane": "0.45.0",
                      "openfermion": "1.6.1", "numpy": "2.2.6", "scipy": "1.13.1"}

PUBLISHED_H2 = next(REPO.glob("releases/v4/db/H2_ccpvdz_JW_UCCSD_*.json"))

COMMON = ["--molecule", "H2", "--allow-dirty", "--allow-env-drift"]


def _entry_in(out_dir: Path) -> dict:
    files = sorted(out_dir.glob("*.json"))
    assert files, "the pipeline wrote no entry to %s" % out_dir
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _run(cmd, out_dir):
    env = dict(os.environ)
    env["QENCODE_REPO"] = str(REPO)
    proc = subprocess.run(cmd + COMMON + ["--out-dir", str(out_dir)],
                          cwd=str(REPO), env=env,
                          capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, "command failed: %s\n%s" % (cmd, proc.stdout[-2000:])


@pytest.fixture(scope="module")
def entries(tmp_path_factory):
    """One H2 run through each code path, all in this interpreter's environment."""
    import qencode

    shim = tmp_path_factory.mktemp("shim")
    _run([sys.executable, str(REPO / "scripts" / "generate_entry_v4.py")], shim)

    cli = tmp_path_factory.mktemp("cli")
    _run([sys.executable, "-m", "qencode.cli", "run"], cli)

    api_dir = tmp_path_factory.mktemp("api")
    api = qencode.generate_entry(molecule="H2", out_dir=str(api_dir),
                                 allow_dirty=True, allow_env_drift=True)
    return {"shim": _entry_in(shim), "cli": _entry_in(cli), "api": api}


def _hash(e):
    return e["provenance"]["entry_hash_sha256"]


def test_shim_at_documented_path(entries):
    """scripts/generate_entry_v4.py is referenced by the Dockerfile, CI, the QUICKSTART
    and several published posts, so it has to keep working."""
    assert _hash(entries["shim"])


def test_all_three_code_paths_agree_with_each_other(entries):
    hashes = {k: _hash(v) for k, v in entries.items()}
    assert len(set(hashes.values())) == 1, hashes


def test_every_code_path_reproduces_the_published_energy(entries):
    """H2 tapers to one qubit and converges exactly, so this holds on any machine."""
    published = json.loads(PUBLISHED_H2.read_text())["results"]["vqe"]["best_energy_hartree"]
    for name, e in entries.items():
        assert abs(e["results"]["vqe"]["best_energy_hartree"] - published) < 1e-6, name


def test_reference_environment_hash(entries):
    """On the reference stack the hash is a fixed value. Elsewhere the two tests above
    still hold; only this pin is skipped, and it says why."""
    recorded = dict(entries["shim"]["provenance"]["tool_versions"])
    recorded.pop("git_commit", None)
    if recorded != REFERENCE_VERSIONS:
        pytest.skip("not the reference environment: %s" % {
            k: (recorded.get(k), REFERENCE_VERSIONS[k])
            for k in REFERENCE_VERSIONS if recorded.get(k) != REFERENCE_VERSIONS[k]})
    assert _hash(entries["shim"]) == REFERENCE_H2_HASH


def test_console_entry_point(entries):
    assert _hash(entries["cli"]) == _hash(entries["shim"])


def test_python_api(entries):
    import qencode

    entry = entries["api"]
    assert qencode.entry_hash(entry) == _hash(entries["shim"])
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
