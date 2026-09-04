"""The website may not quote a reference energy the package disagrees with.

`qencode.score` reads src/qencode/data/references_v4.json. The website reads its own copy
at website/public/data/references_v4.json, because the package file lives outside the
Next.js project root and would not be traced into the serverless bundle.

Two copies of the same numbers is one too many unless something checks they agree. If the
suite is ever regenerated and only one copy is updated, the site would publish exact
ground-state energies that the tool scores against differently — a silent, invisible
disagreement in the one number the whole comparison rests on.

    pytest tests/test_website_references.py -v

Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "src" / "qencode" / "data" / "references_v4.json"
WEB = REPO / "website" / "public" / "data" / "references_v4.json"


def test_both_copies_exist():
    assert PKG.is_file(), "the packaged reference table is missing"
    assert WEB.is_file(), (
        "the website copy is missing; run: "
        "cp src/qencode/data/references_v4.json website/public/data/")


def test_the_two_copies_are_byte_identical():
    assert WEB.read_bytes() == PKG.read_bytes(), (
        "website/public/data/references_v4.json has drifted from the packaged table. "
        "Regenerate with `python tools/build_reference_table.py`, then copy it to "
        "website/public/data/.")


def test_the_website_copy_is_well_formed():
    """A structural check, so a truncated or half-written copy fails here rather than
    at request time on the live site."""
    t = json.loads(WEB.read_text(encoding="utf-8"))
    assert t["schema"] == "qencode-references/1"
    assert len(t["references"]) == 16
    assert t["n_source_entries"] == 54
    assert t["certification_threshold_ha"] == 0.01
    assert t["chemical_accuracy_ha"] == 1.6e-3

    for r in t["references"]:
        for field in ("molecule", "basis", "geometry", "active_electrons",
                      "active_orbitals", "orbital_optimization",
                      "exact_qubit_ground_energy_hartree", "n_published_entries"):
            assert field in r, "%s missing %s" % (r.get("molecule"), field)
        assert r["exact_qubit_ground_energy_hartree"] < 0, r["molecule"]
        assert r["n_published_entries"] >= 1, r["molecule"]


@pytest.mark.parametrize("field", ["exact_qubit_ground_energy_hartree",
                                   "casci_ground_energy_hartree"])
def test_energies_match_entry_by_entry(field):
    """Not just the same file — the same numbers, checked per molecule."""
    pkg = {(r["molecule"], r["orbital_optimization"]): r[field]
           for r in json.loads(PKG.read_text(encoding="utf-8"))["references"]}
    web = {(r["molecule"], r["orbital_optimization"]): r[field]
           for r in json.loads(WEB.read_text(encoding="utf-8"))["references"]}
    assert pkg == web
