import json
import base64
import io
import argparse
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

from qiskit import QuantumCircuit
from qiskit import qpy
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector


def load_entry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_entry(path: Path, entry: dict) -> None:
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")


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


def simple_vqe_search(H: SparsePauliOp, hf: QuantumCircuit, ansatz: QuantumCircuit,
                      steps: int = 200, sigma: float = 0.2, seed: int = 123) -> dict:
    """
    A robust, dependency-light VQE-like search:
    - starts at theta=0
    - proposes random Gaussian perturbations
    - keeps best energy
    """
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

    rng = np.random.default_rng(seed)
    improvements = []

    for step in range(steps):
        candidate = best_theta + rng.normal(0.0, sigma, size=len(params))
        e = expectation_value(H, build_combined(candidate))
        if e < best_energy:
            best_energy = e
            best_theta = candidate
            improvements.append({"step": step, "energy": best_energy})

    return {
        "best_energy": float(best_energy),
        "best_theta": [float(x) for x in best_theta],
        "num_params": len(params),
        "steps": steps,
        "sigma": sigma,
        "seed": seed,
        "improvements": improvements[:10],  # store first few improvements only (keep JSON small)
    }

def coordinate_descent_vqe(H, hf, ansatz, rounds=25, step=0.2, decay=0.85):
    """
    Simple coordinate descent:
    - Start at theta=0
    - For each parameter, try +/- step, keep the best
    - Decay step each round
    Great for small parameter counts like UCCSD(H2).
    """
    params = list(ansatz.parameters)
    if len(params) == 0:
        raise RuntimeError("Ansatz has no parameters; cannot run VQE.")

    def energy(theta_vals):
        bind = {p: v for p, v in zip(params, theta_vals)}
        combined = QuantumCircuit(hf.num_qubits)
        combined.compose(hf, inplace=True)
        combined.compose(ansatz.assign_parameters(bind), inplace=True)
        return expectation_value(H, combined)

    theta = np.zeros(len(params))
    best = energy(theta)

    improvements = []
    cur_step = float(step)

    for r in range(rounds):
        improved = False
        for i in range(len(theta)):
            for delta in (+cur_step, -cur_step):
                trial = theta.copy()
                trial[i] += delta
                e = energy(trial)
                if e < best:
                    best = e
                    theta = trial
                    improved = True
        improvements.append({"round": r, "energy": best, "step": cur_step})
        cur_step *= decay
        if not improved and cur_step < 1e-3:
            break

    return {
        "best_energy": float(best),
        "best_theta": [float(x) for x in theta],
        "num_params": len(params),
        "rounds": rounds,
        "initial_step": step,
        "decay": decay,
        "trace": improvements[:10],
    }

def multistart_coordinate_descent_vqe(H, hf, ansatz, starts=30, init_sigma=0.4, rounds=40, step=0.25, decay=0.85, seed=123):
    params = list(ansatz.parameters)
    if len(params) == 0:
        raise RuntimeError("Ansatz has no parameters; cannot run VQE.")

    def energy(theta_vals):
        bind = {p: v for p, v in zip(params, theta_vals)}
        combined = QuantumCircuit(hf.num_qubits)
        combined.compose(hf, inplace=True)
        combined.compose(ansatz.assign_parameters(bind), inplace=True)
        return expectation_value(H, combined)

    rng = np.random.default_rng(seed)

    # Evaluate multiple random starts + zero start
    candidates = [np.zeros(len(params))]
    for _ in range(starts):
        candidates.append(rng.normal(0.0, init_sigma, size=len(params)))

    best_theta = None
    best_energy = None

    # pick best start
    for th in candidates:
        e = energy(th)
        if best_energy is None or e < best_energy:
            best_energy = e
            best_theta = th

    # Now coordinate-descent refine from best start
    theta = best_theta.copy()
    best = best_energy
    cur_step = float(step)
    trace = []

    for r in range(rounds):
        improved = False
        for i in range(len(theta)):
            for delta in (+cur_step, -cur_step):
                trial = theta.copy()
                trial[i] += delta
                e = energy(trial)
                if e < best:
                    best = e
                    theta = trial
                    improved = True
        trace.append({"round": r, "energy": float(best), "step": cur_step})
        cur_step *= decay
        if not improved and cur_step < 1e-3:
            break

    return {
        "best_energy": float(best),
        "best_theta": [float(x) for x in theta],
        "num_params": len(params),
        "starts": starts,
        "init_sigma": init_sigma,
        "rounds": rounds,
        "initial_step": step,
        "decay": decay,
        "trace": trace[:10],
        "seed": seed,
    }


def ensure_validation_block(entry: dict) -> dict:
    if "validation" not in entry or not isinstance(entry["validation"], dict):
        entry["validation"] = {}
    return entry["validation"]

