# qencode-db v1 Schema (human readable)

Each DB entry is a single JSON file representing a molecule encoding and artifacts.

## Required top-level fields
- schema_version (string)
- entry_id (string, unique)
- created_utc (string, ISO-8601 UTC)
- source (object)
- problem (object)
- settings (object)
- artifacts (object)
- validation (object)
- provenance (object)

## problem
- type: "molecule"
- name: e.g. "H2", "LiH"
- geometry.units: "angstrom"
- geometry.atoms: list of { element, xyz [x,y,z] }
- charge (int)
- multiplicity (int)

## settings
- chemistry: { basis, driver, reference_method }
- reduction: { freeze_core, active_space }
- mapping: { type, two_qubit_reduction, z2_symmetry_reduction }
- ansatz: { type, initial_state, reps }
- estimation: { shots, backend }

## artifacts
- qubit_hamiltonian:
  - num_qubits (int)
  - format: "pauli_sum"
  - pauli_terms: list of { pauli (string), coeff (number) }
  - energy_offset (number)
- circuits:
  - hartree_fock_qasm (string, OpenQASM2)
  - ansatz_template_qpy_b64 (string, optional)
  - ansatz_param_names (array of strings, optional)
  - notes (string)

## validation
All fields optional. Common keys:
- hf_energy_statevector.energy (number)
- vqe.best_energy (number)
- vqe.method (string)
- exact_qubit_ground_energy.energy (number)

## provenance
- input_fingerprint.sha256 (string)
- notes (array of strings)

