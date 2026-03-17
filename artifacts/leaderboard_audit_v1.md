# Leaderboard Audit Report

This report validates the leaderboard dataset produced by `scripts/generate_leaderboard.py` (certified entries only).

## Summary

- **Total entries (max across categories):** 11
- **Excluded entries:** N/A (dataset is certified-only at generation time)

## Checks

- ✓ **Accuracy: required columns** — Has ['rank', 'molecule', 'gap', 'depth', '2q_gates']
- ✓ **Accuracy: no NaN in required metrics** — OK
- ✓ **Accuracy: rank order (gap)** — Per-molecule order correct
- ✓ **Accuracy: no duplicate (molecule, rank)** — OK
- ✓ **Cost: required columns** — Has ['rank', 'molecule', 'gap', 'depth', '2q_gates']
- ✓ **Cost: no NaN in required metrics** — OK
- ✓ **Cost: rank order (2q_gates)** — Per-molecule order correct
- ✓ **Cost: no duplicate (molecule, rank)** — OK
- ✓ **Balanced: required columns** — Has ['rank', 'molecule', 'gap', 'depth', 'balanced_score']
- ✓ **Balanced: no NaN in required metrics** — OK
- ✓ **Balanced: rank order (balanced_score)** — Per-molecule order correct
- ✓ **Balanced: no duplicate (molecule, rank)** — OK
- ✓ **Balanced: score = gap × depth** — Consistent within 1e-6

## Result

**Leaderboard dataset valid.**
