"""CI names entries by filename, and a filename changes whenever an entry is regenerated.

The 2026-09-07 sector fix regenerated 18 entries. Each got a new content hash and
therefore a new filename, and the old files moved to releases/v4/db_superseded/. Three
places in CI still named the old files:

  * .github/workflows/ci.yml, two steps of the push-time regression subset
  * .github/verify_ci_entries.txt, 16 of the 40 entries the weekly job re-runs
  * tools/certification_margin.MEASURED_FRAGILE, the weekly job's known-fragile list

"File not found" counts as a failure, so the push gate was red from that commit on, every
weekly run failed, and the fragile list exempted a file that no longer existed while the
real fragile entry went unprotected. Nothing in the test suite looked. These checks do.

    pytest tests/test_ci_wiring.py -v

Standard library only.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "releases" / "v4" / "db"
SUPERSEDED = REPO / "releases" / "v4" / "db_superseded"
CI = REPO / ".github" / "workflows" / "ci.yml"
MANIFEST = REPO / ".github" / "verify_ci_entries.txt"

_ENTRY = re.compile(r"[A-Za-z0-9]+_ccpvdz_[A-Za-z0-9_]+__sha256_[0-9a-f]{16}\.json")


def _published():
    return {p.name for p in DB.glob("*.json")}


def _manifest():
    """(entries the weekly job runs, entries listed as excluded in its header)."""
    run, excluded = [], []
    for line in MANIFEST.read_text().splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            excluded += _ENTRY.findall(line)
        else:
            run.append(line.strip())
    return run, excluded


def _certification_margin():
    spec = importlib.util.spec_from_file_location(
        "certification_margin", REPO / "tools" / "certification_margin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_entry_ci_yml_names_is_published():
    named = set(re.findall(r"releases/v4/db/(" + _ENTRY.pattern + ")", CI.read_text()))
    assert named, "ci.yml no longer names any v4 entry; update this test"
    missing = sorted(named - _published())
    assert not missing, f"ci.yml names entries that are not in releases/v4/db: {missing}"


def test_every_entry_in_the_weekly_manifest_is_published():
    run, excluded = _manifest()
    missing = sorted((set(run) | set(excluded)) - _published())
    assert not missing, (
        f"{MANIFEST.relative_to(REPO)} names entries that are not in releases/v4/db "
        f"(regenerated? see releases/v4/db_superseded/README.md): {missing}")


def test_the_weekly_manifest_accounts_for_every_published_entry():
    """Each entry is either re-run weekly or listed as excluded with a reason. A new or
    regenerated entry that is in neither would silently never be verified in CI."""
    run, excluded = _manifest()
    assert len(run) == len(set(run)), "an entry is listed twice in the weekly manifest"
    unaccounted = sorted(_published() - set(run) - set(excluded))
    assert not unaccounted, f"published entries the weekly job neither runs nor excludes: {unaccounted}"


def test_the_fragile_list_ci_consumes_names_only_published_entries():
    cm = _certification_margin()
    listed = cm.measured_fragile_files(str(REPO))
    assert listed, "no entry is listed as fragile; the cross-machine table says three are"
    assert set(listed) <= _published()


def test_the_fragile_list_includes_every_cross_machine_fragile_entry():
    cm = _certification_margin()
    table = cm.cross_machine_table() or {}
    fragile = {rec.get("file") or f"{eid}.json"
               for eid, rec in (table.get("entries") or {}).items()
               if rec.get("classification") == "fragile"}
    assert fragile <= set(cm.measured_fragile_files(str(REPO)))


def test_legacy_fragile_records_point_at_a_real_file():
    """A key in the hand-recorded dict is either published or kept as the record of a
    superseded entry -- never a name that exists nowhere."""
    cm = _certification_margin()
    for name in cm.MEASURED_FRAGILE:
        assert (DB / name).exists() or (SUPERSEDED / name).exists(), name
