# QEncode Entry Schema — v3 (human readable)

Each benchmark entry is a single JSON file. The machine-readable schema is at
`schema/schema_v3.json`.

---

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | `"3"` |
| `entry_id` | string | Unique identifier encoding molecule/basis/mapping/ansatz |
| `created_utc` | string | ISO-8601 UTC timestamp |
| `problem` | object | Molecule definition |
| `encoding` | object | Qubit mapping and ansatz configuration |
| `circuit_stats` | object | Depth, 2Q gate count, parameter count |
| `results` | object | All energies and quality metrics |
| `provenance` | object | SHA-256 hash and tool versions |

---

## problem

| Field | Description |
|-------|-------------|
| `name` | Molecule name (e.g. `"LiH"`) |
| `basis` | Basis set (e.g. `"6-31g"`) |
| `geometry` | Geometry string (e.g. `"Li 0.0 0.0 0.0; H 0.0 0.0 1.594"`) |
| `charge` | Integer charge |
| `spin` | Spin multiplicity |
| `active_space.num_electrons` | Active electrons |
| `active_space.num_spatial_orbitals` | Active orbitals |
| `active_space.method` | `"casci"` |

---

## encoding

| Field | Description |
|-------|-------------|
| `mapping` | `"jordan_wigner"`, `"bravyi_kitaev"`, or `"parity"` |
| `ansatz_type` | `"uccsd"` or `"hardware_efficient"` |
| `ansatz_reps` | Number of repetitions (HEA) |
| `tapering.enabled` | Whether Z2 symmetry tapering was applied |
| `tapering.num_symmetries` | Number of qubits removed |
| `tapering.original_num_qubits` | Qubit count before tapering |
| `tapering.tapered_num_qubits` | Qubit count after tapering |

---

## results

| Field | Description |
|-------|-------------|
| `vqe.best_energy_hartree` | Lowest VQE energy found |
| `vqe.optimizer` | Optimizer used (e.g. `"COBYLA"`) |
| `vqe.multistart_runs` | Number of independent restarts |
| `vqe.num_params` | Variational parameter count |
| `reference.casci_ground_energy_hartree` | Exact CASCI ground state energy |
| `classical_comparison.hf_energy_hartree` | Hartree–Fock energy |
| `classical_comparison.ccsd_t_energy_hartree` | CCSD(T) energy |
| `classical_comparison.ccsd_t_correlation` | `\|E_CCSD(T) − E_HF\|` |
| `quality.abs_vqe_exact_gap` | `\|E_VQE − E_CASCI\|` |
| `quality.beats_classical` | `True` if gap < CCSD(T) correlation |
| `quality.trusted` | `True` if entry is Certified |

---

## provenance

| Field | Description |
|-------|-------------|
| `entry_hash_sha256` | SHA-256 of the canonical entry JSON |
| `tool_versions.python` | Python version |
| `tool_versions.pyscf` | PySCF version |
| `tool_versions.pennylane` | PennyLane version |
| `tool_versions.scipy` | SciPy version |
| `tool_versions.numpy` | NumPy version |
