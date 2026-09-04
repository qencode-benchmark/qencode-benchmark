"""Documentation that tells you to run a command that fails is worse than no documentation.

Consolidating the docs on 2026-09-04 found, in files nobody had opened since May:

  * two guides instructing `pip install -r requirements.txt` -- a file that has never
    existed in this repository, so following either one failed at step one
  * a quick start quoting the v3 package pins as if they were v4, and CLI defaults
    (`--multistart 5`, `--reps 4`) that the parser disagreed with
  * links to `BENCHMARK_SPEC_V4.md` and `TRUSTED_POLICY.md`, neither of which exists
  * three overlapping getting-started guides and two changelogs with different histories

None of that is catchable by reading; all of it is catchable by a test. These checks are
deliberately mechanical -- they compare documentation against the repository and against
the argument parser, and say nothing about whether the prose is any good.

    pytest tests/test_docs_integrity.py -v

Standard library only.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PIPELINE = REPO / "src" / "qencode" / "pipeline" / "generate_entry_v4.py"

# Docs a reader is expected to follow. Generated notes, archived scripts and the
# experiment records are excluded: they describe what was true when they were written.
DOC_GLOBS = ["*.md", "docs/*.md", "notebooks/*.md", "tools/*.md", "website/*.md"]
SKIP = {"docs/V4_PLAN.md"}          # a roadmap: names files that do not exist yet, by design


def docs():
    out = []
    for pattern in DOC_GLOBS:
        for p in sorted(REPO.glob(pattern)):
            rel = p.relative_to(REPO).as_posix()
            if rel not in SKIP:
                out.append(p)
    return out


DOCS = docs()
IDS = [p.relative_to(REPO).as_posix() for p in DOCS]


# ── Nothing may point at a file that does not exist ───────────────────────────

_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_every_relative_link_resolves(doc):
    """Markdown links to files in this repository must point at something real."""
    broken = []
    for target in _LINK.findall(doc.read_text(encoding="utf-8")):
        target = target.split("#")[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (doc.parent / target).resolve().exists():
            broken.append(target)
    assert not broken, "%s links to non-existent path(s): %s" % (
        doc.relative_to(REPO), broken)


def _code_blocks(text):
    """Only fenced blocks. A reader copies those; prose that merely mentions a broken
    command -- as the redirect stubs do, to record what was wrong -- is not an
    instruction and must not be flagged."""
    return "\n".join(re.findall(r"```[a-z]*\n(.*?)```", text, re.S))


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_no_doc_tells_you_to_install_a_requirements_file_that_does_not_exist(doc):
    """The specific failure that shipped: `pip install -r requirements.txt`."""
    for match in re.findall(r"pip install\s+-r\s+(\S+)",
                            _code_blocks(doc.read_text(encoding="utf-8"))):
        target = match.strip("`\"'")
        assert (REPO / target).exists(), (
            "%s says `pip install -r %s`, which does not exist. The pinned files are "
            "requirements-v4.txt and requirements-v3.txt."
            % (doc.relative_to(REPO), target))


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_no_doc_references_a_script_that_does_not_exist(doc):
    """A command a reader would copy must name a script that is present."""
    missing = set()
    for path in re.findall(r"(?:python\s+)((?:scripts|tools)/[A-Za-z0-9_/-]+\.(?:py|sh))",
                           _code_blocks(doc.read_text(encoding="utf-8"))):
        if not (REPO / path).exists():
            missing.add(path)
    assert not missing, "%s references missing script(s): %s" % (
        doc.relative_to(REPO), sorted(missing))


# ── Documented CLI defaults must match the parser ─────────────────────────────

def _parser_defaults():
    """Read `add_argument("--flag", ..., default=X)` out of the pipeline without importing
    it, so the chemistry stack is not needed to check the docs."""
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
    found = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        flags = [a.value for a in node.args
                 if isinstance(a, ast.Constant) and str(a.value).startswith("--")]
        default = None
        for kw in node.keywords:
            if kw.arg == "default":
                try:
                    default = ast.literal_eval(kw.value)
                except (ValueError, SyntaxError):
                    default = None
        for f in flags:
            if default is not None:
                found[f] = default
    return found


# Flags the quick start puts in a table. If a doc quotes a default for one of these, it
# has to be the real one -- `--multistart 5` and `--reps 4` were both wrong for months.
CHECKED_FLAGS = ["--multistart", "--max-iter", "--reps", "--backend", "--orbital-opt"]


def test_the_parser_still_exposes_the_flags_the_docs_document():
    defaults = _parser_defaults()
    missing = [f for f in CHECKED_FLAGS if f not in defaults]
    assert not missing, "docs document flags the parser no longer has: %s" % missing


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_documented_cli_defaults_match_the_parser(doc):
    """A markdown table row `| \\`--flag\\` | \\`value\\` | ... |` must state the real default."""
    defaults = _parser_defaults()
    text = doc.read_text(encoding="utf-8")
    wrong = []
    for flag in CHECKED_FLAGS:
        pattern = r"\|\s*`" + re.escape(flag) + r"`\s*\|\s*`?([^|`]+?)`?\s*\|"
        for stated in re.findall(pattern, text):
            stated = stated.strip()
            actual = str(defaults[flag])
            if stated.lower() in ("required", "—", "-", ""):
                continue
            if stated != actual:
                wrong.append((flag, stated, actual))
    assert not wrong, "%s states wrong default(s) [flag, doc says, actual]: %s" % (
        doc.relative_to(REPO), wrong)


# ── One canonical document per topic ──────────────────────────────────────────

@pytest.mark.parametrize("stub,canonical", [
    ("docs/QUICK_START.md", "QUICKSTART.md"),
    ("docs/GETTING_STARTED.md", "QUICKSTART.md"),
    ("docs/CHANGELOG.md", "CHANGELOG.md"),
    ("VERIFY.md", "docs/VERIFY.md"),
])
def test_superseded_docs_stay_pointers(stub, canonical):
    """These four paths are linked from outside the repository, so they are kept as
    pointers rather than deleted. A pointer that grows back into a second copy of the
    content is the problem returning, so it is capped."""
    p = REPO / stub
    assert p.is_file(), "%s should exist as a pointer" % stub
    text = p.read_text(encoding="utf-8")
    assert Path(canonical).name in text, "%s does not point at %s" % (stub, canonical)
    assert len(text.splitlines()) < 40, (
        "%s has grown to %d lines; it is meant to be a pointer to %s, not a second copy"
        % (stub, len(text.splitlines()), canonical))


def test_the_suite_version_claimed_by_the_docs_is_current():
    """No reader-facing doc should still headline a superseded suite."""
    stale = []
    for doc in DOCS:
        head = "\n".join(doc.read_text(encoding="utf-8").splitlines()[:3])
        if re.search(r"Suite v3(\.\d)?\b", head):
            stale.append(doc.relative_to(REPO).as_posix())
    assert not stale, "docs still headlining Suite v3 in their title: %s" % stale
