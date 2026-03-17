# Balanced Score Evaluation

This report compares alternative balanced-score formulas on the certified leaderboard dataset.

## Formulas

| Formula | Expression | Description |
|---------|------------|-------------|
| **A** | `gap × depth` | Current implementation (Leaderboard Rules v1). |
| **B** | `gap × log(1 + depth)` | Reduces influence of large depth. |
| **C** | `gap × log(1 + two_qubit_gates)` | Hardware-relevant gate count. |

## Ranking stability (top 3 per molecule)

### BeH2

- **Formula A (gap × depth):** parity+uccsd, bravyi_kitaev+uccsd, jordan_wigner+uccsd
- **Formula B (gap × log(1+depth)):** parity+uccsd, bravyi_kitaev+uccsd, jordan_wigner+uccsd
- **Formula C (gap × log(1+2q_gates)):** parity+uccsd, bravyi_kitaev+uccsd, jordan_wigner+uccsd
- Ranking: **stable** across A, B, C for top 3.

### H2

- **Formula A (gap × depth):** parity+uccsd, jordan_wigner+uccsd, bravyi_kitaev+uccsd
- **Formula B (gap × log(1+depth)):** jordan_wigner+uccsd, parity+uccsd, bravyi_kitaev+uccsd
- **Formula C (gap × log(1+2q_gates)):** jordan_wigner+uccsd, parity+uccsd, bravyi_kitaev+uccsd
- Ranking: **differs** between formulas (A vs B or A vs C).

## Recommendation

For **Standard Suite v1**, the official balanced score remains:

```
balanced_score = gap × depth
```

This is implemented in `qencode.leaderboard.model.compute_balanced_score` and documented in `docs/LEADERBOARD_RULES_V1.md`. Formulas B and C can be revisited in a future rules version if hardware cost or depth scaling becomes a priority.
