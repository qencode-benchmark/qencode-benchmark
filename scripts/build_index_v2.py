#!/usr/bin/env python3
"""
Build index.json for v2 entries.

Usage:
  python3 scripts/build_index_v2.py --db-dir releases/v2/db
"""
from __future__ import annotations

import argparse
import json
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
    ignore = {"index.json", "benchmarks.csv"}
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def _extract_entry(d: Json, filename: str) -> Json:
    created_utc = _as_str(d.get("created_utc"))
    entry_id = _as_str(d.get("entry_id")) or filename.replace(".json", "")

    molecule = _as_str(_get_nested(d, ["problem", "name"]))
    basis = _as_str(_get_nested(d, ["problem", "basis"]))
    mapping = _as_str(_get_nested(d, ["encoding", "mapping"]))

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
        "trusted": trusted,
        "abs_vqe_exact_gap": abs_gap,
        "flags": flags,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    entries: List[Json] = []
    for p in _iter_entry_files(db_dir):
        d = json.loads(p.read_text(encoding="utf-8"))
        entries.append(_extract_entry(d, p.name))

    index = {
        "index_schema_version": "2.0.0",
        "generated_utc": _utc_now(),
        "count": len(entries),
        "entries": entries,
    }

    out_path = db_dir / "index.json"
    out_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Wrote index: {out_path} (entries={len(entries)})")


if __name__ == "__main__":
    main()

