# QEncode Suite v4.0 — Release Notes

**Released:** 2026-05-17
**Schema version:** 4.0.0
**Basis:** cc-pVDZ (publication-grade, replaces 6-31G from v3)
**Total certified entries:** 28

---

## Summary

Suite v4.0 upgrades the benchmark from the STO-3G/6-31G basis to **cc-pVDZ** — the standard
publication-grade basis for correlated quantum chemistry. The same 7 molecules from v3 are
retained; active spaces are unchanged (chemistry-driven, not basis-driven). All 28 entries
meet the certification threshold: |E_VQE − E_CASCI| < 0.01 Ha.

New in v4.0:
- **cc-pVDZ basis** for all entries
- **CASSCF orbital optimization** support (`--orbital-opt casscf`) — required for N2
- **BK tapering transparency** fields (`bk_imaginary_stripped`, `bk_max_imaginary_abs_ha`)
- **Schema 4.0.0** — formally documented, stricter entry_id format, new provenance fields
- **N2 certified** for the first time (CASSCF + 20 multistarts; was "research tier" in v3)

---

## Entry Counts by Molecule

| Molecule | Active Space | Qubits (JW) | Entries | Mappings | Notes |
|----------|-------------|-------------|---------|----------|-------|
| H2       | [2e, 2o]    | 4 → 1       | 6       | JW, PAR, BK | All 6 certified (JW+PAR+BK × HEA+UCCSD) |
| HF       | [2e, 2o]    | 4 → 1       | 6       | JW, PAR, BK | All 6 certified |
| LiH      | [4e, 4o]    | 8 → 5       | 3       | JW, PAR  | JW/HEA, JW/UCCSD, PAR/HEA |
| BeH2     | [4e, 4o]    | 8           | 4       | JW, PAR  | JW+PAR × HEA+UCCSD |
| H2O      | [4e, 4o]    | 8           | 3       | JW, PAR  | JW/HEA, JW/UCCSD, PAR/HEA |
| NH3      | [4e, 4o]    | 8           | 3       | JW, PAR  | JW/HEA, JW/UCCSD, PAR/HEA |
| N2       | [6e, 6o]    | 12          | 3       | JW, PAR  | CASSCF orbitals; JW/HEA, JW/UCCSD, PAR/HEA |
| **Total**| —           | —           | **28**  | —        | All certified |

---

## Known Limitations and Design Decisions

### BK Tapering: H2 and HF only

PennyLane 0.45 has a known bug where BK tapering produces complex (imaginary) Pauli
coefficients that should be real by symmetry. For [2e, 2o] molecules (H2, HF), the
imaginary parts are below numerical noise (< 1e-6 × max_abs) and are safely stripped.
For [4e, 4o]+ molecules (LiH, BeH2, H2O, NH3, N2), the imaginary parts are ~7 mHa —
non-trivial physical artefacts — and BK entries are excluded.

The stripping decision is recorded transparently in every BK entry:
- `encoding.tapering.bk_imaginary_stripped` — whether stripping occurred
- `encoding.tapering.bk_max_imaginary_abs_ha` — magnitude before stripping

### PAR/UCCSD: excluded for LiH, H2O, NH3, N2

UCCSD excitation operators are generated in the Jordan-Wigner basis. When applied under
Parity tapering for [4e, 4o]+ molecules, the operator basis mismatch causes catastrophic
VQE convergence failures (gaps of 0.4–2.2 Ha). BeH2 (D∞h linear symmetry) is the
exception — PAR/UCCSD converges reliably and is certified.

PAR/HEA is fully supported for all molecules. JW/UCCSD is unaffected.

### N2: CASSCF orbital optimization required

N2 [6e, 6o] has strong multireference character (σ, σ*, πx, πx*, πy, πy* — full triple-bond
manifold). HF orbitals do not cleanly partition the π/σ manifold in cc-pVDZ, leading to slow
VQE convergence. CASSCF pre-optimization (`--orbital-opt casscf`) is required for N2 entries
and is the default when using `--molecule N2` in the v4 generator.

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
--orbital-opt casscf        # CASSCF orbital optimization (required for N2)
--multistart 20             # Recommended for N2; default 10
--basis cc-pvdz             # Default; can override for custom runs
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

Optionally also tracked:
```
beats_classical = |E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

All 28 v4.0 entries meet the certification threshold.

---

## Reproducibility

Each entry contains:
- Full geometry (PySCF atom-string), basis, active space, orbital optimization method
- All tool versions (PySCF, PennyLane, NumPy, SciPy, OpenFermion)
- SHA-256 provenance hash over scientific content (timestamps and git SHA excluded)
- Optimal VQE parameters for circuit reconstruction

To regenerate any entry:
```bash
python scripts/generate_entry_v4.py \
  --molecule LiH --mapping jordan_wigner --ansatz uccsd \
  --out-dir releases/v4/db/
```

---

## v3 Compatibility

v3 entries in `releases/v3/db/` are unmodified and remain reproducible with
`requirements-v3.txt`. The v4 generator (`generate_entry_v4.py`) is a separate file
and does not modify v3 outputs.

---

## What's Next: v4.1

- ADAPT-VQE ansatz (`--ansatz-type adapt`)
- New molecules: butadiene [4e, 4o], formaldehyde [4e, 4o]
- GPU backend (`lightning.gpu`) for larger molecules

See `docs/V4_PLAN.md` for the full roadmap.
