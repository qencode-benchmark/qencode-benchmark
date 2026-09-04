"""Score a VQE energy you computed yourself against the QEncode reference.

    import qencode
    s = qencode.score(-7.9835, molecule="LiH", optimizer="COBYLA", ansatz="hea")
    print(s.report())

What this answers: how far your energy is from the *exact* ground state of the same
active-space Hamiltonian, where that lands against the two published thresholds, how much
room the result has before it stops meeting the certification threshold, whether your
optimiser and ansatz make that room fragile, and where the number would sit among the
published entries for the same molecule.

Why it is worth having: the comparison needs the exact ground state of your active space,
and computing it means installing PySCF and waiting. This ships the references for all 16
suite molecules inside the package, so scoring needs no chemistry stack and no network --
`import qencode` and one call. The references are extracted from the published database by
tools/build_reference_table.py and a test keeps the two in sync.

Three things this is careful about, because each one is a way to be quietly wrong:

  The comparison is only meaningful for the SAME problem. Same molecule, geometry, basis,
  charge, spin and active space. A gap against a different active space is not a worse
  number, it is a meaningless one, so a declared active space that disagrees raises rather
  than scores.

  Meeting the threshold is not certification. Certification is what the pipeline produces:
  a full run, recorded provenance, a content hash and a signature. A self-reported energy
  that clears 10 mHa would qualify if it were generated and verified that way. Nothing
  here has a field called "certified".

  An energy BELOW the exact ground state is not a good result. The variational principle
  forbids it, so it means the state, the Hamiltonian or the active space is not what you
  think it is. That is reported first, before any gap.
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from qencode._paths import data_file

__all__ = [
    "CERT_THRESHOLD_HA", "CHEMICAL_ACCURACY_HA",
    "Score", "score", "reference", "available", "references_table",
]

CERT_THRESHOLD_HA = 0.01        # QEncode certification threshold, docs/TRUST_POLICY.md
CHEMICAL_ACCURACY_HA = 1.6e-3   # 1 kcal/mol; reported, never a criterion

# Below this fraction of the threshold the margin is thin. Same cut, and the same reason,
# as tools/certification_margin.py: chosen from the measured distribution.
THIN_MARGIN_FRACTION = 0.20

# An energy this far below the exact ground state is a variational violation rather than
# floating-point noise. The published database's own reference values agree to ~2e-9 Ha
# between their two independent computations, so the floor is set an order above that.
VARIATIONAL_TOLERANCE_HA = 1e-8

_TABLE: Optional[Dict[str, Any]] = None


def references_table() -> Dict[str, Any]:
    """The packaged reference table, loaded once."""
    global _TABLE
    if _TABLE is None:
        path = data_file("references_v4.json")
        if path is None:
            raise FileNotFoundError(
                "references_v4.json is missing from the package. Reinstall qencode, or "
                "from a checkout run: python tools/build_reference_table.py")
        _TABLE = _json.loads(path.read_text(encoding="utf-8"))
    return _TABLE


def available() -> List[Tuple[str, str, str]]:
    """Every scorable configuration as (molecule, basis, orbital_optimization)."""
    return [(r["molecule"], r["basis"], r["orbital_optimization"])
            for r in references_table()["references"]]


def reference(molecule: str, basis: str = "cc-pvdz",
              orbital_optimization: Optional[str] = None) -> Dict[str, Any]:
    """The published reference for one problem.

    orbital_optimization may be omitted when the suite holds only one treatment for the
    molecule, which is the case for all 16 today. It is never guessed when ambiguous.
    """
    rows = [r for r in references_table()["references"]
            if r["molecule"].lower() == str(molecule).lower()
            and r["basis"].lower() == str(basis).lower()]
    if not rows:
        names = sorted({r["molecule"] for r in references_table()["references"]})
        raise KeyError(
            "no QEncode reference for molecule %r at basis %r. Scorable molecules: %s. "
            "For anything else, generate the reference yourself with "
            "`qencode run --molecule ... ` (needs the chemistry stack)."
            % (molecule, basis, ", ".join(names)))
    if orbital_optimization is not None:
        rows = [r for r in rows
                if r["orbital_optimization"].lower() == str(orbital_optimization).lower()]
        if not rows:
            raise KeyError("no reference for %s with orbital_optimization=%r"
                           % (molecule, orbital_optimization))
    if len(rows) > 1:
        raise KeyError(
            "%s has several orbital treatments (%s); pass orbital_optimization= to say "
            "which one you ran. They are different problems with different references."
            % (molecule, ", ".join(sorted(r["orbital_optimization"] for r in rows))))
    return rows[0]


def _optimiser_family(optimizer: Optional[str]) -> Optional[str]:
    if not optimizer:
        return None
    return "gradient-free" if "cobyla" in str(optimizer).lower() else "gradient-based"


def _amplifies(optimizer: Optional[str], ansatz: Optional[str]) -> Optional[bool]:
    """Does this (optimiser, ansatz) pair turn a last-bit arithmetic difference into a
    different local minimum?

    Measured, and this is the same rule as tools/certification_margin.py -- a test asserts
    the two agree. It is the CONJUNCTION: a gradient-free optimiser on an unstructured
    ansatz. ADAPT-VQE selects its operators by analytic gradient, so its structure is
    gradient-determined even with a COBYLA inner optimiser. On H4, holding molecule,
    basis, mapping and environment fixed and changing only the ansatz, ADAPT/COBYLA moved
    3.4e-08 Ha across environments and HEA/COBYLA moved 8.8e-04 Ha -- 25,595x more.

    Returns None when the optimiser is unknown, because a guess would be worse than
    saying nothing.
    """
    if not optimizer:
        return None
    fam = _optimiser_family(optimizer)
    structured = "adapt" in str(ansatz or "").lower()
    return fam == "gradient-free" and not structured


@dataclass
class Score:
    """The result of scoring one energy. Print `report()` rather than reading fields."""

    molecule: str
    basis: str
    orbital_optimization: str
    energy_hartree: float
    reference_energy_hartree: float

    gap_ha: float
    gap_mha: float

    below_reference: bool
    variational_violation_ha: Optional[float]

    meets_certification_threshold: bool
    reaches_chemical_accuracy: bool
    margin_ha: Optional[float]
    margin_fraction: Optional[float]
    thin_margin: Optional[bool]

    optimizer: Optional[str] = None
    ansatz: Optional[str] = None
    optimiser_family: Optional[str] = None
    amplifies: Optional[bool] = None

    rank_among_published: Optional[int] = None
    n_published: int = 0
    best_published_gap_ha: Optional[float] = None

    beats_ccsd_t_correlation: Optional[bool] = None
    caveats: List[str] = field(default_factory=list)

    def _threshold_line(self) -> str:
        if self.reaches_chemical_accuracy:
            return ("reaches CHEMICAL ACCURACY (< %.1f mHa) and would meet the %.0f mHa "
                    "certification threshold" % (CHEMICAL_ACCURACY_HA * 1e3,
                                                 CERT_THRESHOLD_HA * 1e3))
        if self.meets_certification_threshold:
            return ("would meet the %.0f mHa certification threshold, but not chemical "
                    "accuracy (%.1f mHa)" % (CERT_THRESHOLD_HA * 1e3,
                                             CHEMICAL_ACCURACY_HA * 1e3))
        return ("does NOT meet the %.0f mHa certification threshold -- research tier, "
                "which is a recorded result, not a failed one"
                % (CERT_THRESHOLD_HA * 1e3))

    def report(self) -> str:
        L: List[str] = []
        add = L.append
        add("QEncode score -- %s / %s / %s orbitals"
            % (self.molecule, self.basis, self.orbital_optimization))
        add("=" * 72)

        if self.below_reference:
            add("")
            add("  STOP: your energy is BELOW the exact ground state by %.3e Ha."
                % (self.variational_violation_ha or 0.0))
            add("  The variational principle forbids this, so the gap below is not a")
            add("  measure of accuracy. Something differs from the reference problem:")
            add("  a different geometry, active space, charge/spin, or a Hamiltonian")
            add("  missing its nuclear repulsion or core energy. Check those first.")
            add("")

        add("  your energy        %18.10f Ha" % self.energy_hartree)
        add("  exact ground state %18.10f Ha   (CASCI in the declared active space)"
            % self.reference_energy_hartree)
        add("  gap                %18.10f Ha   = %.3f mHa" % (self.gap_ha, self.gap_mha))
        add("")
        add("  %s" % self._threshold_line())

        if self.margin_ha is not None:
            add("  margin             %.3e Ha (%.1f%% of the threshold)%s"
                % (self.margin_ha, 100 * (self.margin_fraction or 0.0),
                   "  -- THIN" if self.thin_margin else ""))

        if self.amplifies is not None:
            add("")
            add("  optimiser          %s (%s)" % (self.optimizer, self.optimiser_family))
            if self.amplifies:
                add("  amplifying         YES -- gradient-free optimiser on an unstructured")
                add("                     ansatz. Re-run elsewhere, energies in this class")
                add("                     have moved by up to 1e-2 Ha. If the margin above")
                add("                     is thin, treat it as provisional.")
            else:
                add("  amplifying         no -- this combination has been measured to move")
                add("                     <= 1e-6 Ha across environments.")

        if self.n_published:
            add("")
            if self.rank_among_published is not None:
                add("  among published    #%d of %d QEncode entries for this problem"
                    % (self.rank_among_published, self.n_published + 1))
            add("  best published gap %.3f mHa" % (self.best_published_gap_ha * 1e3))

        if self.caveats:
            add("")
            add("  Read before quoting this:")
            for c in self.caveats:
                add("    - %s" % c)
        return "\n".join(L)

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.report()


def score(energy_hartree: float,
          molecule: str,
          *,
          basis: str = "cc-pvdz",
          orbital_optimization: Optional[str] = None,
          active_space: Optional[Sequence[int]] = None,
          optimizer: Optional[str] = None,
          ansatz: Optional[str] = None) -> Score:
    """Score one VQE energy against the published QEncode reference.

    energy_hartree       your best variational energy, in Hartree
    molecule             one of the 16 suite molecules; `available()` lists them
    basis                must match the suite's basis for the comparison to mean anything
    orbital_optimization "hf" or "casscf"; optional while each molecule has only one
    active_space         (n_electrons, n_orbitals). Checked, not assumed: a mismatch
                         raises, because the gap would be against a different problem
    optimizer, ansatz    optional; enable the amplification assessment

    Raises KeyError for an unknown problem and ValueError for a declared active space
    that does not match the reference.
    """
    ref = reference(molecule, basis=basis, orbital_optimization=orbital_optimization)

    if active_space is not None:
        want = (int(ref["active_electrons"]), int(ref["active_orbitals"]))
        got = tuple(int(x) for x in active_space)
        if got != want:
            raise ValueError(
                "active space mismatch: you declared [%de, %do] and the QEncode "
                "reference for %s is [%de, %do]. These are different problems and the "
                "gap between them would not mean anything, so nothing is scored. "
                "Re-run in the suite's active space, or generate your own reference "
                "with the pipeline." % (got[0], got[1], ref["molecule"], want[0], want[1]))

    e_ref = float(ref["exact_qubit_ground_energy_hartree"])
    e = float(energy_hartree)
    delta = e - e_ref
    gap = abs(delta)

    below = delta < -VARIATIONAL_TOLERANCE_HA
    meets = gap < CERT_THRESHOLD_HA
    chem = gap < CHEMICAL_ACCURACY_HA
    margin = (CERT_THRESHOLD_HA - gap) if meets else None
    margin_frac = (margin / CERT_THRESHOLD_HA) if margin is not None else None
    thin = (margin_frac < THIN_MARGIN_FRACTION) if margin_frac is not None else None

    published = sorted(
        (x["gap_ha"] for x in references_table()["entries"]
         if x["molecule"] == ref["molecule"]
         and x["orbital_optimization"] == ref["orbital_optimization"]))
    rank = (sum(1 for g in published if g < gap) + 1) if published else None
    best = published[0] if published else None

    corr = ref.get("ccsd_t_correlation")
    beats = (gap < abs(float(corr))) if corr is not None else None

    caveats = [
        "The gap is measured against the exact ground state of the SAME active-space "
        "Hamiltonian, not against experiment and not against a complete-basis limit. It "
        "isolates the algorithm's error and says nothing about chemical realism.",
        "This scores a number you reported. It is not a QEncode certification: that "
        "requires the pipeline to generate the entry, with recorded provenance, a "
        "content hash and a signature.",
        "Your geometry, charge and spin must match the reference. QEncode used: %s "
        "(charge %s, spin %s), active space [%de, %do], %s orbitals."
        % (ref.get("geometry"), ref.get("charge"), ref.get("spin"),
           ref["active_electrons"], ref["active_orbitals"], ref["orbital_optimization"]),
    ]
    if beats:
        caveats.append(
            "\"Beats CCSD(T)\" is weaker than it sounds and is not a quality mark: it "
            "holds for all 54 published entries, including the 7 that are not certified.")
    if optimizer is None:
        caveats.append(
            "No optimiser given, so no amplification assessment. Pass optimizer= and "
            "ansatz= to find out whether your margin is fragile across machines.")
    if below:
        caveats.insert(0, "Energy below the variational minimum -- see the warning above. "
                          "The gap is reported for completeness only.")

    return Score(
        molecule=ref["molecule"], basis=ref["basis"],
        orbital_optimization=ref["orbital_optimization"],
        energy_hartree=e, reference_energy_hartree=e_ref,
        gap_ha=gap, gap_mha=gap * 1e3,
        below_reference=below,
        variational_violation_ha=(abs(delta) if below else None),
        meets_certification_threshold=meets, reaches_chemical_accuracy=chem,
        margin_ha=margin, margin_fraction=margin_frac, thin_margin=thin,
        optimizer=optimizer, ansatz=ansatz,
        optimiser_family=_optimiser_family(optimizer),
        amplifies=_amplifies(optimizer, ansatz),
        rank_among_published=rank, n_published=len(published),
        best_published_gap_ha=best,
        beats_ccsd_t_correlation=beats,
        caveats=caveats,
    )
