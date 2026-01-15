# qencode-db — Release v1

This release contains a small, reproducible dataset of **molecule → qubit encodings**
for quantum simulation workflows.

It is designed to be:
- reproducible
- machine-readable
- extensible
- suitable for benchmarking and research

---

## Contents

- `schema_v1.json`  
  Machine-readable JSON Schema used to validate each entry.

- `SCHEMA.md`  
  Human-readable explanation of the schema fields and design choices.

- `molecules_v1.json`  
  Batch configuration used to generate this release.

- `db/`  
  The actual dataset:
  - individual entry JSON files
  - `index.json` (summary index)
  - `benchmarks.csv` (tabular summary)

---

## What is inside each entry (`db/*.json`)

Each entry represents **one molecule encoded into qubits** and includes:

### Problem definition
- molecule name
- atomic geometry
- charge
- multiplicity

### Settings
- basis set (e.g. STO-3G)
- fermion → qubit mapping (e.g. Jordan–Wigner)
- ansatz type and repetitions
- active space configuration (if used)

### Artifacts
- qubit Hamiltonian (Pauli sum)
- Hartree–Fock circuit (OpenQASM 2)
- ansatz stored as either:
  - `ansatz_template_qpy_b64` (QPY base64), or
  - `ansatz_recipe` (rebuild instructions when circuit is too large)

### Validation (when feasible)
- Hartree–Fock energy
- VQE result
- exact qubit minimum eigenvalue (for small qubit counts)

---

## Quick start (from repository root)

### 1. Validate schema
```bash
python scripts/validate_schema.py --db-dir releases/v1/db
python scripts/build_index.py --db-dir releases/v1/db
python scripts/query_index.py --molecule H2
python scripts/query_index.py --active-space true
python scripts/query_index.py --validated
python scripts/report_benchmarks.py --db-dir releases/v1/db --sort molecule
python scripts/report_benchmarks.py --db-dir releases/v1/db --csv --sort vqe

---

### What to do now
1. Paste this into `releases/v1/RELEASE.md`
2. Save the file
3. You’re done — the release is **complete and professional**

If you want, next we can:
- do a **final v1 audit checklist**
- plan **v1.1 scaling (more molecules)**
- or talk about **how this becomes a product / IP**

