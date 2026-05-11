# releases/v3/db/

This directory stores completed QEncode Suite v3 benchmark entries.

## Entry naming convention

```
{MOLECULE}_{BASIS}_{MAPPING}_{ANSATZ}_v3_tapered__sha256_{hash16}.json
```

Example:
```
LiH_sto3g_JW_uccsd_v3_tapered__sha256_a1b2c3d4e5f60718.json
```

## What's different from v2

| Feature | v2 | v3 |
|---------|----|----|
| Pipeline | qiskit-nature | PySCF + PennyLane |
| Reference energy | Full-system exact (NumPy eigensolver on qubit H) | CASCI active-space FCI |
| Classical comparison | None | HF, MP2, CCSD, CCSD(T) — REQUIRED |
| Z2 tapering | Optional | Enabled by default |
| LiH active space | [2,2] | [4,4] |
| New molecules | — | H2O, NH3 |
| Schema | schema_v2.json | schema_v3.json |

## Generating entries

Phase 1 will add `scripts/generate_entry_v3.py`.
Until then, this directory is empty — Phase 0 only sets up the skeleton.

## Suite definition

See `benchmarks/v3/suite_v3.yaml` for the canonical molecule × encoding × ansatz matrix.
