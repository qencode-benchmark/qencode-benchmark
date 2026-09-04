"""The onboarding notebook must stay runnable, and must stay honest.

notebooks/score_your_vqe_result.ipynb is the front door for anyone who has a VQE energy
and wants to know what it is worth. If a rename in the package silently breaks it, the
first person to find out is a stranger.

Executing it here would mean adding jupyter to CI for one file, so this checks the things
that actually break instead: it is valid notebook JSON, the committed outputs are from a
clean run, every qencode name it calls still exists, and the claims it makes about
certification are the ones the trust policy allows. Executing it is a separate, manual
step, recorded in notebooks/README.md.

    pytest tests/test_notebook.py -v

Standard library only -- no nbformat, no jupyter.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NB = REPO / "notebooks" / "score_your_vqe_result.ipynb"


@pytest.fixture(scope="module")
def nb():
    return json.loads(NB.read_text(encoding="utf-8"))


def _cells(nb, kind):
    return [c for c in nb["cells"] if c["cell_type"] == kind]


def _source(cell):
    src = cell["source"]
    return src if isinstance(src, str) else "".join(src)


def test_is_valid_notebook_json(nb):
    assert nb["nbformat"] == 4
    assert nb["cells"], "notebook has no cells"
    for c in nb["cells"]:
        assert c["cell_type"] in ("markdown", "code")
        assert "source" in c


def test_committed_outputs_are_from_a_clean_run(nb):
    """Every code cell ran, and none of them raised."""
    code = _cells(nb, "code")
    assert len(code) >= 6
    errors = [o for c in code for o in c.get("outputs", [])
              if o.get("output_type") == "error"]
    assert not errors, "committed notebook contains %d error output(s): %s" % (
        len(errors), [e.get("ename") for e in errors])
    ran = [c for c in code if c.get("execution_count")]
    assert len(ran) >= len(code) - 1, (
        "%d of %d code cells have no execution count; re-run the notebook before "
        "committing" % (len(code) - len(ran), len(code)))


def test_every_qencode_name_it_uses_still_exists(nb):
    """The realistic breakage: a rename in the package. Resolve each attribute for real."""
    import qencode

    source = "\n".join(_source(c) for c in _cells(nb, "code"))
    names = sorted(set(re.findall(r"\bqencode\.([A-Za-z_][A-Za-z0-9_]*)", source)))
    assert names, "the notebook no longer calls qencode at all"
    for name in names:
        assert hasattr(qencode, name), "notebook calls qencode.%s, which no longer exists" % name

    # The scoring call is the point of the notebook; keep its keywords honest too.
    for kw in ("molecule=", "active_space=", "optimizer=", "ansatz="):
        assert kw in source, "notebook no longer passes %s to score()" % kw


def test_the_edit_me_cell_is_findable_and_minimal(nb):
    """A reader must be able to see at a glance which cell to change."""
    edit = [c for c in _cells(nb, "code") if "EDIT ME" in _source(c)]
    assert len(edit) == 1, "expected exactly one EDIT ME cell, found %d" % len(edit)
    src = _source(edit[0])
    for var in ("MY_ENERGY", "MY_MOLECULE", "MY_ACTIVE_SPACE", "MY_OPTIMIZER", "MY_ANSATZ"):
        assert var in src


def test_it_does_not_claim_a_self_reported_number_is_certified(nb):
    """Same rule the scoring report is held to, applied to the prose."""
    md = "\n".join(_source(c) for c in _cells(nb, "markdown")).lower()
    assert "not a certification" in md or "it is not a certification" in md
    for bad in ("your result is certified", "this certifies", "you are certified"):
        assert bad not in md
    # And it must say what the gap is measured against.
    assert "not against experiment" in md


def test_it_states_the_amplification_finding_with_its_numbers(nb):
    """The fragility assessment is the part a reader cannot get elsewhere, so the
    notebook has to explain it rather than just print a flag."""
    md = "\n".join(_source(c) for c in _cells(nb, "markdown"))
    assert "3.4 × 10⁻⁸" in md and "8.8 × 10⁻⁴" in md
    assert "conjunction" in md.lower()


def test_setup_instructions_match_the_published_package_name(nb):
    md = "\n".join(_source(c) for c in _cells(nb, "markdown"))
    import tomllib

    name = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["name"]
    assert "pip install %s" % name in md, "setup cell does not install %r" % name
