import json
import base64
import io
import argparse
from pathlib import Path

import numpy as np

from qiskit import QuantumCircuit
from qiskit import qpy
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.circuit import ParameterVector

def load_entry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def build_hamiltonian(qubit_ham: dict) -> SparsePauliOp:
    paulis = [t["pauli"] for t in qubit_ham["pauli_terms"]]
    coeffs = [t["coeff"] for t in qubit_ham["pauli_terms"]]
    return SparsePauliOp.from_list(list(zip(paulis, coeffs)))

def load_hf_circuit(qasm_text: str) -> QuantumCircuit:
    return qasm2_loads(qasm_text)

def load_ansatz_qpy_b64(b64: str) -> QuantumCircuit:
    raw = base64.b64decode(b64.encode("ascii"))
    buf = io.BytesIO(raw)
    return qpy.load(buf)[0]

def expectation_value(H: SparsePauliOp, circuit: QuantumCircuit) -> float:
    sv = Statevector.from_instruction(circuit)
    value = np.real(sv.expectation_value(H))
    return float(value)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to entry JSON in db/")
    parser.add_argument("--vqe", action="store_true", help="Run a simple VQE (recommended for H2 only)")
    args = parser.parse_args()

    entry_path = Path(args.file).resolve()
    entry = load_entry(entry_path)

    mol = entry["problem"]["name"]
    qubit_ham = entry["artifacts"]["qubit_hamiltonian"]
    H = build_hamiltonian(qubit_ham)

    circuits = entry["artifacts"]["circuits"]
    hf = load_hf_circuit(circuits["hartree_fock_qasm"])
    ansatz = load_ansatz_qpy_b64(circuits["ansatz_template_qpy_b64"])

    # HF energy
    hf_energy = expectation_value(H, hf)
    print(f"✅ {mol}: HF energy (statevector) = {hf_energy:.12f} Hartree")

    if not args.vqe:
        return

    # Simple VQE: random-search + small local tweaks (super robust, no dependencies)
    # This is not the fanciest optimizer but it's reliable for v1 proof.
    params = list(ansatz.parameters)
    if len(params) == 0:
        raise RuntimeError("Ansatz has no parameters; cannot run VQE.")

    def build_combined(theta_vals):
        bind = {p: v for p, v in zip(params, theta_vals)}
        combined = QuantumCircuit(hf.num_qubits)
        combined.compose(hf, inplace=True)
        combined.compose(ansatz.assign_parameters(bind), inplace=True)
        return combined

    best_theta = np.zeros(len(params))
    best_energy = expectation_value(H, build_combined(best_theta))

    print(f"🔎 {mol}: starting energy (theta=0) = {best_energy:.12f}")

    rng = np.random.default_rng(123)
    # Keep this small for v1; for H2 it’s enough to show improvement
    for step in range(200):
        candidate = best_theta + rng.normal(0.0, 0.2, size=len(params))
        e = expectation_value(H, build_combined(candidate))
        if e < best_energy:
            best_energy = e
            best_theta = candidate
            if step % 10 == 0:
                print(f"✅ improved at step {step}: {best_energy:.12f}")

    print(f"🏁 {mol}: VQE-best energy (simple search) = {best_energy:.12f} Hartree")
    print(f"📌 {mol}: improvement vs HF = {hf_energy - best_energy:.12f} Hartree")

if __name__ == "__main__":
    main()

