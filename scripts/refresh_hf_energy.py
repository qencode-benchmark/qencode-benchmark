import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector

from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import HartreeFock


def safe_get(d: Dict[str, Any], path: list, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def safe_set(d: Dict[str, Any], path: list, value):
    cur = d
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value


def pauli_sum_to_sparse_pauli_op(qubit_h: Dict[str, Any]) -> SparsePauliOp:
    terms = qubit_h["pauli_terms"]
    paulis = [t["pauli"] for t in terms]
    coeffs = [complex(t["coeff"]) for t in terms]
    return SparsePauliOp(paulis, coeffs)


def rebuild_hf_for_entry(num_qubits: int, ansatz_recipe: Dict[str, Any]):
    """
    For JW mapping: num_qubits = 2 * num_spatial_orbitals.
    We need num_particles; we store it in ansatz_recipe for UCCSD entries.
    """
    if num_qubits % 2 != 0:
        raise ValueError("Expected even num_qubits for electronic structure (2 * spatial orbitals).")

    num_spatial_orbitals = num_qubits // 2
    num_particles = ansatz_recipe.get("num_particles", None)
    if num_particles is None:
        raise ValueError("Cannot rebuild HF: ansatz_recipe.num_particles is missing.")

    mapper = JordanWignerMapper()
    hf = HartreeFock(num_spatial_orbitals, tuple(num_particles), mapper)
    return hf


def expectation_energy(H: SparsePauliOp, circ) -> float:
    sv = Statevector.from_instruction(circ)
    val = np.real(sv.expectation_value(H))
    return float(val)


def refresh_one(file_path: Path, write: bool = True) -> Dict[str, Any]:
    data = json.loads(file_path.read_text(encoding="utf-8"))

    qubit_h = safe_get(data, ["artifacts", "qubit_hamiltonian"])
    if qubit_h is None:
        raise ValueError("Missing artifacts.qubit_hamiltonian")
    H = pauli_sum_to_sparse_pauli_op(qubit_h)
    nq = int(qubit_h["num_qubits"])

    hf_qasm = safe_get(data, ["artifacts", "circuits", "hartree_fock_qasm"], "")
    if not hf_qasm:
        raise ValueError("Missing artifacts.circuits.hartree_fock_qasm")

    hf_circ = qasm2_loads(hf_qasm)

    ansatz_recipe = safe_get(data, ["artifacts", "circuits", "ansatz_recipe"], {}) or {}

    hf_rebuilt = False
    if hf_circ.num_qubits != nq:
        try:
            hf_circ = rebuild_hf_for_entry(nq, ansatz_recipe)
            hf_rebuilt = True
        except Exception:
            # If rebuild fails, keep original HF circuit and still compute energy if possible
            hf_rebuilt = False

    ehf = expectation_energy(H, hf_circ)

    # Write to a consistent place in the JSON
    # We'll store:
    # validation.classical_reference.hf_energy_hartree
    safe_set(data, ["validation", "classical_reference", "hf_energy_hartree"], ehf)
    safe_set(data, ["validation", "classical_reference", "hf_energy_units"], "hartree_like")
    safe_set(data, ["validation", "classical_reference", "hf_rebuilt"], hf_rebuilt)

    if write:
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {
        "file": file_path.name,
        "num_qubits": nq,
        "hf_energy": ehf,
        "hf_rebuilt": hf_rebuilt,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=None, help="Single entry JSON file to refresh")
    parser.add_argument("--db-dir", default=None, help="Refresh all entries in a DB directory")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write changes")
    args = parser.parse_args()

    if not args.file and not args.db_dir:
        raise SystemExit("Provide --file <path> or --db-dir <dir>")

    write = not args.dry_run

    if args.file:
        p = Path(args.file).expanduser().resolve()
        res = refresh_one(p, write=write)
        print(f"✅ {res['file']} | qubits={res['num_qubits']} HF={res['hf_energy']:.12f} rebuilt={res['hf_rebuilt']}")
        return

    db_dir = Path(args.db_dir).expanduser().resolve()
    files = sorted([p for p in db_dir.glob("*.json") if p.name != "index.json"])

    ok = 0
    bad = 0
    for f in files:
        try:
            res = refresh_one(f, write=write)
            print(f"✅ {res['file']} | qubits={res['num_qubits']} HF={res['hf_energy']:.12f} rebuilt={res['hf_rebuilt']}")
            ok += 1
        except Exception as e:
            print(f"❌ {f.name} | {e}")
            bad += 1

    print(f"\nDone. OK={ok}, BAD={bad}, Total={ok+bad}")


if __name__ == "__main__":
    main()

