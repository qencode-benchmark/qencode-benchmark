import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import base64
import io

from importlib.metadata import version as pkg_version

from qiskit import QuantumCircuit, qpy
from qiskit.qasm2 import dumps as qasm2_dumps

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def main():
    project_root = Path(__file__).resolve().parents[1]
    db_dir = project_root / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    # Molecule: H2
    molecule_name = "H2"
    units = "angstrom"
    atoms = [
        {"element": "H", "xyz": [0.0, 0.0, 0.0]},
        {"element": "H", "xyz": [0.0, 0.0, 0.735]},
    ]
    charge = 0
    multiplicity = 1

    settings = {
        "chemistry": {"basis": "sto3g", "driver": "pyscf", "reference_method": "hf"},
        "reduction": {"freeze_core": False, "active_space": None},
        "mapping": {"type": "jordan_wigner", "two_qubit_reduction": False, "z2_symmetry_reduction": False},
        "ansatz": {"type": "uccsd", "initial_state": "hartree_fock", "reps": 1},
        "estimation": {"shots": 0, "backend": "statevector_simulator"},
    }

    # Fingerprint
    input_obj = {
        "problem": {"name": molecule_name, "units": units, "atoms": atoms, "charge": charge, "multiplicity": multiplicity},
        "settings": settings,
    }
    input_hash = sha256_text(json.dumps(input_obj, sort_keys=True))

    # Qiskit Nature imports
    try:
        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD
    except Exception as e:
        raise RuntimeError(f"Qiskit Nature imports failed: {e}")

    atom_str = "H 0.0 0.0 0.0; H 0.0 0.0 0.735"
    driver = PySCFDriver(atom=atom_str, basis="sto3g", charge=charge, spin=multiplicity - 1)
    problem = driver.run()

    second_q_op = problem.hamiltonian.second_q_op()

    mapper = JordanWignerMapper()
    qubit_op = mapper.map(second_q_op)

    # Hamiltonian as Pauli terms
    pauli_terms = []
    for pauli, coeff in zip(qubit_op.paulis, qubit_op.coeffs):
        c = complex(coeff)
        if abs(c.imag) > 1e-10:
            raise ValueError(f"Non-trivial imaginary coefficient {c}")
        pauli_terms.append({"pauli": pauli.to_label(), "coeff": float(c.real)})

    qubit_hamiltonian = {
        "num_qubits": qubit_op.num_qubits,
        "format": "pauli_sum",
        "pauli_terms": pauli_terms,
        "energy_offset": 0.0
    }

    # Hartree-Fock circuit (QASM2)
    hf_circuit = HartreeFock(problem.num_spin_orbitals, problem.num_particles, mapper)
    hartree_fock_qasm = qasm2_dumps(hf_circuit)

    # UCCSD ansatz (particle-number conserving)
    num_spatial_orbitals = problem.num_spin_orbitals // 2

    uccsd = UCCSD(
        num_spatial_orbitals,
        problem.num_particles,
        qubit_mapper=mapper
    )


# Attach Hartree–Fock initial state (required in 0.7.2)
    uccsd_circuit = uccsd.decompose(reps=10)

    buf = io.BytesIO()
    qpy.dump(uccsd, buf)
    ansatz_template_qpy_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    ansatz_param_names = [p.name for p in uccsd_circuit.parameters]

    # Versions
    qiskit_version = pkg_version("qiskit")
    qiskit_nature_version = pkg_version("qiskit-nature")
    pyscf_version = pkg_version("pyscf")

    entry = {
        "schema_version": "1.0.0",
        "entry_id": f"{molecule_name}_sto3g_JW_uccsd_v1__sha256_{input_hash[:16]}",
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
                "ansatz_template_qasm": "",
                "ansatz_template_qpy_b64": ansatz_template_qpy_b64,
                "ansatz_param_names": ansatz_param_names,
                "notes": "HF stored as QASM2; UCCSD ansatz stored as QPY (base64). HF is NOT embedded in the ansatz to avoid blueprint compose issues; compose HF+ansatz at runtime."
            },
            "resources": {}
        },
        "validation": {},
        "provenance": {
            "input_fingerprint": {"sha256": input_hash},
            "notes": ["H2 with UCCSD ansatz (particle-number conserving)"]
        }
    }

    out_path = db_dir / f"{entry['entry_id']}.json"
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    print(f"✅ Wrote: {out_path}")
    print(f"✅ num_qubits: {qubit_hamiltonian['num_qubits']}, pauli_terms: {len(pauli_terms)}, params: {len(ansatz_param_names)}")

if __name__ == "__main__":
    main()

