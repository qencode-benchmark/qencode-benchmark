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


## Related

- [`docs/TRUST_POLICY.md`](TRUST_POLICY.md) — certified vs research tier
- [`docs/SUBMISSIONS.md`](SUBMISSIONS.md) — submitting an entry
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — the determinism rules the project enforces
