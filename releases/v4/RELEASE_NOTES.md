# QEncode Suite v4.0 — Release Notes

**Released:** 2026-05-17
**Schema version:** 4.0.0
**Basis:** cc-pVDZ (publication-grade, replaces 6-31G from v3)
**Certified entries:** 25  |  **Validated entries:** 1 (N2)  |  **Total:** 26

---

## Summary

Suite v4.0 upgrades the benchmark from the STO-3G/6-31G basis to **cc-pVDZ** — the standard
publication-grade basis for correlated quantum chemistry. The same 7 molecules from v3 are
retained; active spaces are unchanged (chemistry-driven, not basis-driven). 25 entries meet
the certification threshold: |E_VQE − E_CASCI| < 0.01 Ha.

New in v4.0:
- **cc-pVDZ basis** for all entries
- **CASSCF orbital optimization** support (`--orbital-opt casscf`)
- **BK tapering transparency** fields (`bk_imaginary_stripped`, `bk_max_imaginary_abs_ha`)
- **Schema 4.0.0** — formally documented, stricter entry_id format, new provenance fields

---

## Entry Counts by Molecule

| Molecule | Active Space | Qubits (JW→tapered) | Certified | Mapping/Ansatz combinations | Notes |
|----------|-------------|---------------------|-----------|----------------------------|-------|
| H2       | [2e, 2o]    | 4 → 1               | 6         | JW+PAR+BK × HEA+UCCSD | All certified |
| HF       | [2e, 2o]    | 4 → 1               | 6         | JW+PAR+BK × HEA+UCCSD | All certified |
| LiH      | [4e, 4o]    | 8 → 5               | 3         | JW/HEA, JW/UCCSD, PAR/HEA | BK and PAR/UCCSD excluded |
| BeH2     | [4e, 4o]    | 8 → null            | 4         | JW+PAR × HEA+UCCSD | BK excluded |
| H2O      | [4e, 4o]    | 8 → null            | 3         | JW/HEA, JW/UCCSD, PAR/HEA | PAR/UCCSD excluded |
| NH3      | [4e, 4o]    | 8 → null            | 3         | JW/HEA, JW/UCCSD, PAR/HEA | PAR/UCCSD excluded |
| N2       | [6e, 6o]    | 12 → 8              | 0         | JW/HEA (CASSCF) | **Validated only** — see N2 note |
| **Total**| —           | —                   | **25**    | —                          | + 1 validated |

---

## N2 Status: Validated, Not Certified

N2 [6e, 6o] has 8 qubits after Z2 tapering (4 symmetries removed). CASSCF orbital
optimization was applied (`--orbital-opt casscf`) with 20 multistarts. The best gap
achieved was **0.112 Ha** — well above the 0.01 Ha certification threshold.

Root cause: HEA with `reps=2` is not sufficiently expressive for the 8-qubit N2 active
space. The triple-bond π/σ manifold requires either:
- Deeper HEA (reps ≥ 4) to cover the full entanglement structure, or
- UCCSD (which provides the correct excitation operators for this active space)

N2 certification is the primary target for **v4.1**. The validated JW/HEA entry is
included in the research leaderboard tier.

---

## Known Limitations and Design Decisions

### BK Tapering: H2 and HF only

PennyLane 0.45 has a known bug where BK tapering produces complex (imaginary) Pauli
coefficients that should be real by symmetry. For [2e, 2o] molecules (H2, HF), the
imaginary parts are below numerical noise (< 1e-6 × max_abs) and are safely stripped.
For [4e, 4o]+ molecules, the imaginary parts are ~7 mHa — non-trivial physical artefacts
— and BK entries are excluded.

Stripping decisions are recorded transparently in every BK entry:
- `encoding.tapering.bk_imaginary_stripped`
- `encoding.tapering.bk_max_imaginary_abs_ha`

### PAR/UCCSD: excluded for LiH, H2O, NH3, N2

UCCSD excitation operators are generated in the Jordan-Wigner basis. When applied under
Parity tapering for these molecules, the operator basis mismatch causes catastrophic VQE
convergence failures (gaps of 0.4–2.2 Ha). BeH2 (D∞h linear symmetry) is the exception
— PAR/UCCSD converges reliably and is certified.

PAR/HEA is fully supported for all molecules. JW/UCCSD is unaffected.

---

## Schema Changes from v3 to v4.0.0

Full schema documented in `schema/schema_v4.json`.

| Change | Details |
|--------|---------|
| `problem.orbital_optimization` | New required field: `"hf"` or `"casscf"` |
| `results.reference.casscf_energy_hartree` | CASSCF total energy when `orbital_optimization="casscf"` |
| `encoding.tapering.bk_imaginary_stripped` | Transparency flag: was BK imaginary stripping applied? |
| `encoding.tapering.bk_max_imaginary_abs_ha` | Max imaginary coefficient magnitude before stripping |
| `trust` object | Restructured: `level`/`certified_utc`/`signature_b64`/`signing_key_id` |
| `run_config`, `circuit_stats` | Now required top-level objects |
| `entry_id` format | `{mol}_{basis}_{map}_{ans}_v4[_casscf]_tapered__sha256_{hash16}` |
| Default basis | cc-pvdz (was 6-31g in v3) |

---

## Generator

```
scripts/generate_entry_v4.py
```

Key flags:
```
--molecule N2 --mapping jordan_wigner --ansatz hardware_efficient
--orbital-opt casscf        # CASSCF orbital optimization
--multistart 20             # Recommended for N2; default 10
--basis cc-pvdz             # Default; can override
```

Requirements: `requirements-v4.txt`
```
pennylane==0.45.0
numpy==2.2.6
pyscf==2.6.2
scipy==1.13.1
openfermion==1.6.1
```

---

## Certification Criterion

An entry is **CERTIFIED** when:

```
|E_VQE − E_CASCI| < 0.01 Ha  (gap threshold)
```

All 25 certified v4.0 entries meet this threshold.

---

## Reproducibility

Each entry contains full geometry, basis, active space, orbital optimization method,
all tool versions, SHA-256 provenance hash, and optimal VQE parameters.

To regenerate any entry:
```bash
python scripts/generate_entry_v4.py \
  --molecule LiH --mapping jordan_wigner --ansatz uccsd \
  --out-dir releases/v4/db/
```

---

## v3 Compatibility

v3 entries in `releases/v3/db/` are unmodified and remain reproducible with
`requirements-v3.txt`. The v4 generator is a separate file.

---

## What's Next: v4.1

- **N2 certification** — deeper HEA (reps=4) or UCCSD ansatz
- ADAPT-VQE ansatz (`--ansatz-type adapt`)
- New molecules: butadiene [4e, 4o], formaldehyde [4e, 4o]
- GPU backend (`lightning.gpu`) for larger molecules

See `docs/V4_PLAN.md` for the full roadmap.
