"""Scoring somebody else's energy has to be right, and honest about when it is not.

The whole value of `qencode.score` is that a user does not have to run CASCI to find out
how good their VQE result is. That only works if the packaged reference table is exactly
what the published database says, so the strongest test here re-scores all 54 published
entries from their own stored energies and requires the gap to come back to the last bit.

The rest pin the refusals, which matter more than the arithmetic: a mismatched active
space must raise rather than return a meaningless number, an energy below the variational
minimum must be called out before any gap is discussed, and nothing may be labelled
"certified" on the strength of a self-reported number.

    pytest tests/test_scoring.py -v

No chemistry stack needed, which is the point -- and one test enforces that.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "releases" / "v4" / "db"
TABLE = REPO / "src" / "qencode" / "data" / "references_v4.json"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import qencode  # noqa: E402
from qencode import scoring  # noqa: E402


# ── The table is the database ─────────────────────────────────────────────────

def test_packaged_table_matches_the_published_database():
    """Regenerate from releases/v4/db and require the committed file to be identical."""
    import build_reference_table as brt

    assert TABLE.read_text(encoding="utf-8") == brt.serialise(brt.build(DB)), (
        "src/qencode/data/references_v4.json is stale; "
        "run python tools/build_reference_table.py")


def test_table_covers_every_published_problem():
    table = scoring.references_table()
    assert len(table["references"]) == 16
    assert table["n_source_entries"] == len(list(DB.glob("*.json"))) == 54
    assert len(qencode.available()) == 16


@pytest.mark.parametrize("entry_path", sorted(DB.glob("*.json")), ids=lambda p: p.stem[:40])
def test_scoring_a_published_energy_reproduces_its_published_gap(entry_path):
    """The end-to-end check on the table: feed back each entry's own energy and the gap
    must equal the gap that entry was published with."""
    d = json.loads(entry_path.read_text(encoding="utf-8"))
    s = qencode.score(
        d["results"]["vqe"]["best_energy_hartree"],
        molecule=d["problem"]["name"],
        basis=d["problem"]["basis"],
        orbital_optimization=d["problem"].get("orbital_optimization"),
        active_space=(d["problem"]["active_space"]["num_electrons"],
                      d["problem"]["active_space"]["num_spatial_orbitals"]),
    )
    stored_gap = d["results"]["quality"]["abs_vqe_exact_gap"]
    assert abs(s.gap_ha - stored_gap) < 1e-12
    assert s.meets_certification_threshold == d["results"]["quality"]["trusted"]


# ── Refusals ──────────────────────────────────────────────────────────────────

def test_a_mismatched_active_space_raises_rather_than_scoring():
    with pytest.raises(ValueError, match="active space mismatch"):
        qencode.score(-7.98, molecule="LiH", active_space=(6, 6))


def test_an_unknown_molecule_raises_and_says_what_is_available():
    with pytest.raises(KeyError) as exc:
        qencode.score(-1.0, molecule="C60")
    msg = str(exc.value)
    assert "LiH" in msg and "benzene" in msg


def test_an_unknown_basis_raises():
    with pytest.raises(KeyError, match="no QEncode reference"):
        qencode.score(-7.98, molecule="LiH", basis="sto-3g")


def test_energy_below_the_variational_minimum_is_flagged_first():
    s = qencode.score(-8.20, molecule="LiH")
    assert s.below_reference is True
    assert s.variational_violation_ha > 0.2
    report = s.report()
    assert "STOP" in report
    # The warning has to come before the gap, or it will be read past.
    assert report.index("STOP") < report.index("gap")
    assert "variational" in s.caveats[0].lower()


def test_floating_point_noise_below_the_reference_is_not_a_violation():
    ref = qencode.reference("LiH")["exact_qubit_ground_energy_hartree"]
    assert qencode.score(ref - 1e-12, molecule="LiH").below_reference is False


# ── Thresholds, margin, and what must not be claimed ──────────────────────────

def test_the_two_thresholds_and_the_margin():
    ref = qencode.reference("LiH")["exact_qubit_ground_energy_hartree"]

    chem = qencode.score(ref + 1.0e-3, molecule="LiH")
    assert chem.reaches_chemical_accuracy and chem.meets_certification_threshold
    assert abs(chem.margin_ha - (0.01 - 1.0e-3)) < 1e-12
    assert chem.thin_margin is False

    mid = qencode.score(ref + 5.0e-3, molecule="LiH")
    assert not mid.reaches_chemical_accuracy and mid.meets_certification_threshold

    thin = qencode.score(ref + 9.9e-3, molecule="LiH")
    assert thin.thin_margin is True

    out = qencode.score(ref + 2.0e-2, molecule="LiH")
    assert not out.meets_certification_threshold
    assert out.margin_ha is None and out.thin_margin is None


def test_nothing_is_ever_reported_as_certified():
    """A self-reported energy cannot be certified, and the verdict must not imply it.

    Only the verdict body is inspected. The caveats below it deliberately discuss
    certification -- to say this is not it, and that 7 published entries are not
    certified either -- which is the opposite of a claim.
    """
    ref = qencode.reference("LiH")["exact_qubit_ground_energy_hartree"]
    s = qencode.score(ref + 1e-9, molecule="LiH")
    assert not hasattr(s, "certified")
    assert not any(f.startswith("certified") for f in vars(s))

    report = s.report()
    verdict = report.split("Read before quoting this:")[0]
    assert "would meet" in verdict
    for line in verdict.splitlines():
        low = line.lower()
        if "certif" in low:
            assert "would meet" in low or "threshold" in low, (
                "unqualified certification claim in the verdict: %r" % line)

    # And the caveat that says so explicitly must always be present.
    assert any("not a QEncode certification" in c for c in s.caveats)


def test_rank_is_against_the_published_entries_for_the_same_problem():
    gaps = sorted(e["gap_ha"] for e in scoring.references_table()["entries"]
                  if e["molecule"] == "LiH")
    ref = qencode.reference("LiH")["exact_qubit_ground_energy_hartree"]
    best = qencode.score(ref, molecule="LiH")
    assert best.rank_among_published == 1
    assert best.n_published == len(gaps) == 3
    worst = qencode.score(ref + 1.0, molecule="LiH")
    assert worst.rank_among_published == len(gaps) + 1


# ── The amplification rule must not drift from the tool that defines it ───────

def test_amplification_rule_agrees_with_certification_margin_tool():
    """qencode.scoring carries its own copy so the wheel needs no tools/ directory.
    Two copies of a rule is one too many unless something checks they agree."""
    import certification_margin as cm

    cases = [
        ("COBYLA", "hea"), ("COBYLA", "uccsd_tapered"), ("COBYLA", "adapt"),
        ("L-BFGS-B", "hea"), ("L-BFGS-B", "adapt"),
        ("ADAPT-VQE (COBYLA inner)", "adapt"),
        ("ADAPT-VQE (L-BFGS-B inner, statevector engine)", "adapt"),
    ]
    for opt, ansatz in cases:
        assert scoring._amplifies(opt, ansatz) == cm._amplifies(opt, ansatz), (opt, ansatz)
        assert scoring._optimiser_family(opt) == cm._optimiser_family(opt), opt


def test_amplification_is_the_conjunction_not_the_optimiser_alone():
    assert scoring._amplifies("COBYLA", "hea") is True
    assert scoring._amplifies("COBYLA", "adapt") is False       # H4: 3.4e-08 Ha
    assert scoring._amplifies("L-BFGS-B", "hea") is False
    assert scoring._amplifies(None, "hea") is None              # unknown, not guessed


def test_no_optimiser_means_no_assessment_and_the_report_says_so():
    s = qencode.score(-7.9835, molecule="LiH")
    assert s.amplifies is None
    assert any("No optimiser given" in c for c in s.caveats)
    assert "amplifying" not in s.report()


# ── The dependency promise ────────────────────────────────────────────────────

def test_scoring_pulls_in_no_chemistry_stack():
    """`pip install qencode-benchmark` then score a result: the point is that this path
    never touches pyscf or pennylane, which is what makes it fast enough to be used."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys, qencode; "
         "s = qencode.score(-7.9835, molecule='LiH', optimizer='COBYLA', ansatz='hea'); "
         "assert s.gap_mha > 0; "
         "print(any(m in sys.modules for m in ('pyscf','pennylane','openfermion','numpy')))"],
        capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO / "src")})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"
