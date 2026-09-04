# Leaderboard Rules v2

How entries become rows on [the public leaderboard](https://www.qencode-benchmark.org/leaderboard),
and how those rows are ordered. This document describes what
`scripts/export_leaderboard_v4.py` actually does; the leaderboard metadata reports
`leaderboard_rules: 2`, matching the version in this filename.

Ranking rules are versioned independently of the benchmark suite. Any change to a
ranking formula, an eligibility criterion, or a tie-break must be published as a new
rules version rather than applied silently, because a score that changes meaning
without changing its label is exactly the failure this project exists to avoid.

---

## Eligibility

**Source.** Rows are built from the entry JSON files in `releases/v4/db/`. Nothing is
entered by hand; an entry that is not in the database is not on the leaderboard.

**Deduplication.** At most one row survives per
`(molecule, mapping, ansatz, orbital_optimization)`. If the database holds several
runs of the same configuration, the one with the **lowest gap** is kept. This guards
against duplicate files, not against cherry-picking: every run remains in the
repository and in git history.

**Tiers.** An entry is *certified* when its gap to the active-space CASCI reference is
below the **10 mHartree** threshold (`gap < 0.01 Ha`). Everything else is *research
tier* — recorded, published, and never discarded.

---

## Categories

Rankings are **global across the suite**, not per molecule. Rank 1 is the best entry
overall in that category; the molecule, mapping and ansatz filters narrow the view
without changing the ranks. Entries with equal keys share a rank.

### Best Accuracy — certified entries

Ordered by `gap` ascending. Lower is better.

### Lowest Hardware Cost — certified entries with circuit metrics

Ordered by two-qubit gate count ascending, then circuit depth ascending.

Entries whose circuit metrics are symbolic rather than transpiled are excluded. UCCSD
builds exponentials of Pauli sums whose 1q/2q decomposition depends on the target
device, so a reported depth of ≤ 1 or a 2-qubit count of ≤ 1 is a placeholder, not a
measurement. Ranking on a placeholder would put those entries at the top of a cost
board they have not earned.

### Balanced — same eligibility as Lowest Cost

An equal-weight blend of the two rankings above, in *rank space* rather than in the
raw units, since a gap in Hartrees and a gate count are not commensurable:

```
N  = number of eligible entries
gr = (position in gap-sorted order)  / (N - 1)      # 0.0 = best
cr = (position in cost-sorted order) / (N - 1)      # 0.0 = best

balanced_score = round(0.5 * gr + 0.5 * cr, 6)      # lower is better
```

Ordered by `balanced_score` ascending.

### Research — everything not certified

Ordered by `gap` ascending. A research row is a real result that did not reach the
threshold, usually because the method met its limit on a strongly correlated system.
It is not a failed or discarded run.

---

## Reported alongside every row

- **CCSD(T) correlation energy**, so a VQE gap can be read against the best classical
  single-reference perturbative result for the same molecule. The *Beats CCSD(T)*
  badge means the VQE error is smaller than that correlation energy — it does not
  mean quantum beat classical computing.
- **Estimated T-gate count and non-Clifford gate count**, the resource-relevant cost
  of a fault-tolerant implementation. These are estimates from the pre-transpilation
  circuit, not compiled counts for a specific device, and they are suppressed for the
  symbolic circuits described above.

---

## Regenerating the leaderboard

```bash
python scripts/export_leaderboard_v4.py            # entry JSONs -> CSVs
python scripts/publish_leaderboard.py --secret ... # CSVs -> live site
```

The export writes `leaderboard_accuracy.csv`, `leaderboard_hardware_cost.csv`,
`leaderboard_balanced.csv`, `leaderboard_research.csv` and `leaderboard_metadata.json`
to `website/public/data/`. `--dry-run` prints what would be written without touching
anything.

`scripts/generate_leaderboard.py` is the earlier v2 CSV path, kept for the frozen v2
and v3 suites. It is not what produces the current leaderboard.

---

## Changes from v1

Rules v1 was drafted for the original suite and is superseded. The differences are
recorded here rather than left for a reader to discover by comparing a published
score against a formula that no longer produces it.

| | v1 | v2 |
|---|---|---|
| Balanced score | `gap x depth` | `0.5*gap_rank + 0.5*cost_rank`, normalised over the field |
| Categories | 3 | 4 — research tier added |
| Ranking scope | per molecule | global across the suite; filters narrow the view |
| Cost eligibility | not specified | symbolic (pre-transpilation) circuits excluded |
| Reported per row | gap, depth, 2q | adds CCSD(T) correlation and T-gate estimate |

Multiplying a gap in Hartrees by a gate count is not a meaningful quantity: the units
do not combine, and the product is dominated by whichever factor happens to be
numerically larger. v2 blends the two *rankings* instead, which is scale-free.


## Amendments to v2

Amendments are dated and listed here rather than issued as a new version, because none of
them changes the status of an existing entry or moves a published ranking. An amendment
that did either would be a version bump.

### 2026-08-27 — simulator backend eligibility

**`default.qubit` is the reference backend.** Every entry in the database was produced on
it (54 of 54), and it remains the source of truth.

**An entry whose optimiser contains any gradient-free component must be produced on
`default.qubit` to be certified.** That covers plain COBYLA and ADAPT-VQE with a COBYLA
inner optimiser — 47 of the 54 current entries.

**`lightning.qubit` is permitted only for fully gradient-based entries** (L-BFGS-B,
ADAPT-VQE with a gradient-based inner optimiser — 7 of 54 today). Such an entry must
record its backend in `run_config.backend_type`, which the pipeline already does, and must
be displayed with that backend labelled.

**Why the restriction.** The two backends agree on the arithmetic and disagree on the
answer. Measured over H₂O, LiH, N₂ and benzene:

| | worst disagreement |
|---|---|
| a single energy evaluation at a fixed point | 2.56 × 10⁻¹³ Ha |
| after COBYLA (gradient-free) | 2.40 × 10⁻³ Ha — **2.40 mHa** |
| after L-BFGS-B (parameter-shift) | 1.55 × 10⁻⁶ Ha |

A gradient-free optimiser chooses its next step by comparing two nearly equal energies, so
a difference in the thirteenth decimal can flip a comparison and send the run into a
different local minimum. In one run benzene differed by **11.03 mHa** between backends —
larger than the 10 mHa certification threshold, meaning two backends can place the same
configuration on opposite sides of the certified line. The magnitude is not stable, because
it is a question of which basin the run reaches.

This is the same amplification that makes threaded BLAS unsafe, which is why the
single-thread rule exists. A gradient-based optimiser is effectively immune: a 10⁻¹³
perturbation moves a computed search direction by 10⁻¹³ rather than flipping a decision.

`lightning.qubit` is roughly 1.8× faster. That speedup is real, and it is not worth a
certification that depends on which simulator happened to run. Evidence and method:
[`DEFERRED_TRACKS_FEASIBILITY.md`](DEFERRED_TRACKS_FEASIBILITY.md),
`tools/probe_backend.py`, `tools/probe_backend_mechanism.py`.

### 2026-09-03 — what reproducibility means for a gradient-free optimiser

**Gradient-free optimisers are certified on outcome, not on bit-identical energies across
machines. Bit-identical regeneration is guaranteed only on the reference pinned
environment.**

This states what the numerics support rather than what the word "reproducible" is usually
taken to imply. A gradient-free optimiser chooses its next step by comparing two nearly
equal energies, so a last-bit arithmetic difference can flip a comparison and send the run
into a different local minimum. Two simulator backends that agree to 10⁻¹³ Ha on a single
evaluation have landed 11 mHa apart after COBYLA. A different machine is a larger
perturbation than that.

Reproducing a published entry therefore means three things, in decreasing strength:

1. **The procedure is identical and fully declared** — same ansatz, optimiser, iteration
   budget, seed, active space, mapping and classical preprocessing. Every one of those is
   recorded in the entry.
2. **The outcome still satisfies the certification criterion** — the regenerated gap is
   below the 10 mHa threshold. This is what should hold on any machine, and it is what
   `scripts/verify_entry.py --mode certification` checks.
3. **The energy matches bit-for-bit** — only claimed on the reference pinned environment,
   and checked there by `tools/verify_sweep.sh`. `--mode strict` is that check.

Anything stronger than (2) across machines is aspirational and is currently false for
COBYLA-style methods.

**Measured.** Re-running all 40 entries on an environment with drifted package versions moved
the published energy by a median of 6.7 × 10⁻⁸ Ha, a 90th percentile of 2.1 × 10⁻³ Ha and
a maximum of 1.4 × 10⁻² Ha. **17 of 40 exceeded the 10⁻⁶ Ha strict tolerance**, while
still certifying — which is exactly the gap between (2) and (3) above.

**A known limit of (2).** Two entries do not re-certify on that environment:
`C4H4_ccpvdz_PAR_HEA` and `C4H4_ccpvdz_JW_HEA`, published at gaps of 6.1 and 9.6 mHa,
regenerate at 20.5 and 19.0 mHa. Both were certified close to the threshold, and an entry
certified close to the threshold is not robustly certified: a different environment moves
it across. That is a property of those entries, not of the verifier, and it is recorded
here rather than worked around.

### 2026-09-03 — certification margin

**An entry certified close to the threshold is not robustly certified**, and the
leaderboard has been showing it identically to one certified with room to spare. Both are
"certified"; only one survives being re-run somewhere else.

    margin = certification_threshold - gap

`tools/certification_margin.py` reports the margin for every certified entry and flags two
kinds of fragility, because neither subsumes the other:

- **thin margin** — margin below 20% of the threshold. A heuristic, computable for every
  entry without re-running anything. **10 of the 47 certified entries** qualify, the
  tightest being H₁₀ at a margin of **0.2%** (gap 9.977 mHa against a 10 mHa threshold).
- **measured fragile** — the entry has been *observed* to fail re-certification on another
  environment. Authoritative, but only exists for entries that have been re-run.

Two entries are currently measured fragile:

| entry | published gap | regenerated gap |
|---|---|---|
| `C4H4_ccpvdz_PAR_HEA` | 6.1 mHa | 20.5 mHa |
| `C4H4_ccpvdz_JW_HEA` | 9.6 mHa | 19.0 mHa |

They remain certified: they reproduce exactly on the reference pinned environment, which
is what certification attests. They are flagged, not withdrawn. The weekly cross-machine CI
job reports them as known and does not fail on them; any *other* entry that stops
certifying is a real regression.

**The heuristic does not subsume the measurement.** `C4H4_ccpvdz_PAR_HEA` has a margin of
**38.9%** of the threshold — comfortably outside any sensible thin-margin cut — and fails
anyway, because its energy moved 14 mHa. Margin bounds how far an entry *can* move before
it stops certifying; it says nothing about how far it *will*. Both flags are needed.

A related trap, recorded because it caught us: `gap + |ΔE|` does **not** predict
re-certification. Two entries that looked like failures by that arithmetic passed when
actually tested, because their energy moved *toward* the reference and the gap shrank.
Fragility is established by running `verify_entry.py --mode certification`, never by
inference.

### 2026-09-04 — what actually amplifies: the ansatz, not the optimiser alone

The amendment above attributes environment fragility to the optimiser family. **That is
measurably incomplete, and the correction is recorded here rather than edited into the
earlier text.**

`H4_ccpvdz_JW_ADAPT` is gradient-free by that rule (ADAPT-VQE with a COBYLA inner
optimiser), holds the **second-thinnest margin in the suite at 0.58%**, and was therefore
the entry the rule predicted would fail next. Re-run on the drifted environment its energy
moved **3.4 × 10⁻⁸ Ha** — 1692× *less* than its own margin, and the smallest movement
measured anywhere in the suite.

H₄ is the controlled comparison, because it is the only molecule carrying both an ADAPT and
an HEA entry. Same molecule, basis, mapping, seed and environment; only the ansatz differs:

| H₄ entry | optimiser | energy moved | against its own margin |
|---|---|---|---|
| ADAPT | COBYLA **inner** | 3.4 × 10⁻⁸ Ha | 0.001× |
| HEA | plain COBYLA | 8.8 × 10⁻⁴ Ha | **1.22×** |

**25,595× apart.** ADAPT selects its operators by analytic gradient, so the ansatz
*structure* is gradient-determined and the gradient-free optimiser only polishes a small,
incrementally grown, well-conditioned parameter set. An unstructured ansatz hands the same
optimiser a full parameter vector over a landscape of near-degenerate minima — which is
where a flipped comparison selects a different basin.

All five cross-environment measurements, ranked by movement against the entry's own margin:

| entry | ansatz / optimiser | margin | moved | moved/margin |
|---|---|---|---|---|
| H₄ | ADAPT / COBYLA inner | 5.8 × 10⁻⁵ | 3.4 × 10⁻⁸ | 0.001× |
| H₁₀ | ADAPT / L-BFGS-B inner | 2.3 × 10⁻⁵ | 1.0 × 10⁻⁶ | 0.04× |
| H₄ | HEA / COBYLA | 7.2 × 10⁻⁴ | 8.8 × 10⁻⁴ | 1.22× |
| C₄H₄ | HEA / COBYLA | 3.9 × 10⁻³ | 1.4 × 10⁻² | 3.71× |

Clean separation, no overlap: **ADAPT ≤ 1.0 × 10⁻⁶ Ha, HEA ≥ 8.8 × 10⁻⁴ Ha.** The risk
flag in `tools/certification_margin.py` is now the conjunction *gradient-free **and**
unstructured ansatz*. It previously named 6 at-risk entries, 4 of which were ADAPT runs
this measurement indicates are not the concern.

**A pass is not automatically robustness.** `H4_ccpvdz_JW_HEA` moved **1.22× its own
margin** and certified anyway, because the energy moved *toward* the reference and its gap
shrank from 9.283 to 8.405 mHa. The opposite sign would have failed it. It is recorded as
**measured-marginal**, not measured-robust — a distinct flag, because a pass that depended
on the direction of the movement is not evidence of stability. This is the mirror of the
`gap + |ΔE|` trap noted above: movement can be favourable, so that arithmetic
over-predicts failure *and* a pass under-reports risk.

Nothing here changes the status of any entry, the CI allow-list, or a published ranking.
Evidence: `experiments/verification_sweep/cross_environment/H4_cross_env_check.txt`.

**Caveat.** n = 5 measured entries, resting on two ADAPT measurements. Stated as what has
been measured, not as a proven law.

### 2026-08-27 — suite stability during publication

The molecule catalogue, basis set and active spaces are **frozen** until the paper
currently pending on the v4.4 numbers is published. A basis-set change re-runs and
re-hashes every entry, which would move every figure that paper cites.

This is a timing decision, not a rejection. A cc-pVTZ track has been measured and is
cheaper than assumed — identical qubit counts, identical Pauli term counts, λ within 2%,
so circuits and gate counts are unchanged and only the energies move. It is a *when*.


## Related

- [`docs/TRUST_POLICY.md`](TRUST_POLICY.md) — certified vs research tier
- [`docs/SUBMISSIONS.md`](SUBMISSIONS.md) — submitting an entry
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — the determinism rules the project enforces
