# Standard Benchmark Suite v2

## What it is

The Standard Benchmark Suite v2 is an expanded workload intended for new experiments and algorithm research.

- v1 remains the frozen official reference set.
- v2 extends v1 with additional molecules while preserving fixed benchmarking methodology.

## Definition

- Suite YAML: `benchmarks/standard/suite_v2.yaml`

## How to run

```bash
python scripts/run_standard_suite.py --suite benchmarks/standard/suite_v2.yaml
```

Run one molecule:

```bash
python scripts/run_standard_suite.py --suite benchmarks/standard/suite_v2.yaml --molecule H2
```

## How to validate

```bash
python scripts/validate_standard_suite.py --suite benchmarks/standard/suite_v2.yaml --db-dir releases/v2/db
```

## Included in v2

| Molecules | Basis | Mappings | Ansatzes | Backends |
|---|---|---|---|---|
| H2, BeH2, HF, LiH, N2 | sto3g | JW, BK, Parity | UCCSD (reps=1), hardware_efficient (reps=2) | ideal, shots, noisy |

## Runtime notes

LiH and N2 can be significantly heavier than H2/BeH2/HF in transpilation and execution cost.
For production leaderboard refresh cycles, it is acceptable to scope metric recomputation to active leaderboard molecules.
