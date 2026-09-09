# ADAPT rebalancing candidates — NOT part of the published suite

Same status as `../candidates/`: staged evidence for [`docs/SUITE_BALANCE.md`](../../../docs/SUITE_BALANCE.md),
not in `releases/v4/db`, not on the leaderboard, not counted anywhere.

## What they are

Twenty ADAPT-VQE entries generated 2026-09-09 on the cluster:

- **Eight paired counterparts.** The eight published ADAPT entries that run COBYLA inside,
  regenerated with L-BFGS-B inside. One variable changed.
- **Twelve new cells.** The six molecules with no ADAPT entry at all (BeH2, H2, H2O, HF,
  LiH, NH3), each with both inner optimisers, so the new cells arrive paired.

Filenames are the run tag (molecule_orbitals_inner), not the entry id, because two entries
of the same molecule differ only by inner optimiser.

## A caveat that is the point

Every one of these stops as soon as it certifies, like every published ADAPT entry. Their
gaps therefore record where the stopping rule fired, not what ADAPT can reach. Three runs
with the rule disabled are in `../nostop_probe.md`.

## Reproducing one

    python scripts/generate_entry_v4.py --molecule LiH --mapping jordan_wigner         --orbital-opt hf --ansatz-type adapt --adapt-inner bfgs --out-dir <somewhere>

Note that before commit 11f36748 that command silently ran COBYLA.
