#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List
from io import BytesIO
import base64

from qiskit import qpy


def run(cmd: List[str]) -> None:
    print("\n$ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def iter_entry_files(db_dir: Path) -> List[Path]:
    return sorted([p for p in db_dir.glob("*.json") if p.name != "index.json"])


def has_vqe_result(entry: dict) -> bool:
    v = entry.get("validation", {}).get("vqe_run", {})
    if isinstance(v, dict) and v.get("best_energy_hartree_like") is not None:
        return True
    if isinstance(v, dict) and v.get("status") == "skipped":
        return True
    return False


def should_run_exact(entry: dict, max_qubits: int = 6) -> bool:
    nq = entry.get("artifacts", {}).get("qubit_hamiltonian", {}).get("num_qubits", None)
    if nq is None:
        return False
    return int(nq) <= max_qubits


def estimate_num_params(entry: dict) -> int:
    circuits = entry.get("artifacts", {}).get("circuits", {})
    qpy_b64 = circuits.get("ansatz_template_qpy_b64")

    if qpy_b64:
        raw = base64.b64decode(qpy_b64.encode("ascii"))
        buf = BytesIO(raw)
        circ = qpy.load(buf)[0]
        return len(circ.parameters)

    return 999


def main():
    ap = argparse.ArgumentParser(description="qencode-db v1.1 release pipeline")
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--max-qubits", type=int, default=10)
    ap.add_argument("--max-params", type=int, default=40)
    ap.add_argument("--force-big", action="store_true")
    ap.add_argument("--maxiter", type=int, default=800)
    ap.add_argument("--multistart", type=int, default=20)
    ap.add_argument("--init-sigma", type=float, default=0.35)
    ap.add_argument("--init", choices=["zeros", "random", "small_random"], default="random")
    ap.add_argument("--hf-mode", choices=["strict", "zeros_on_mismatch", "skip_hf"], default="zeros_on_mismatch")
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    db_dir = Path(args.db_dir).expanduser().resolve()

    # Counters
    ran_vqe = 0
    already_had_vqe = 0
    skipped_too_big = 0

    # 1) Schema validation
    run([sys.executable, str(root / "scripts" / "validate_schema.py"), "--db-dir", str(db_dir)])

    # 2) Refresh HF
    run([sys.executable, str(root / "scripts" / "refresh_hf_energy.py"), "--db-dir", str(db_dir)])

    # 3) Process entries
    files = iter_entry_files(db_dir)

    for f in files:
        entry = json.loads(f.read_text(encoding="utf-8"))
        nq = entry.get("artifacts", {}).get("qubit_hamiltonian", {}).get("num_qubits", None)

        # ---- Exact diagonalization ----
        if should_run_exact(entry):
            print(f"🔎 Exact diagonalization: {f.name}")
            run([
                sys.executable,
                str(root / "scripts" / "exact_reference_energy.py"),
                "--file", str(f),
                "--write"
            ])
            entry = json.loads(f.read_text(encoding="utf-8"))

        # ---- Skip if VQE already exists ----
        if has_vqe_result(entry):
            already_had_vqe += 1
            continue

        n_params = estimate_num_params(entry)

        # ---- Skip heavy entries ----
        if not args.force_big:
            if nq is not None and int(nq) > args.max_qubits:
                entry.setdefault("validation", {})["vqe_run"] = {
                    "status": "skipped",
                    "reason": f"num_qubits={nq} > max_qubits={args.max_qubits}",
                }
                f.write_text(json.dumps(entry, indent=2), encoding="utf-8")
                skipped_too_big += 1
                continue

            if n_params > args.max_params:
                entry.setdefault("validation", {})["vqe_run"] = {
                    "status": "skipped",
                    "reason": f"num_params={n_params} > max_params={args.max_params}",
                }
                f.write_text(json.dumps(entry, indent=2), encoding="utf-8")
                skipped_too_big += 1
                continue

        # ---- Run VQE ----
        run([
            sys.executable, str(root / "scripts" / "run_vqe_from_entry.py"),
            "--file", str(f),
            "--seed", "123",
            "--maxiter", str(args.maxiter),
            "--multistart", str(args.multistart),
            "--init-sigma", str(args.init_sigma),
            "--init", str(args.init),
            "--hf-mode", str(args.hf_mode),
        ])
        ran_vqe += 1

    # 4) Rebuild index
    run([sys.executable, str(root / "scripts" / "build_index.py"), "--db-dir", str(db_dir)])

    # 5) Report
    report_cmd = [
        sys.executable,
        str(root / "scripts" / "report_benchmarks.py"),
        "--db-dir", str(db_dir),
        "--sort", "molecule",
    ]
    if args.csv:
        report_cmd.insert(-1, "--csv")

    run(report_cmd)

    print("\n✅ Pipeline complete")
    print(f"   VQE ran on:          {ran_vqe}")
    print(f"   Already had VQE:     {already_had_vqe}")
    print(f"   Skipped (too big):   {skipped_too_big}")


if __name__ == "__main__":
    main()

