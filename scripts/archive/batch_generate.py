import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from importlib.metadata import version as pkg_version

# Qiskit/QPY
from qiskit import QuantumCircuit, qpy
from qiskit.qasm2 import dumps as qasm2_dumps
from qiskit.circuit import ParameterVector

# Qiskit Nature (0.7.2 compatible imports)
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper

try:
    from qiskit_nature.second_q.transformers import ActiveSpaceTransformer
except Exception:
    ActiveSpaceTransformer = None

try:
    from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD
except Exception as e:
    raise RuntimeError(f"Failed to import HartreeFock/UCCSD from qiskit_nature: {e}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deep_merge(a: dict, b: dict) -> dict:
    """Return deep merged dict (b overrides a)."""
    out = deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def atoms_to_pyscf_string(atoms):
    # "H 0 0 0; H 0 0 0.735"
    parts = []
    for at in atoms:
        x, y, z = at["xyz"]
        parts.append(f"{at['element']} {x} {y} {z}")
    return "; ".join(parts)


def build_hardware_efficient_ansatz(num_qubits: int, reps: int = 2) -> QuantumCircuit:
    """
    Simple hardware-efficient template:
      (RY on all) + (RZ on all) + (linear CX chain), repeated.
    """
    n = int(num_qubits)
    reps = int(reps)
    theta = ParameterVector("theta", length=2 * n * reps)
    qc = QuantumCircuit(n)
    k = 0
    for _ in range(reps):
        for i in range(n):
            qc.ry(theta[k], i)
            k += 1
        for i in range(n):
            qc.rz(theta[k], i)
            k += 1
        for i in range(n - 1):
            qc.cx(i, i + 1)
    return qc


def qpy_b64_safe(circ: QuantumCircuit):
    """
    Return base64 QPY if possible, else None.

    QPY can hit size/format limits for large circuits (e.g., big UCCSD),
    so we fall back to storing a recipe instead of the full circuit.
    """
    try:
        buf = io.BytesIO()
        qpy.dump(circ, buf)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def generate_entry(problem: dict, settings: dict, out_dir: Path) -> Path:
    """
    Generate one DB entry:
    - build second-quantized Hamiltonian (PySCF)
    - optional active space
    - map to qubits (JW)
    - store HF QASM2
    - store ansatz template as QPY base64 when possible, otherwise store ansatz recipe
    """
    molecule_name = problem["name"]
    atoms = problem["atoms"]
    units = problem["units"]
    charge = int(problem["charge"])
    multiplicity = int(problem["multiplicity"])

    basis = settings["chemistry"]["basis"]
    mapping_type = settings["mapping"]["type"]
    ansatz_type = settings["ansatz"]["type"]
    ansatz_reps = int(settings["ansatz"].get("reps", 1))

    # fingerprint
    input_obj = {"problem": problem, "settings": settings}
    input_hash = sha256_text(json.dumps(input_obj, sort_keys=True))

    # Driver
    atom_str = atoms_to_pyscf_string(atoms)
    driver = PySCFDriver(
        atom=atom_str,
        basis=basis,
        charge=charge,
        spin=multiplicity - 1,  # multiplicity = 2S+1 -> spin = 2S
    )
    es_problem = driver.run()

    # Optional active space
    active_space = settings.get("reduction", {}).get("active_space", {})
    if active_space and active_space.get("enabled", False):
        if ActiveSpaceTransformer is None:
            raise RuntimeError("ActiveSpaceTransformer not available in this qiskit-nature install.")
        ne = int(active_space["num_electrons"])
        nso = int(active_space["num_spatial_orbitals"])
        transformer = ActiveSpaceTransformer(num_electrons=ne, num_spatial_orbitals=nso)
        es_problem = transformer.transform(es_problem)

    second_q_op = es_problem.hamiltonian.second_q_op()

    # Mapper (v1: only JW)
    if mapping_type != "jordan_wigner":
        raise RuntimeError(f"v1 supports only jordan_wigner right now (got {mapping_type}).")
    mapper = JordanWignerMapper()
    qubit_op = mapper.map(second_q_op)

    # Hamiltonian as Pauli terms
    pauli_terms = []
    for pauli, coeff in zip(qubit_op.paulis, qubit_op.coeffs):
        c = complex(coeff)
        if abs(c.imag) > 1e-10:
            raise ValueError(f"Found non-trivial imaginary coefficient {c}")
        pauli_terms.append({"pauli": pauli.to_label(), "coeff": float(c.real)})

    qubit_hamiltonian = {
        "num_qubits": qubit_op.num_qubits,
        "format": "pauli_sum",
        "pauli_terms": pauli_terms,
        "energy_offset": 0.0,
    }

    # HF circuit
    hf = HartreeFock(es_problem.num_spin_orbitals, es_problem.num_particles, mapper)
    hartree_fock_qasm = qasm2_dumps(hf)

    # Ansatz recipe ALWAYS stored (even if QPY is available)
    ansatz_recipe = {
        "type": ansatz_type,
        "reps": ansatz_reps,
        "mapping": mapping_type,
    }

    # Ansatz template
    ansatz_param_names = []
    ansatz_qpy_b64 = None

    if ansatz_type == "hardware_efficient":
        ansatz = build_hardware_efficient_ansatz(qubit_op.num_qubits, reps=ansatz_reps)
        ansatz_param_names = [p.name for p in ansatz.parameters]
        ansatz_recipe.update({
            "num_qubits": qubit_op.num_qubits,
            "layout": "ry_rz_linear_cx",
        })
        ansatz_qpy_b64 = qpy_b64_safe(ansatz)
        if ansatz_qpy_b64 is None:
            ansatz_param_names = []

    elif ansatz_type == "uccsd":
        # IMPORTANT: Do NOT embed HF initial state in UCCSD.
        # We store HF separately and compose HF+ansatz at runtime (validator).
        num_spatial_orbitals = es_problem.num_spin_orbitals // 2

        # In Qiskit Nature 0.7.2, UCCSD signature expects spatial orbitals + particles + mapper
        uccsd = UCCSD(num_spatial_orbitals, es_problem.num_particles, qubit_mapper=mapper)

        # Materialize to a plain circuit for serialization stability
        ansatz = uccsd.decompose(reps=10)
        ansatz_param_names = [p.name for p in ansatz.parameters]

        ansatz_recipe.update({
            "num_spatial_orbitals": num_spatial_orbitals,
            "num_particles": list(es_problem.num_particles),
            "note": "UCCSD template; HF composed at runtime",
        })

        ansatz_qpy_b64 = qpy_b64_safe(ansatz)
        if ansatz_qpy_b64 is None:
            ansatz_param_names = []

    else:
        raise RuntimeError(f"Unknown ansatz type: {ansatz_type}")

    # Versions
    qiskit_version = pkg_version("qiskit")
    qiskit_nature_version = pkg_version("qiskit-nature")
    pyscf_version = pkg_version("pyscf")

    entry_id = f"{molecule_name}_{basis}_JW_{ansatz_type}_v1__sha256_{input_hash[:16]}"
    entry = {
        "schema_version": "1.0.0",
        "entry_id": entry_id,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "generator": {"name": "qencode-db", "version": "0.1.0", "git_commit": "local"},
            "software": {
                "python": "local",
                "qiskit": qiskit_version,
                "qiskit_nature": qiskit_nature_version,
                "pyscf": pyscf_version,
            },
        },
        "problem": {
            "type": "molecule",
            "name": molecule_name,
            "geometry": {"units": units, "atoms": atoms},
            "charge": charge,
            "multiplicity": multiplicity,
        },
        "settings": settings,
        "artifacts": {
            "qubit_hamiltonian": qubit_hamiltonian,
            "circuits": {
                "hartree_fock_qasm": hartree_fock_qasm,
                "ansatz_template_qasm": "",
                # Keep as string for schema compatibility; empty string means “not stored”
                "ansatz_template_qpy_b64": ansatz_qpy_b64 if ansatz_qpy_b64 is not None else "",
                "ansatz_param_names": ansatz_param_names,
                "ansatz_recipe": ansatz_recipe,
                "notes": (
                    "HF stored as QASM2; ansatz stored as QPY (base64) when possible, "
                    "otherwise stored as ansatz_recipe only. For UCCSD, HF is composed at runtime."
                ),
            },
            "resources": {},
        },
        "validation": {},
        "provenance": {
            "input_fingerprint": {"sha256": input_hash},
            "notes": ["generated by batch_generate.py"],
        },
    }

    out_path = out_dir / f"{entry_id}.json"
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return out_path


