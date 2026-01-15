import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from qiskit import qasm2
from qiskit.circuit import ParameterVector
from qiskit import QuantumCircuit
import base64
import io
from qiskit import qpy

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def main():
    # --- Paths ---
    project_root = Path(__file__).resolve().parents[1]
    db_dir = project_root / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    # 1) Define the molecule (H2)
    molecule_name = "H2"
    units = "angstrom"
    atoms = [
        {"element": "H", "xyz": [0.0, 0.0, 0.0]},
        {"element": "H", "xyz": [0.0, 0.0, 0.735]},
    ]
    charge = 0
    multiplicity = 1

    # 2) Define settings (v1 locked)
    settings = {
        "chemistry": {"basis": "sto3g", "driver": "pyscf", "reference_method": "hf"},
        "reduction": {"freeze_core": False, "active_space": None},
        "mapping": {"type": "jordan_wigner", "two_qubit_reduction": False, "z2_symmetry_reduction": False},
        "ansatz": {"type": "hardware_efficient", "initial_state": "hartree_fock", "reps": 2},
        "estimation": {"shots": 0, "backend": "statevector_simulator"},
    }

    # 3) Build an input fingerprint for reproducibility
    input_obj = {
        "problem": {
            "name": molecule_name,
            "units": units,
            "atoms": atoms,
            "charge": charge,
            "multiplicity": multiplicity,
        },
        "settings": settings,
    }
    input_text = json.dumps(input_obj, sort_keys=True)
    input_hash = sha256_text(input_text)

    # 4) Build REAL qubit Hamiltonian using PySCF + Qiskit Nature (Jordan–Wigner)
    from importlib.metadata import version as pkg_version

    try:
        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.second_q.circuit.library import HartreeFock
    except Exception as e:
        raise RuntimeError(
            "Qiskit Nature imports failed. Make sure you installed: qiskit-nature and pyscf.\n"
            "Run: pip install qiskit qiskit-nature pyscf\n"
            f"Original error: {e}"
        )

    # Build molecule string for PySCFDriver (same geometry as above)
    atom_str = "H 0.0 0.0 0.0; H 0.0 0.0 0.735"

    driver = PySCFDriver(
        atom=atom_str,
        basis=settings["chemistry"]["basis"],
        charge=charge,
        spin=multiplicity - 1,  # multiplicity = 2S+1 -> spin = 2S
    )

    problem = driver.run()
    second_q_op = problem.hamiltonian.second_q_op()

    mapper = JordanWignerMapper()
    qubit_op = mapper.map(second_q_op)
    num_spin_orbitals = problem.num_spin_orbitals
    num_particles = problem.num_particles

    hf_circuit = HartreeFock(
        num_spin_orbitals,
        num_particles,
        mapper
    )

    hartree_fock_qasm = qasm2.dumps(hf_circuit)

# 4b) Build a simple hardware-efficient ansatz template
# 4b) Hardware-efficient ansatz template (reps=2)
    n = qubit_op.num_qubits
    reps = 2

    theta = ParameterVector("theta", length=2 * n * reps)
    ansatz_circuit = QuantumCircuit(n)

    k = 0
    for r in range(reps):
    # single-qubit rotations
        for i in range(n):
            ansatz_circuit.ry(theta[k], i)
            k += 1

        for i in range(n):
            ansatz_circuit.rz(theta[k], i)
            k += 1

        # entanglement (linear chain)
        for i in range(n - 1):
            ansatz_circuit.cx(i, i + 1)



# Export to OpenQASM2 (parameters will appear as symbols in the QASM output)
    # QASM2 cannot represent circuits with unbound parameters, so store QPY (supports parameters)
    import base64, io
    from qiskit import qpy

    buf = io.BytesIO()
    qpy.dump(ansatz_circuit, buf)
    ansatz_template_qpy_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

# Parameter names for readability
    ansatz_param_names = [p.name for p in ansatz_circuit.parameters]

# Keep QASM empty for template circuits in v1
    ansatz_template_qasm = ""

# QASM2 cannot represent circuits with unbound parameters, so we store QPY instead (supports params)
    buf = io.BytesIO()
    qpy.dump(ansatz_circuit, buf)
    ansatz_template_qpy_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

# Also store parameter names for readability
    ansatz_param_names = [p.name for p in ansatz_circuit.parameters]

# Keep QASM empty in v1 for param circuits
    ansatz_template_qasm = ""

    pauli_terms = []
    for pauli, coeff in zip(qubit_op.paulis, qubit_op.coeffs):
        c = complex(coeff)
        if abs(c.imag) > 1e-10:
            raise ValueError(f"Found non-trivial imaginary coefficient {c}.")
        pauli_terms.append({"pauli": pauli.to_label(), "coeff": float(c.real)})

    qubit_hamiltonian = {
        "num_qubits": qubit_op.num_qubits,
        "format": "pauli_sum",
        "pauli_terms": pauli_terms,
        "energy_offset": 0.0
    }

    # Package versions for reproducibility
    qiskit_version = pkg_version("qiskit")
    qiskit_nature_version = pkg_version("qiskit-nature")
    pyscf_version = pkg_version("pyscf")

    # 5) Assemble the JSON entry
    entry = {
        "schema_version": "1.0.0",
        "entry_id": f"{molecule_name}_sto3g_JW_geom_v1__sha256_{input_hash[:16]}",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "generator": {"name": "qencode-db", "version": "0.1.0", "git_commit": "local"},
            "software": {"python": "local", "qiskit": qiskit_version, "qiskit_nature": qiskit_nature_version, "pyscf": pyscf_version},
        },
        "problem": {
            "type": "molecule",
            "name": molecule_name,
            "geometry": {"units": units, "atoms": atoms},
            "charge": charge,
            "multiplicity": multiplicity
        },
        "settings": settings,
        "artifacts": {
            "qubit_hamiltonian": qubit_hamiltonian,
            "circuits": {
                   "hartree_fock_qasm": hartree_fock_qasm,
                   "ansatz_template_qasm": ansatz_template_qasm,
                   "ansatz_template_qpy_b64": ansatz_template_qpy_b64,
                   "ansatz_param_names": ansatz_param_names,
                   "ansatz_template_qpy_b64": ansatz_template_qpy_b64,
                   "ansatz_param_names": ansatz_param_names,
                   "notes": "HF stored as QASM2; ansatz stored as QPY (base64) because it has parameters"
            },
            "resources": {}
        },
        "validation": {
            "classical_reference": {"method": "FCI", "energy": None, "units": "hartree"},
            "vqe_run": {"optimizer": None, "maxiter": None, "estimated_ground_energy": None, "units": "hartree"},
            "tolerance": {"abs_energy_error": None}
        },
        "provenance": {
            "input_fingerprint": {"sha256": input_hash},
            "notes": ["Real qubit Hamiltonian generated with PySCF + Qiskit Nature + Jordan-Wigner"]
        }
    }

    # 6) Write JSON file to db/
    out_path = db_dir / f"{entry['entry_id']}.json"
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    print(f"✅ Wrote: {out_path}")
    print(f"✅ num_qubits: {qubit_hamiltonian['num_qubits']}, pauli_terms: {len(pauli_terms)}")

if __name__ == "__main__":
    main()
