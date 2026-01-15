# TRUST POLICY (qencode-db)

## Canonical data
- **v1 canonical VQE:** `validation.vqe`
- **v2 canonical VQE:** `results.vqe`

Legacy data is **non-canonical** and kept for traceability only:
- **v1 legacy:** `validation.legacy.*`
- **v2 legacy:** `results.legacy.*` (if present)

## Units
All energies are **hartree_like**.

## References
- **HF reference**
  - v1: `validation.classical_reference.hf_energy_hartree_like`
  - v2: `results.reference.hf_energy_hartree_like`
- **Exact reference**
  - v1: `validation.exact_qubit_ground_energy.energy`
  - v2: `results.reference.exact_qubit_ground_energy_hartree_like`

“Exact” means **exact diagonalization of the stored qubit Hamiltonian** (when feasible).

## Trusted benchmark rule (v2)
An entry is **trusted** if:
- `results.quality.trusted == true`

Default trust threshold:
- `abs(vqe - exact) <= 0.01` when both are present

Entries may be **valid but incomplete**:
- Missing VQE and/or exact values are allowed, but such entries are not trusted.

## Reproducibility
- v2 entries are derived from v1 via: `scripts/migrate_v1_to_v2.py`
- Repo-wide health check: `python3 scripts/check_all.py`

