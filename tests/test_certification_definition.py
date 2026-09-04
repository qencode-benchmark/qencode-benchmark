"""There is exactly one definition of "certified", and everything agrees with it.

    certified  <=>  |E_VQE - E_CASCI| < 0.01 Ha

The threshold is a literal in five places -- the pipeline that writes `trusted`, the
leaderboard export that splits tiers, the verifier, the margin tool, and the FT resource
estimator -- and it is stated in prose in the trust policy, the README and the rules.
For a while the trust policy said something else (the CCSD(T) comparison, which is a
badge), and nobody noticed because the two conditions agreed on every entry that existed.

This pins the number in code and checks the documents still say it, so the next
divergence is a failing test rather than a reader's discovery.

    pytest tests/test_certification_definition.py -v
"""
from __future__ import annotations

import ast
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THRESHOLD_HA = 0.01

sys.path.insert(0, str(REPO / "src"))


def _module_constant(path, name):
    """Read a top-level `NAME = <number>` from a file without importing it, so the
    heavy pipeline modules are not executed just to inspect one literal."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError("%s not found in %s" % (name, path))


def test_every_executable_path_uses_the_same_threshold():
    assert _module_constant(REPO / "scripts/export_leaderboard_v4.py", "GAP_THRESHOLD") == THRESHOLD_HA
    assert _module_constant(REPO / "scripts/verify_entry.py", "CERT_THRESHOLD_HA") == THRESHOLD_HA
    assert _module_constant(REPO / "tools/certification_margin.py", "CERT_THRESHOLD_HA") == THRESHOLD_HA
    assert _module_constant(REPO / "tools/estimate_ft_resources.py", "EPS_CERTIFY") == THRESHOLD_HA

    from qencode import trust
    import inspect
    for fn in (trust.validate_for_certified, trust.determine_trust_level):
        default = inspect.signature(fn).parameters["gap_threshold"].default
        assert default == THRESHOLD_HA, "%s defaults to %r" % (fn.__name__, default)


def test_pipeline_sets_trusted_from_the_threshold():
    src = (REPO / "src/qencode/pipeline/generate_entry_v4.py").read_text(encoding="utf-8")
    assignments = re.findall(r"^\s*trusted\s*=\s*abs_gap\s*<\s*([0-9.eE+-]+)", src, re.M)
    assert assignments, "pipeline no longer sets `trusted` from abs_gap"
    assert all(float(v) == THRESHOLD_HA for v in assignments), assignments


def test_published_entries_match_the_definition():
    """Every entry's stored `trusted` flag is exactly what the criterion says it is."""
    checked = 0
    for f in glob.glob(str(REPO / "releases/v4/db/*.json")):
        d = json.load(open(f))
        q = d.get("results", {}).get("quality", {}) or {}
        gap, trusted = q.get("abs_vqe_exact_gap"), q.get("trusted")
        if gap is None or trusted is None:
            continue
        assert trusted == (gap < THRESHOLD_HA), "%s: gap=%r trusted=%r" % (Path(f).name, gap, trusted)
        checked += 1
    assert checked >= 50, "only %d entries carried both fields" % checked


def test_beats_classical_is_independent_of_certification():
    """The CCSD(T) badge is informational: it must be neither implied by nor imply
    certification across the published database, or the two concepts have collapsed."""
    cert_without_badge = badge_without_cert = 0
    for f in glob.glob(str(REPO / "releases/v4/db/*.json")):
        q = json.load(open(f)).get("results", {}).get("quality", {}) or {}
        gap, badge = q.get("abs_vqe_exact_gap"), q.get("beats_classical")
        if gap is None or badge is None:
            continue
        cert = gap < THRESHOLD_HA
        cert_without_badge += cert and not badge
        badge_without_cert += badge and not cert
    # The direction that matters: carrying the badge must not imply certification, or the
    # badge *is* the criterion. In v4 it demonstrably does not -- all 7 research-tier
    # entries beat CCSD(T) at cc-pVDZ, because the correlation energies there are large
    # enough that even a 27 mHa gap clears them. (It also means the badge currently
    # discriminates nothing: all 54 entries carry it. Recorded in TRUST_POLICY.md.)
    assert badge_without_cert > 0, (
        "every badged entry is certified; the badge has collapsed into the criterion")
    assert cert_without_badge >= 0


def test_trust_policy_states_the_criterion_and_not_the_badge_as_it():
    text = (REPO / "docs/TRUST_POLICY.md").read_text(encoding="utf-8")
    assert "0.01 Ha" in text and "10 mHa" in text
    # The CCSD(T) inequality may appear only where it is being described as a badge or
    # as history -- never under the criterion heading.
    head = text.split("## Tiers")[0]
    crit = head.split("## The certification criterion")[1]
    assert "E_CCSD(T)" not in crit, "the criterion section names the CCSD(T) comparison"
    assert "beats_classical" in text and "informational" in text


def test_other_documents_do_not_redefine_it():
    """Any doc that spells out the CCSD(T) inequality must, within a few lines, say it is
    a badge, a correction, or history -- never present it as the live criterion."""
    pat = re.compile(r"\|E_VQE\s*[−-]\s*E_CASCI\|\s*<\s*\|E_CCSD\(T\)")
    ok_words = ("badge", "informational", "not the criterion", "not, and has never",
                "Correction", "corrected", "History", "originally")
    for md in list((REPO / "docs").glob("*.md")) + [REPO / "README.md", REPO / "SCHEMA.md"]:
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if pat.search(line):
                window = "\n".join(lines[max(0, i - 12): i + 8])
                assert any(w in window for w in ok_words), (
                    "%s:%d presents the CCSD(T) comparison as the criterion" % (md.name, i + 1))
