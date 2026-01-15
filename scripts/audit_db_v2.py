#!/usr/bin/env python3
"""
Audit v2 entries.

Usage:
  python3 scripts/audit_db_v2.py --db-dir releases/v2/db --gap-threshold 0.01
"""
from __future__ import annotations

import argparse
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
    if isinstance(x, float) and math.isfinite(x):
        return f"{x:.6f}"
    return str(x)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--gap-threshold", type=float, default=1e-2)
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    print("molecule | basis | mapping | hf | vqe | exact | abs(vqe-exact) | trusted | flags | file")
    print("-" * 140)

    for p in _iter_entry_files(db_dir):
        d = json.loads(p.read_text(encoding="utf-8"))
        mol = _as_str(_get_nested(d, ["problem", "name"])) or "UNKNOWN"
        basis = _as_str(_get_nested(d, ["problem", "basis"])) or "UNKNOWN"
        mapping = _as_str(_get_nested(d, ["encoding", "mapping"])) or "UNKNOWN"

        hf = _as_float(_get_nested(d, ["results", "reference", "hf_energy_hartree_like"]))
        vqe = _as_float(_get_nested(d, ["results", "vqe", "best_energy_hartree_like"]))
        exact = _as_float(_get_nested(d, ["results", "reference", "exact_qubit_ground_energy_hartree_like"]))

        abs_gap = None
        if vqe is not None and exact is not None:
            abs_gap = abs(vqe - exact)

        q = _get_nested(d, ["results", "quality"], default={})
        trusted = bool(_get_nested(q, ["trusted"], default=False))
        flags = _get_nested(q, ["flags"], default=[])
        if not isinstance(flags, list):
            flags = []

        # Defensive: ensure gap flag exists if gap exceeds threshold
        if abs_gap is not None and abs_gap > float(args.gap_threshold):
            if not any(str(x).startswith("vqe_gap>") for x in flags):
                flags = list(flags) + [f"vqe_gap>{args.gap_threshold:g}"]

        print(
            " | ".join(
                [
                    _fmt(mol),
                    _fmt(basis),
                    _fmt(mapping),
                    _fmt(hf),
                    _fmt(vqe),
                    _fmt(exact),
                    _fmt(abs_gap),
                    "Y" if trusted else "N",
                    ",".join([str(x) for x in flags]),
                    p.name,
                ]
            )
        )

    print("\nDone.")


if __name__ == "__main__":
    main()

