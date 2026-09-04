import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from qiskit.quantum_info import SparsePauliOp

def build_hamiltonian(qubit_ham: dict) -> SparsePauliOp:
    paulis = [t["pauli"] for t in qubit_ham["pauli_terms"]]
    coeffs = [t["coeff"] for t in qubit_ham["pauli_terms"]]
    return SparsePauliOp.from_list(list(zip(paulis, coeffs)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Entry JSON file")
    parser.add_argument("--write", action="store_true", help="Write result back into JSON")
    args = parser.parse_args()

    path = Path(args.file).resolve()
    entry = json.loads(path.read_text(encoding="utf-8"))

    H = build_hamiltonian(entry["artifacts"]["qubit_hamiltonian"])
    n = entry["artifacts"]["qubit_hamiltonian"]["num_qubits"]

    # Exact diagonalization (OK for small n like 4–10; for big n it explodes)
    dim = 2 ** n
    if dim > 4096:
        raise RuntimeError(f"Too large for exact diagonalization: {n} qubits (dim={dim}). Use active space or skip.")

    mat = H.to_matrix(sparse=False)
    eigvals = np.linalg.eigvalsh(mat)
    e0 = float(np.min(eigvals))

    print(f"✅ Exact qubit-H ground energy (min eigenvalue) = {e0:.12f} Hartree-like units")

    if args.write:
        entry.setdefault("validation", {})
        entry["validation"]["exact_qubit_ground_energy"] = {
            "energy": e0,
            "units": "hartree_like",
            "computed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Exact min eigenvalue of stored qubit Hamiltonian (not necessarily physical electron-number sector)."
        }
        path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        print(f"✅ Wrote into JSON: {path.name}")

if __name__ == "__main__":
    main()

