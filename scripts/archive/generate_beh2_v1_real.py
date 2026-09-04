#!/usr/bin/env python3
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import base64
import io

from qiskit import qasm2, qpy

# Qiskit Nature imports (compatible with your current errors)
from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.transformers import ActiveSpaceTransformer
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD

try:
    from importlib.metadata import version as pkg_version
except Exception:
    pkg_version = None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    # -------------------------
    # Output location
    # -------------------------
    repo_root = Path(__file__).resolve().parents[1]
    db_dir = repo_root / "releases" / "v1" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Molecule: BeH2 (linear geometry)
    # -------------------------
    molecule_name = "BeH2"
    units_str = "angstrom"

    atoms = [
        {"element": "H", "xyz": [0.0, 0.0, -1.30]},
        {"element": "Be", "xyz": [0.0, 0.0, 0.0]},
        {"element": "H", "xyz": [0.0, 0.0, 1.30]},
    ]
    charge = 0
    multiplicity = 1  # singlet
    spin = multiplicity - 1  # Qiskit Nature expects 2S

    # PySCFDriver atom string
    atom_str = "H 0.0 0.0 -1.30; Be 0.0 0.0 0.0; H 0.0 0.0 1.30"

    # -------------------------
    # Settings (active space to keep it manageable)
    # BeH2 total electrons=6; active space: 4 electrons in 4 spatial orbitals => 8 qubits.
    # -------------------------
    settings = {
        "chemistry": {"basis": "sto3g", "driver": "pyscf", "reference_method": "hf"},
        "reduction": {
            "freeze_core": False,
            "active_space": {"enabled": True, "num_electrons": 4, "num_spatial_orbitals": 4},
        },
        "mapping": {"type": "jordan_wigner"},
        "ansatz": {"type": "uccsd", "initial_state": "hartree_fock", "reps": 1},
        "estimation": {"backend": "statevector", "shots": 0},
    }

    # Reproducibility fingerprint
    input_obj = {
        "problem": {
            "name": molecule_name,
            "units": units_str,
            "atoms": atoms,
            "charge": charge,
            "multiplicity": multiplicity,
        },
        "settings": settings,
    }
    input_hash = sha256_text(json.dumps(input_obj, sort_keys=True))

    # -------------------------
    # Build problem via driver.run()
    # -------------------------
    driver = PySCFDriver(
        atom=atom_str,
        basis=settings["chemistry"]["basis"],
        charge=charge,
        spin=spin,
        unit=DistanceUnit.ANGSTROM,  # IMPORTANT: enum, not string
    )

    es_problem = driver.run()

    # Some versions wrap the result; try extracting problem
    if not hasattr(es_problem, "second_q_ops") and hasattr(es_problem, "problem"):
        es_problem = es_problem.problem

    # Active space transform
    if settings["reduction"]["active_space"]["enabled"]:
        ast = ActiveSpaceTransformer(
            num_electrons=settings["reduction"]["active_space"]["num_electrons"],
            num_spatial_orbitals=settings["reduction"]["active_space"]["num_spatial_orbitals"],
        )
        es_problem = ast.transform(es_problem)

    # -------------------------
    # Hamiltonian -> qubit operator (JW)
    # -------------------------
    second_q_ops = es_problem.second_q_ops()
    hamiltonian_op = second_q_ops[0]

    mapper = JordanWignerMapper()
    mapped = mapper.map(hamiltonian_op)

    # Some versions return SparsePauliOp directly; others have .primitive
    sparse = getattr(mapped, "primitive", mapped)

    pauli_terms = []
    for p, c in zip(sparse.paulis, sparse.coeffs):
        cc = complex(c)
        if abs(cc.imag) > 1e-12:
            raise ValueError(f"Unexpected complex coefficient with imag part: {cc}")
        pauli_terms.append({"pauli": p.to_label(), "coeff": float(cc.real)})

    num_qubits = int(sparse.num_qubits)

    qubit_hamiltonian = {
        "num_qubits": num_qubits,
        "format": "pauli_sum",
        "pauli_terms": pauli_terms,
        "energy_offset": 0.0,
    }

    # -------------------------
    # HF + UCCSD ansatz template
    # -------------------------
    num_spatial_orbitals = num_qubits // 2
    num_particles = es_problem.num_particles  # (alpha, beta)

    hf = HartreeFock(num_spatial_orbitals, num_particles, mapper)
    hartree_fock_qasm = qasm2.dumps(hf)

    ansatz = UCCSD(num_spatial_orbitals, num_particles, mapper, initial_state=hf)
    ansatz_template = ansatz.decompose(reps=10)

    # IMPORTANT: Do NOT export ansatz_template to QASM2 (it has unbound parameters).
    # Store it as QPY base64 instead.
    ansatz_param_names = [str(p) for p in ansatz_template.parameters]

    buf = io.BytesIO()
    qpy.dump(ansatz_template, buf)
    ansatz_template_qpy_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    # Software versions (best effort)
    software = {"python": "local"}
    if pkg_version is not None:
        for pkg in ("qiskit", "qiskit-nature", "pyscf"):
            try:
                software[pkg.replace("-", "_")] = pkg_version(pkg)
            except Exception:
                pass

    # -------------------------
    # Build entry JSON
    # -------------------------
    entry_id = f"{molecule_name}_sto3g_JW_uccsd_v1__sha256_{input_hash[:16]}"

    entry = {
        "schema_version": "1.0.0",
        "entry_id": entry_id,
        "created_utc": now_utc(),
        "problem": {
            "type": "molecule",
            "name": molecule_name,
            "geometry": {"units": units_str, "atoms": atoms},
            "charge": charge,
            "multiplicity": multiplicity,
        },
        "settings": settings,
        "artifacts": {
            "qubit_hamiltonian": qubit_hamiltonian,
            "circuits": {
                "hartree_fock_qasm": hartree_fock_qasm,
                "ansatz_template_qpy_b64": ansatz_template_qpy_b64,
                "ansatz_param_names": ansatz_param_names,
                "ansatz_recipe": {
                    "type": "uccsd",
                    "num_particles": list(num_particles),
                    "num_spatial_orbitals": int(num_spatial_orbitals),
                    "mapper": "jordan_wigner",
                },
                "notes": "HF stored as QASM2. Ansatz is parameterized, stored as QPY base64 (QASM2 cannot store unbound parameters).",
            },
        },
        "provenance": {
            "input_fingerprint": {"sha256": input_hash},
            "notes": [
                "BeH2 generated with PySCFDriver + ActiveSpaceTransformer + JordanWignerMapper.",
                "Ansatz stored as QPY base64 (parameterized circuits cannot be exported to OpenQASM2)."
            ],
        },



        "validation": {
            "classical_reference": {
                "hf_energy_hartree": None,
            },
            "vqe_run": {},
            "exact_qubit_ground_energy": {},
        },
        "source": {
            "generator": {
                "name": "qencode-db",
                "version": "0.1.0",
                "script": "scripts/generate_beh2_v1_real.py",
            },
            "software": software,
            "input_fingerprint": {"sha256": input_hash},
        },

        "source": {
            "generator": {"script": "scripts/generate_beh2_v1_real.py"},
            "software": software,
            "input_fingerprint": {"sha256": input_hash},
        },
    }

    out_path = db_dir / f"{entry_id}.json"
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    print(f"✅ Wrote: {out_path}")
    print(f"✅ num_qubits: {num_qubits}, pauli_terms: {len(pauli_terms)}, params: {len(ansatz_param_names)}")


if __name__ == "__main__":
    main()

