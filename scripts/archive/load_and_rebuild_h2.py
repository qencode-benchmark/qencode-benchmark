import json
import base64
import io
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit import qpy
from qiskit.qasm2 import loads as qasm2_loads

def main():
    project_root = Path(__file__).resolve().parents[1]
    db_dir = project_root / "db"

    # Pick the newest JSON file in db/
    newest = sorted(db_dir.glob("H2_sto3g_JW_geom_v1__sha256_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[0]
    print(f"✅ Loading entry: {newest.name}")

    entry = json.loads(newest.read_text(encoding="utf-8"))
    circuits = entry["artifacts"]["circuits"]

    # 1) Rebuild Hartree-Fock circuit from QASM2
    hf_qasm = circuits["hartree_fock_qasm"]
    hf_circuit = qasm2_loads(hf_qasm)
    print("✅ Rebuilt HF circuit")
    print(hf_circuit)

    # 2) Rebuild Ansatz from QPY base64
    ansatz_b64 = circuits["ansatz_template_qpy_b64"]
    ansatz_bytes = base64.b64decode(ansatz_b64.encode("ascii"))
    buf = io.BytesIO(ansatz_bytes)
    ansatz_circuit = qpy.load(buf)[0]
    print("✅ Rebuilt Ansatz circuit")
    print(ansatz_circuit)

    # 3) Show parameters
    param_names = circuits.get("ansatz_param_names", [])
    print(f"✅ Ansatz parameters ({len(param_names)}): {param_names}")

    # 4) (Optional) Combine HF + Ansatz into one circuit (template)
    combined = QuantumCircuit(hf_circuit.num_qubits)
    combined.compose(hf_circuit, inplace=True)
    combined.compose(ansatz_circuit, inplace=True)

    print("✅ Combined HF + Ansatz (template)")
    print(combined)

if __name__ == "__main__":
    main()

