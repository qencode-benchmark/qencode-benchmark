# ADAPT without the early-stop rule

Three entries re-run with `--no-early-stop`, gradient inner optimiser, everything else
unchanged. Cluster, 2026-09-09.

| molecule | published: stops at the bar | run to convergence | improvement |
|---|---|---|---|
| H4 | 9.9417 mHa, 1 operator | 0.0514 mHa, 22 operators | x193 |
| C4H6 | 2.8286 mHa, 1 operator | 0.00033 mHa, 9 operators | x8,500 |
| H2CO | 1.1239 mHa, 1 operator | 0.00395 mHa, 7 operators | x285 |

H4 certifies with a single operator and stops there. The published 9.94 mHa is not an
ansatz limit; it is the first point past the threshold.

See [`docs/SUITE_BALANCE.md`](../../docs/SUITE_BALANCE.md).