def run_script(script_path: Path, args_list):
    cmd = [sys.executable, str(script_path)] + args_list
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Show helpful output before failing
        if proc.stdout.strip():
            print(proc.stdout)
        if proc.stderr.strip():
            print(proc.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="molecules_v1.json", help="Path to config JSON")
    parser.add_argument("--generate-only", action="store_true", help="Only generate entries (no validate/index)")
    parser.add_argument("--validate", action="store_true", help="Run validate_and_update_entry.py on generated entries")
    parser.add_argument("--index", action="store_true", help="Rebuild db/index.json after generation/validation")
    parser.add_argument("--exact-threshold", type=int, default=8, help="If num_qubits <= threshold, compute exact min eig")
    parser.add_argument("--vqe-optimizer", default="scipy", choices=["random", "coord", "scipy"], help="Optimizer for VQE validation")
    parser.add_argument("--vqe-steps", type=int, default=1200, help="Steps for random VQE (if used)")
    parser.add_argument("--vqe-sigma", type=float, default=0.10, help="Sigma for random VQE (if used)")
    parser.add_argument("--seed", type=int, default=123, help="Seed for VQE")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "db"
    out_dir.mkdir(parents=True, exist_ok=True)

    config_path = (root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    defaults = cfg.get("defaults", {})
    molecules = cfg.get("molecules", [])
    if not molecules:
        raise RuntimeError("No molecules found in config.")

    # Option B behavior: if not generate-only, we validate+index by default
    if args.generate_only:
        do_validate = False
        do_index = False
    else:
        do_validate = True if (args.validate or True) else False
        do_index = True if (args.index or True) else False

    generated = []

    for mol in molecules:
        problem = {
            "name": mol["name"],
            "units": mol.get("units", "angstrom"),
            "atoms": mol["atoms"],
            "charge": mol.get("charge", 0),
            "multiplicity": mol.get("multiplicity", 1),
        }

        variants = mol.get("variants", [{}])
        for v in variants:
            merged = deep_merge(defaults, v)

            settings = {
                "chemistry": {
                    "basis": merged.get("basis", "sto3g"),
                    "driver": merged.get("driver", "pyscf"),
                    "reference_method": "hf",
                },
                "reduction": {
                    "freeze_core": False,
                    "active_space": merged.get("active_space", {"enabled": False}),
                },
                "mapping": {
                    "type": merged.get("mapping", "jordan_wigner"),
                    "two_qubit_reduction": False,
                    "z2_symmetry_reduction": False,
                },
                "ansatz": {
                    "type": merged.get("ansatz", {}).get("type", "uccsd"),
                    "initial_state": "hartree_fock",
                    "reps": merged.get("ansatz", {}).get("reps", 1),
                },
                "estimation": {"shots": 0, "backend": "statevector_simulator"},
            }

            out_path = generate_entry(problem, settings, out_dir)
            print(f"✅ Generated: {out_path.name}")
            generated.append(out_path)

            # exact min eig for small systems
            if do_validate and args.exact_threshold is not None:
                try:
                    entry = json.loads(out_path.read_text(encoding="utf-8"))
                    nq = entry["artifacts"]["qubit_hamiltonian"]["num_qubits"]
                    if nq <= args.exact_threshold:
                        run_script(root / "scripts" / "exact_reference_energy.py", ["--file", str(out_path), "--write"])
                        print(f"✅ Exact min eig saved ({nq} qubits): {out_path.name}")
                except Exception as e:
                    print(f"⚠️ Exact min eig skipped for {out_path.name}: {e}")

            # validate (HF always; VQE only if ansatz QPY is present)
            if do_validate:
                entry_now = json.loads(out_path.read_text(encoding="utf-8"))
                ansatz_qpy = entry_now.get("artifacts", {}).get("circuits", {}).get("ansatz_template_qpy_b64", "")

                if ansatz_qpy:
                    # Full validation: HF + VQE
                    vqe_args = [
                        "--file", str(out_path),
                        "--vqe",
                        "--optimizer", args.vqe_optimizer,
                        "--seed", str(args.seed),
                        "--write-mode", "inplace",
                        "--steps", str(args.vqe_steps),
                        "--sigma", str(args.vqe_sigma),
                    ]
                    run_script(root / "scripts" / "validate_and_update_entry.py", vqe_args)
                    print(f"✅ Validated+updated (HF+VQE): {out_path.name}")
                else:
                    # HF-only validation (ansatz stored as recipe-only)
                    hf_args = [
                        "--file", str(out_path),
                        "--write-mode", "inplace",
                    ]
                    run_script(root / "scripts" / "validate_and_update_entry.py", hf_args)
                    print(f"⚠️ Validated+updated (HF only; no ansatz QPY): {out_path.name}")


    # rebuild index
    if do_index:
        run_script(root / "scripts" / "build_index.py", [])
        print("✅ Index rebuilt.")

    print(f"\nDone. Generated {len(generated)} entries.")


if __name__ == "__main__":
    main()

