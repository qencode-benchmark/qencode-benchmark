# Benchmark Specification v2

This document defines the benchmark scope and rules for QEncode Standard Suite v2.

## Scope

Suite v2 extends v1 with a broader molecule set while preserving reproducibility constraints.

Canonical source of truth:

- `benchmarks/standard/suite_v2.yaml`

## Molecules (v2)

- H2
- BeH2
- HF
- LiH
- N2

## Fixed benchmark dimensions

- Basis set: `sto3g`
- Mappings: `jordan_wigner`, `bravyi_kitaev`, `parity`
- Ansatzes:
  - `uccsd` (`reps=1`)
  - `hardware_efficient` (`reps=2`)
- Backends: `ideal`, `shots`, `noisy`

## Required metrics

Each suite result must include:

- `vqe_energy`
- `exact_energy`
- `gap_ideal`
- `gap_shots`
- `gap_noisy`
- `depth`
- `num_2q_gates`
- `terms`
- `groups`

## Notes

- v2 is used for expanded workload benchmarking and future leaderboard evolution.
- Official public ranking rules remain tied to published leaderboard rule versions.
- Any change to fixed dimensions above requires a new suite/rules version.
