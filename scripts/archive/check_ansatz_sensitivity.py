import json, base64, io
import numpy as np
from pathlib import Path

from qiskit import QuantumCircuit, qpy
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector

def build_hamiltonian(qubit_ham: dict) -> SparsePauliOp:
    paulis = [t["pauli"] for t in qubit_ham["pauli_terms"]]
    coeffs = [t["coeff"] for t in qubit_ham["pauli_terms"]]
    return SparsePauliOp.from_list(list(zip(paulis, coeffs)))

def expect(H, circ):
    sv = Statevector.from_instruction(circ)
    return float(np.real(sv.expectation_value(H)))

def main():
    path = Path("db/H2_sto3g_JW_uccsd_v1__sha256_e2167895d13b67c4.json").resolve()
    entry = json.loads(path.read_text(encoding="utf-8"))

    H = build_hamiltonian(entry["artifacts"]["qubit_hamiltonian"])
    hf = qasm2_loads(entry["artifacts"]["circuits"]["hartree_fock_qasm"])

    # load ansatz qpy
    b64 = entry["artifacts"]["circuits"]["ansatz_template_qpy_b64"]
    raw = base64.b64decode(b64.encode("ascii"))
    ansatz = qpy.load(io.BytesIO(raw))[0]

    params = list(ansatz.parameters)
    print(f"Ansatz params: {len(params)}")
    if not params:
        print("❌ No parameters found -> ansatz is trivial.")
        return

    def energy(theta_vals):
        bind = {p: v for p, v in zip(params, theta_vals)}
        c = QuantumCircuit(hf.num_qubits)
        c.compose(hf, inplace=True)
        c.compose(ansatz.assign_parameters(bind), inplace=True)
        return expect(H, c)

    e0 = energy(np.zeros(len(params)))
    print(f"E(theta=0) = {e0:.12f}")

    rng = np.random.default_rng(0)
    for k in range(5):
        th = rng.normal(0, 0.2, size=len(params))
        ek = energy(th)
        print(f"E(rand {k})  = {ek:.12f} | delta={ek - e0:+.12e}")

if __name__ == "__main__":
    main()