def scipy_vqe(H, hf, ansatz, seed=123, maxiter=300, method="COBYLA"):
    from scipy.optimize import minimize

    params = list(ansatz.parameters)
    if len(params) == 0:
        raise RuntimeError("Ansatz has no parameters; cannot run VQE.")

    def energy(x):
        bind = {p: float(v) for p, v in zip(params, x)}
        combined = QuantumCircuit(hf.num_qubits)
        combined.compose(hf, inplace=True)
        combined.compose(ansatz.assign_parameters(bind), inplace=True)
        return expectation_value(H, combined)

    rng = np.random.default_rng(seed)
    x0 = rng.normal(0.0, 0.3, size=len(params))  # random start (important!)

    res = minimize(energy, x0, method=method, options={"maxiter": maxiter})

    return {
        "best_energy": float(res.fun),
        "best_theta": [float(v) for v in res.x],
        "num_params": len(params),
        "method": method,
        "maxiter": maxiter,
        "seed": seed,
        "status": int(res.status),
        "message": str(res.message),
        "nfev": int(getattr(res, "nfev", -1)),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate an entry and write results back into the JSON.")
    parser.add_argument("--file", required=True, help="Path to entry JSON in db/")
    parser.add_argument("--vqe", action="store_true", help="Also run a simple VQE search and store result")
    parser.add_argument(
    "--optimizer",
    choices=["random", "coord", "scipy"],
    default="random",
    help="VQE optimizer: random search or coordinate descent"
    )
    parser.add_argument("--steps", type=int, default=200, help="VQE steps (only if --vqe)")
    parser.add_argument("--sigma", type=float, default=0.2, help="VQE proposal stddev (only if --vqe)")
    parser.add_argument("--seed", type=int, default=123, help="Random seed (only if --vqe)")
    parser.add_argument("--write-mode", choices=["inplace", "copy"], default="inplace",
                        help="inplace overwrites the file; copy writes a new *_validated.json file")
    args = parser.parse_args()

    entry_path = Path(args.file).resolve()
    if not entry_path.exists():
        raise FileNotFoundError(f"File not found: {entry_path}")

    entry = load_entry(entry_path)
    mol = entry["problem"]["name"]

    qubit_ham = entry["artifacts"]["qubit_hamiltonian"]
    H = build_hamiltonian(qubit_ham)

    circuits = entry["artifacts"]["circuits"]
    hf = load_hf_circuit(circuits["hartree_fock_qasm"])

    hf_energy = expectation_value(H, hf)
    print(f"✅ {mol}: HF energy (statevector) = {hf_energy:.12f} Hartree")

    # Update validation section
    validation = ensure_validation_block(entry)
    validation["hf_energy_statevector"] = {
        "energy": hf_energy,
        "units": "hartree",
        "computed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    if args.vqe:
        ansatz_b64 = circuits.get("ansatz_template_qpy_b64", "")
        if not ansatz_b64:
            raise RuntimeError("Entry does not contain ansatz_template_qpy_b64; cannot run VQE.")

        ansatz = load_ansatz_qpy_b64(ansatz_b64)
        if args.optimizer == "random":
            vqe_res = simple_vqe_search(
                H, hf, ansatz,
                steps=args.steps,
                sigma=args.sigma,
                seed=args.seed,
            )
            vqe_payload = {
                "method": "random_search",
                "best_energy": vqe_res["best_energy"],
                "units": "hartree",
                "improvement_vs_hf": float(hf_energy - vqe_res["best_energy"]),
                "settings": {
                    "steps": vqe_res["steps"],
                    "sigma": vqe_res["sigma"],
                    "seed": vqe_res["seed"],
                    "num_params": vqe_res["num_params"],
                },
                "example_trace": vqe_res["improvements"],
            }

        elif args.optimizer == "coord":
            vqe_res = multistart_coordinate_descent_vqe(
                H, hf, ansatz,
                starts=40,
                init_sigma=0.6,
                rounds=60,
                step=0.3,
                decay=0.85,
                seed=args.seed,
            )
            vqe_payload = {
                "method": "multistart_coordinate_descent",
                "best_energy": vqe_res["best_energy"],
                "units": "hartree",
                "improvement_vs_hf": float(hf_energy - vqe_res["best_energy"]),
                "settings": {
                    "starts": vqe_res["starts"],
                    "init_sigma": vqe_res["init_sigma"],
                    "rounds": vqe_res["rounds"],
                    "initial_step": vqe_res["initial_step"],
                    "decay": vqe_res["decay"],
                    "seed": vqe_res["seed"],
                    "num_params": vqe_res["num_params"],
                },
                "example_trace": vqe_res["trace"],
                "best_theta": vqe_res["best_theta"],
            }

        elif args.optimizer == "scipy":
            vqe_res = scipy_vqe(
                H, hf, ansatz,
                seed=args.seed,
                maxiter=400,
                method="COBYLA",
            )
            vqe_payload = {
                "method": "scipy_cobyla",
                "best_energy": vqe_res["best_energy"],
                "units": "hartree",
                "improvement_vs_hf": float(hf_energy - vqe_res["best_energy"]),
                "settings": {
                    "seed": vqe_res["seed"],
                    "maxiter": vqe_res["maxiter"],
                    "num_params": vqe_res["num_params"],
                    "status": vqe_res["status"],
                    "message": vqe_res["message"],
                    "nfev": vqe_res["nfev"],
                },
                "best_theta": vqe_res["best_theta"],
                "example_trace": [],
            }

        print(f"🏁 {mol}: VQE-best energy = {vqe_payload['best_energy']:.12f} Hartree")
        print(f"📌 {mol}: improvement vs HF = {vqe_payload['improvement_vs_hf']:.12f} Hartree")

        validation["vqe"] = {
            **vqe_payload,
            "computed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }



    # Decide output path
    if args.write_mode == "inplace":
        out_path = entry_path
    else:
        out_path = entry_path.with_name(entry_path.stem + "_validated.json")

    save_entry(out_path, entry)
    print(f"✅ Saved validation into: {out_path}")


if __name__ == "__main__":
    main()

