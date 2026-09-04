# QEncode entry schema — v4 (human readable)

Each benchmark entry is a single JSON file. The machine-readable schema is
`schema/schema_v4.json`; the frozen earlier suites use `schema/schema_v3.json` and
`schema/schema_v2.json`.

An entry records everything needed to rebuild the result: the problem, the encoding, the
Hamiltonian itself, the optimiser configuration, the energies, the exact software
environment, and a content hash over all of it. The field list below is generated from
the 54 published entries, so it describes what is actually there rather than what was
once intended.

`schema_version` is `"4.0.0"` on every v4 entry.

---

## Top level

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"4.0.0"` |
| `entry_id` | string | Unique id: molecule, basis, mapping, ansatz, orbital treatment, and the first 16 hex of the content hash. Also the filename. |
| `created_utc` | string | ISO-8601 UTC timestamp |
| `problem` | object | What was solved |
| `encoding` | object | How it was mapped to qubits, and the ansatz |
| `artifacts` | object | The qubit Hamiltonian and circuit inputs |
| `results` | object | All energies and the quality verdict |
| `run_config` | object | Optimiser settings actually used |
| `circuit_stats` | object | Circuit size and fault-tolerant cost estimates |
| `provenance` | object | Content hash, tool versions, environment |
| `trust` | object | Tier and signature |

---

## `problem`

| Field | Description |
|---|---|
| `name` | Molecule, e.g. `"LiH"` |
| `basis` | Basis set — `"cc-pvdz"` throughout Suite v4 |
| `geometry` | PySCF geometry string, Ångström, e.g. `"Li 0.0 0.0 0.0; H 0.0 0.0 1.6"` |
| `charge`, `spin` | Integers; `0, 0` for every current entry |
| `variant` | Geometry variant label, `"default"` unless a stretched or scanned geometry |
| `active_space` | `num_electrons`, `num_spatial_orbitals`, `method` (`"casci"`), `frozen_core` |
| `orbital_optimization` | `"hf"` or `"casscf"` — **part of the problem, not a setting.** The two give different active-space Hamiltonians and different reference energies. |

---

## `encoding`

| Field | Description |
|---|---|
| `mapping` | `jordan_wigner`, `parity`, or `bravyi_kitaev` |
| `ansatz_type` | `uccsd_tapered`, `hea`, or `adapt` |
| `ansatz_reps` | Layer count for `hea`; 1 otherwise |
| `adapt_metadata` | ADAPT entries only: pool size, the selected operator indices in order, gradient threshold, operator cap, whether it converged, iteration count |
| `tapering` | Z2 tapering: `num_symmetries`, `original_num_qubits`, `tapered_num_qubits`, the chosen `sectors`, the tapered HF state, and the Bravyi-Kitaev constant/imaginary corrections when applied |

---

## `artifacts`

| Field | Description |
|---|---|
| `qubit_hamiltonian` | `num_qubits`, `num_pauli_terms`, the full `pauli_terms` list (coefficient and Pauli string), `is_tapered`, `framework` |
| `circuits` | `hf_state` (tapered Hartree-Fock occupation), `ansatz_pennylane`, `ansatz_includes_hf` |

The Hamiltonian is stored in full. An entry is therefore checkable without re-running
PySCF: the Pauli decomposition can be diagonalised directly.

---

## `results`

**`reference`** — what the VQE is aiming at.

| Field | Description |
|---|---|
| `casci_ground_energy_hartree` | Exact diagonalisation in the active space |
| `exact_qubit_ground_energy_hartree` | Ground state of the stored qubit Hamiltonian — **this is what the gap is measured against** |
| `hf_energy_hartree`, `casci_first_excited_hartree`, `casscf_energy_hartree` | Context |

**`classical_comparison`** — HF, MP2, CCSD, CCSD(T) energies and correlation energies on
the same molecule and basis, plus the PySCF version that produced them.

**`vqe`** — `best_energy_hartree`, `optimal_params`, `num_params`, `nfev`, `optimizer`,
`multistart_runs`.

**`quality`** — the verdict.

| Field | Description |
|---|---|
| `abs_vqe_exact_gap` | `\|E_VQE − E_exact\|` in Hartree. **The benchmark metric.** |
| `gap_threshold` | `0.01` Ha |
| `trusted` | `abs_vqe_exact_gap < gap_threshold`. This, and only this, is certification. |
| `gap_reference` | `"exact_qubit_hamiltonian"` |
| `beats_classical` | VQE error smaller than the CCSD(T) correlation energy. Informational, weaker than it sounds, and true for all 54 entries — see [`docs/TRUST_POLICY.md`](docs/TRUST_POLICY.md) |
| `flags`, `notes` | Machine-readable markers and free text |

---

## `run_config`

| Field | Description |
|---|---|
| `optimizer` | e.g. `"COBYLA"`, `"L-BFGS-B"`, `"ADAPT-VQE (COBYLA inner)"` |
| `max_iterations`, `multistart`, `multistart_requested` | `multistart` is restarts actually completed; `multistart_requested` is what was asked for, which differs when early-stop fired |
| `early_stopped` | Whether the run stopped on reaching the threshold |
| `seed` | RNG seed — necessary for reproducibility but **not sufficient**; see `provenance.environment` |
| `backend_type` | Simulator device. Gradient-free entries must be `default.qubit` — see [`docs/LEADERBOARD_RULES_V2.md`](docs/LEADERBOARD_RULES_V2.md) |
| `shots` | `null` — every published entry is exact statevector, not sampled |

---

## `circuit_stats`

| Field | Description |
|---|---|
| `num_qubits_original`, `num_qubits_tapered` | Before and after Z2 tapering |
| `ansatz_num_parameters`, `ansatz_depth`, `ansatz_num_1q_gates`, `ansatz_num_2q_gates` | Near-term cost. Symbolic for UCCSD and ADAPT until compiled for a target, and suppressed on the cost leaderboard when so. |
| `non_clifford_gate_count`, `t_gate_estimate`, `t_gate_synthesis_epsilon` | Fault-tolerant cost. Derived by post-processing the Pauli decomposition under qubitized QPE assumptions — an estimate, not a compiled count. |
| `cost_basis` | How the above were derived, when the derivation is not the default |

---

## `provenance`

| Field | Description |
|---|---|
| `entry_hash_sha256` | SHA-256 over the canonical entry with volatile fields stripped: timestamps, `entry_id`, the hash itself, the git commit, and the signature |
| `tool_versions` | Exact Python, PySCF, PennyLane, openfermion, NumPy, SciPy versions, and the git commit that produced the entry |
| `environment` | `platform`, `blas_threads`, `threads_pinned` |
| `hamiltonian_source` | Which construction path built the Hamiltonian (`of_bridge` or PennyLane native) — not cosmetic, the two can differ in term ordering |
| `source_schema_version`, `created_utc` | |

`blas_threads` is recorded because it is the field that most often explains a
non-reproducing result. Multi-threaded BLAS sums floating point in a nondeterministic
order, and a gradient-free optimiser turns that into a different local minimum.

---

## `trust`

| Field | Description |
|---|---|
| `level` | `"certified"` or research tier |
| `certified_utc` | When the tier was assigned |
| `signature_b64`, `signing_key_id` | Ed25519 signature over the content hash. `null` on entries generated without the signing key present — the hash is still verifiable. |

---

## Related

- [`docs/TRUST_POLICY.md`](docs/TRUST_POLICY.md) — what *certified* means
- [`docs/VERIFY.md`](docs/VERIFY.md) — checking an entry, and what a check proves
- [`docs/LEADERBOARD_RULES_V2.md`](docs/LEADERBOARD_RULES_V2.md) — how entries are ranked
