# Rebalancing candidates — NOT part of the published suite

These entries are **not** in `releases/v4/db`, are **not** on the leaderboard, and are
**not** counted anywhere. They are staged evidence for the argument in
[`docs/SUITE_BALANCE.md`](../../docs/SUITE_BALANCE.md).

## What they are

A gradient-based counterpart to every UCCSD entry in the suite: same molecule, same
mapping, same active space, same orbitals, same tapering, L-BFGS-B in place of COBYLA.
The published suite has 15 UCCSD entries and every one uses COBYLA, so the ansatz-by-
optimiser table had an empty cell and no controlled comparison was possible.

Generated 2026-09-09 on the cluster node, one thread each, through the ordinary
`scripts/generate_entry_v4.py` with the same reproducibility guard as any other entry.
Each file is a complete v4 entry and carries its own provenance, including the machine
fingerprint.

## Why they are staged rather than merged

Suite v4.4 is frozen until the paper is published. Adding entries changes the
per-molecule best in the paper's Table 2, the certified count, and the leaderboard
composition. Merging is a decision for the authors, not a side effect of running the
experiment.

## Reproducing one

    python scripts/generate_entry_v4.py --molecule BeH2 --mapping jordan_wigner \
        --orbital-opt hf --ansatz-type uccsd --optimizer bfgs --out-dir <somewhere>

The runner that produced the set is `~/qencode_runs/rebalance_run.sh` on the cluster.
