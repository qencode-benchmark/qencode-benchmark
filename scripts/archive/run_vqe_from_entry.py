#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
from scipy.optimize import minimize

from qiskit.quantum_info import SparsePauliOp
from qiskit.quantum_info import Statevector

# Import locally from same folder without needing "scripts" as a package
from load_entry import load_entry, bind_all_parameters, expectation_energy


def run_vqe_statevector(
    H: SparsePauliOp,
    circ,
    seed: int,
    maxiter: int,
    multistart: int,
    init: str,
    init_sigma: float,
    method: str,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    params = list(circ.parameters)
    n = len(params)

    if n == 0:
        e = expectation_energy(H, circ)
        return {
            "best_energy": e,
            "best_theta": [],
            "nfev": 1,
            "nit": None,
            "success": True,
            "message": "No parameters; evaluated once.",
        }

    def obj(theta_vec: np.ndarray) -> float:
        bind = {p: float(v) for p, v in zip(params, theta_vec)}
        c = bind_all_parameters(circ, bind)
        return expectation_energy(H, c)

    best = {"energy": float("inf"), "theta": None, "res": None}

    for _ in range(int(multistart)):
        if init == "zeros":
            x0 = np.zeros(n, dtype=float)
        else:
            x0 = rng.normal(0.0, float(init_sigma), size=n)

        method_map = {
            "scipy_cobyla": "COBYLA",
            "cobyla": "COBYLA",
            "COBYLA": "COBYLA",
            "nelder_mead": "Nelder-Mead",
            "Nelder-Mead": "Nelder-Mead",
        }

        scipy_method = method_map.get(str(method), str(method))
        res = minimize(obj, x0, method=scipy_method, options={"maxiter": int(maxiter)})

        e = float(res.fun)
        if e < best["energy"]:
            best = {"energy": e, "theta": np.array(res.x, dtype=float), "res": res}

    res = best["res"]
    return {
        "best_energy": float(best["energy"]),
        "best_theta": [float(v) for v in (best["theta"] if best["theta"] is not None else [])],
        "nfev": int(getattr(res, "nfev", 0)) if res is not None else None,
        "nit": getattr(res, "nit", None),  # some SciPy methods don’t provide nit
        "success": bool(getattr(res, "success", True)) if res is not None else True,
        "message": str(getattr(res, "message", "")) if res is not None else "",
    }


def write_vqe_into_json(path: Path, data: Dict[str, Any], vqe: Dict[str, Any], chosen_mode: str, method: str):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data.setdefault("validation", {})
    data["validation"]["vqe"] = {
        "best_energy": float(vqe["best_energy"]),
        "units": "hartree_like",
        "method": method,
        "computed_utc": now,
        "params": vqe["best_theta"],
        "nfev": vqe.get("nfev", None),
        "nit": vqe.get("nit", None),
        "success": vqe.get("success", None),
        "message": vqe.get("message", ""),
        "chosen_mode": chosen_mode,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--maxiter", type=int, default=800)
    ap.add_argument("--multistart", type=int, default=20)
    ap.add_argument("--init", choices=["random", "zeros"], default="random")
    ap.add_argument("--init-sigma", type=float, default=0.35)
    ap.add_argument("--method", type=str, default="COBYLA")
    args = ap.parse_args()

    entry_path = Path(args.file)

    data, H, hf, ansatz, chosen, chosen_mode, ans_source, stats = load_entry(entry_path)

    # Extra sanity: if hf exists and chosen is composed, but composed theta=0 ~0 warn
    if "E_comp_0" in stats and abs(stats["E_comp_0"]) < 1e-9:
        print("⚠️  SANITY WARNING: (HF+ansatz)(theta=0) energy is ~0.")
        print("   This usually means the ansatz already contains HF initial state; ansatz-only is safer.")

    vqe = run_vqe_statevector(
        H=H,
        circ=chosen,
        seed=args.seed,
        maxiter=args.maxiter,
        multistart=args.multistart,
        init=args.init,
        init_sigma=args.init_sigma,
        method=args.method,
    )

    print(f"✅ VQE done: {entry_path.name}")
    print(f"   chosen_mode = {chosen_mode}")
    print(f"   best_energy = {vqe['best_energy']:.12f} (hartree-like)")
    print(f"   params      = {len(chosen.parameters)} | nfev={vqe.get('nfev')} nit={vqe.get('nit')} success={vqe.get('success')}")

    write_vqe_into_json(entry_path, data, vqe, chosen_mode, args.method.lower())
    print(f"✅ Saved into: {entry_path.resolve()}")


if __name__ == "__main__":
    main()

