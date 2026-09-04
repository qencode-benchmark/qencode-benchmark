#!/usr/bin/env python3
"""
Export a v2 "Trusted Benchmark Set" for company-safe consumption.

Writes:
  - <out-dir>/*.json (only trusted entries)
  - <out-dir>/trusted_index.json
  - <out-dir>/trusted_benchmarks.csv

Usage:
  python3 scripts/export_trusted_v2.py --db-dir releases/v2/db --out-dir releases/v2/trusted
  python3 scripts/export_trusted_v2.py --db-dir releases/v2/db --out-dir releases/v2/trusted --gap-threshold 0.01
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

Json = Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    ignore = {"index.json", "benchmarks.csv", "trusted_index.json", "trusted_benchmarks.csv"}
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def _safe_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _is_trusted_entry(d: Json, gap_threshold: float, require_gap_check: bool) -> tuple[bool, Optional[float]]:
    trusted = bool(_get_nested(d, ["results", "quality", "trusted"], default=False))

    vqe = _as_float(_get_nested(d, ["results", "vqe", "best_energy_hartree_like"]))
    exact = _as_float(_get_nested(d, ["results", "reference", "exact_qubit_ground_energy_hartree_like"]))

    abs_gap: Optional[float] = None
    if vqe is not None and exact is not None:
        abs_gap = abs(vqe - exact)

    if not trusted:
        return False, abs_gap

    if require_gap_check:
        # If we require gap checking, we must have both vqe and exact.
        if abs_gap is None:
            return False, abs_gap
        if abs_gap > float(gap_threshold):
            return False, abs_gap

    return True, abs_gap


def _summarize_entry(d: Json, filename: str, abs_gap: Optional[float]) -> Json:
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

    entry_id = _as_str(d.get("entry_id")) or filename.replace(".json", "")
    created_utc = _as_str(d.get("created_utc"))

    flags = _get_nested(d, ["results", "quality", "flags"], default=[])
    if not isinstance(flags, list):
        flags = []

    return {
        "file": filename,
        "entry_id": entry_id,
        "created_utc": created_utc,
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
        "flags": flags,
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="v2 database directory, e.g. releases/v2/db")
    ap.add_argument("--out-dir", required=True, help="output directory, e.g. releases/v2/trusted")
    ap.add_argument("--gap-threshold", type=float, default=1e-2)
    ap.add_argument(
        "--require-gap-check",
        action="store_true",
        help="If set, only keep entries where both VQE and exact exist and abs_gap <= threshold",
    )
    ap.add_argument("--clean-out-dir", action="store_true", help="Delete existing out-dir contents before writing")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    out_dir = Path(args.out_dir)

    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    if args.clean_out_dir and out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    kept_summaries: List[Json] = []

    for p in _iter_entry_files(db_dir):
        d = json.loads(p.read_text(encoding="utf-8"))
        ok, abs_gap = _is_trusted_entry(d, args.gap_threshold, args.require_gap_check)
        if not ok:
            continue

        shutil.copy2(p, out_dir / p.name)
        copied += 1
        kept_summaries.append(_summarize_entry(d, p.name, abs_gap))

    trusted_index = {
        "trusted_index_schema_version": "2.0.0",
        "generated_utc": _utc_now(),
        "source_db_dir": str(db_dir),
        "gap_threshold": float(args.gap_threshold),
        "require_gap_check": bool(args.require_gap_check),
        "count": copied,
        "entries": kept_summaries,
    }

    _safe_write_json(out_dir / "trusted_index.json", trusted_index)

    # Flatten for CSV
    csv_rows: List[Dict[str, Any]] = []
    for e in kept_summaries:
        row = dict(e)
        # make flags CSV-friendly
        row["flags"] = ",".join([str(x) for x in (row.get("flags") or [])])
        csv_rows.append(row)
    _write_csv(out_dir / "trusted_benchmarks.csv", csv_rows)

    print(f"✅ Exported trusted set: {copied} entries")
    print(f"   out_dir: {out_dir}")
    print(f"   index:   {out_dir / 'trusted_index.json'}")
    print(f"   csv:     {out_dir / 'trusted_benchmarks.csv'}")


if __name__ == "__main__":
    main()

