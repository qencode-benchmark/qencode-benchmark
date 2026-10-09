"""The verifier must fail an entry it can see was tampered with.

The 2026-10-08 audit edited copies of a published entry and ran scripts/verify_entry.py on
each. It printed "MISMATCH" for a zeroed hash and then reported PASS with exit code 0; it
passed an entry whose tier had been flipped, one whose reference block had been deleted,
and -- in certification mode, the mode recommended for outside verifiers -- one whose
energy had been moved by 5 mHa. The hash was computed and shown, but nothing depended on
it.

These run the verifier's no-rerun checks (--hash-only) as a subprocess on edited copies,
so they need no chemistry stack and take seconds. What they cannot catch, by design: an
edit that rewrites every dependent number consistently and recomputes the hash. The hash
is a checksum; only a signature, or re-running the entry, detects that.

    pytest tests/test_verify_entry_gates.py -v

Standard library only.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VERIFIER = REPO / "scripts" / "verify_entry.py"
SOURCE = REPO / "releases" / "v4" / "db" / "H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json"


def _verifier_module():
    spec = importlib.util.spec_from_file_location("verify_entry", VERIFIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VE = _verifier_module()


def _run(entry, tmp_path, *flags):
    path = tmp_path / "entry.json"
    path.write_text(json.dumps(entry))
    return subprocess.run([sys.executable, str(VERIFIER), str(path), *flags],
                          capture_output=True, text=True)


def _rehash(entry):
    entry["provenance"]["entry_hash_sha256"] = VE.stable_hash(VE._strip_volatile(entry))
    return entry


def _as_own_unsigned_entry(entry):
    """An edited entry re-hashed and stripped of the project signature: what someone who
    generated their own entry would hold. Its signature would no longer verify, which is
    the point of signing, so tests of other behaviour must remove it."""
    _rehash(entry)
    entry["trust"]["signature_b64"] = None
    entry["trust"]["signing_key_id"] = None
    return entry


@pytest.fixture
def entry():
    return json.loads(SOURCE.read_text())


def test_an_untouched_entry_passes(entry, tmp_path):
    r = _run(entry, tmp_path, "--hash-only")
    assert r.returncode == 0, r.stdout


def test_every_published_v4_entry_passes_the_checks_that_need_no_rerun():
    failed = []
    for p in sorted((REPO / "releases" / "v4" / "db").glob("*.json")):
        d = json.loads(p.read_text())
        hash_ok = VE.tamper_check(d)[0]
        cons_ok, lines = VE.consistency_check(d)
        if not (hash_ok and cons_ok):
            failed.append((p.name, hash_ok, lines))
    assert not failed, failed


def _edit(path_and_value):
    def apply(d):
        *keys, last = path_and_value[0]
        for k in keys:
            d = d[k]
        if path_and_value[1] is _DELETE:
            del d[last]
        elif callable(path_and_value[1]):
            d[last] = path_and_value[1](d[last])
        else:
            d[last] = path_and_value[1]
    return apply


_DELETE = object()

# (case, edit, recompute the hash afterwards?)
TAMPERS = [
    ("hash zeroed",            (("provenance", "entry_hash_sha256"), "0" * 64),        False),
    ("energy moved, no rehash", (("results", "vqe", "best_energy_hartree"), lambda e: e - 5e-3), False),
    ("energy moved, rehashed", (("results", "vqe", "best_energy_hartree"), lambda e: e - 5e-3), True),
    ("tier flipped, rehashed", (("results", "quality", "trusted"), False),             True),
    ("trust level flipped",    (("trust", "level"), "validated"),                      True),
    ("reference deleted",      (("results", "reference"), _DELETE),                    True),
    ("gap edited, rehashed",   (("results", "quality", "abs_vqe_exact_gap"), lambda g: g + 1e-3), True),
]


@pytest.mark.parametrize("case,edit,rehash", TAMPERS, ids=[t[0] for t in TAMPERS])
def test_a_tampered_entry_fails(entry, tmp_path, case, edit, rehash):
    d = copy.deepcopy(entry)
    _edit(edit)(d)
    if rehash:
        # Unsigned, so the case is caught by the consistency check alone, not by the
        # signature (tests/test_signing.py covers that path).
        _as_own_unsigned_entry(d)
    r = _run(d, tmp_path, "--hash-only")
    assert r.returncode == 1, f"{case}: verifier exited {r.returncode}\n{r.stdout}"


def test_certification_mode_refuses_a_hash_mismatch_before_re_running(entry, tmp_path):
    d = copy.deepcopy(entry)
    d["provenance"]["entry_hash_sha256"] = "0" * 64
    r = _run(d, tmp_path, "--mode", "certification")
    assert r.returncode == 1
    assert "Running:" not in r.stdout, "the generator was started on a tampered entry"


def test_an_unsigned_entry_passes_unless_a_signature_is_required(entry, tmp_path):
    d = _as_own_unsigned_entry(copy.deepcopy(entry))
    assert _run(d, tmp_path, "--hash-only").returncode == 0
    assert _run(d, tmp_path, "--hash-only", "--require-signature").returncode == 1


def test_unsupported_schema_is_refused(entry, tmp_path):
    d = copy.deepcopy(entry)
    d["schema_version"] = "2.0.0"
    r = _run(d, tmp_path, "--hash-only")
    assert r.returncode == 1
    assert "not supported" in r.stdout


def test_dry_run_takes_the_seed_from_the_entry(entry, tmp_path):
    d = copy.deepcopy(entry)
    d["run_config"]["seed"] = 7
    _as_own_unsigned_entry(d)
    r = _run(d, tmp_path, "--dry-run")
    assert r.returncode == 0, r.stdout
    assert "--seed 7" in r.stdout
