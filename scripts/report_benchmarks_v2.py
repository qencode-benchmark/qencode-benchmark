#!/usr/bin/env python3
"""
Report v2 benchmarks and optionally write CSV.

Usage:
  python3 scripts/report_benchmarks_v2.py --db-dir releases/v2/db
  python3 scripts/report_benchmarks_v2.py --db-dir releases/v2/db --csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

Json = Dict[str, Any]


def _get_nested(d: Json, path: Sequence[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _as_float(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def _as_str(x: Any) -> Optional[str]:
    return x.strip() if isinstance(x, str) and x.strip() else None


def _iter_entry_files(db_dir: Path) -> List[Path]:
    ignore = {"index.json", "benchmarks.csv"}
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def _fmt(x: Any) -> str:
    if x is None:
        return "None"
    if isinstance(x, float):
        if math.isfinite(x):
            return f"{x:.6f}"
        return str(x)
    return str(x)


def _row(d: Json, filename: str) -> Dict[str, Any]:
    molecule = _as_str(_get_nested(d, ["problem", "name"])) or "UNKNOWN"
    basis = _as_str(_get_nested(d, ["problem", "basis"])) or "UNKNOWN"
    mapping = _as_str(_get_nested(d, ["encoding", "mapping"])) or "UNKNOWN"

    num_qubits = _as_float(_get_nested(d, ["artifacts", "qubit_hamiltonian", "num_qubits"]))
    pauli_terms = _get_nested(d, ["artifacts", "qubit_hamiltonian", "pauli_terms"], default=[])
    num_pauli_terms = float(len(pauli_terms)) if isinstance(pauli_terms, list) else None

    hf = _as_float(_get_nested(d, ["results", "reference", "hf_energy_hartree_like"]))
    exact = _as_float(_get_nested(d, ["results", "reference", "exact_qubit_ground_energy_hartree_like"]))

    vqe = _as_float(_get_nested(d, ["results", "vqe", "best_energy_hartree_like"]))
    vqe_method = _as_str(_get_nested(d, ["results", "vqe", "method"]))

    q = _get_nested(d, ["results", "quality"], default={})
    trusted = bool(_get_nested(q, ["trusted"], default=False))
    abs_gap = _as_float(_get_nested(q, ["abs_vqe_exact_gap"]))
    flags = _get_nested(q, ["flags"], default=[])
    if not isinstance(flags, list):
        flags = []

    return {
        "molecule": molecule,
        "basis": basis,
        "mapping": mapping,
        "num_qubits": num_qubits,
        "num_pauli_terms": num_pauli_terms,
        "hf_energy_hartree_like": hf,
        "vqe_best_energy_hartree_like": vqe,
        "vqe_method": vqe_method,
        "exact_qubit_ground_energy_hartree_like": exact,
        "abs_vqe_exact_gap": abs_gap,
        "trusted": trusted,
        "flags": ",".join([str(x) for x in flags]),
        "file": filename,
    }


def _print_table(rows: List[Dict[str, Any]]) -> None:
    headers = [
        "molecule",
        "basis",
        "mapping",
        "num_qubits",
        "num_pauli_terms",
        "hf",
        "vqe",
        "exact",
        "abs_gap",
        "trusted",
        "flags",
        "file",
    ]
    print(" | ".join(headers))
    print("-" * 160)
    for r in rows:
        print(
            " | ".join(
                [
                    _fmt(r["molecule"]),
                    _fmt(r["basis"]),
                    _fmt(r["mapping"]),
                    _fmt(r["num_qubits"]),
                    _fmt(r["num_pauli_terms"]),
                    _fmt(r["hf_energy_hartree_like"]),
                    _fmt(r["vqe_best_energy_hartree_like"]),
                    _fmt(r["exact_qubit_ground_energy_hartree_like"]),
                    _fmt(r["abs_vqe_exact_gap"]),
                    "Y" if r["trusted"] else "N",
                    r["flags"] or "",
                    r["file"],
                ]
            )
        )


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--csv", action="store_true", help="Write benchmarks.csv in the db dir")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    rows: List[Dict[str, Any]] = []
    for p in _iter_entry_files(db_dir):
        d = json.loads(p.read_text(encoding="utf-8"))
        rows.append(_row(d, p.name))

    _print_table(rows)

    if args.csv:
        out_csv = db_dir / "benchmarks.csv"
        _write_csv(out_csv, rows)
        print(f"\n✅ Wrote CSV: {out_csv}")


if __name__ == "__main__":
    main()

