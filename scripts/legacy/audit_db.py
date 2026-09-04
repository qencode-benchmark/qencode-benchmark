#!/usr/bin/env python3
"""
Audit qencode-db entries for data hygiene and consistency.

What it checks (high level):
- Missing canonical fields (HF, VQE, exact reference).
- Presence of legacy fields under validation.legacy.*.
- Suspicious patterns:
  - HF == VQE (often indicates contaminated / placeholder values)
  - VQE far from exact (gap threshold)
- Prints a compact table and returns non-zero exit status if "fail" conditions are met.

Usage:
  python3 scripts/audit_db.py --db-dir releases/v1/db
  python3 scripts/audit_db.py --db-dir releases/v1/db --out-csv audit.csv
  python3 scripts/audit_db.py --db-dir releases/v1/db --fail-on missing_vqe --fail-on vqe_gap
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

Json = Dict[str, Any]


def _get_nested(d: Json, path: Sequence[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
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
    if isinstance(x, str) and x.strip():
        return x.strip()
    return None


def _iter_entry_files(db_dir: Path) -> List[Path]:
    return sorted([p for p in db_dir.rglob("*.json") if p.name != "index.json"])


def _extract_hf(d: Json) -> Optional[float]:
    v = _as_float(_get_nested(d, ["validation", "classical_reference", "hf_energy_hartree"]))
    if v is not None:
        return v
    return _as_float(_get_nested(d, ["validation", "classical_reference", "hf_energy_hartree_like"]))


def _extract_vqe(d: Json) -> Optional[float]:
    return _as_float(_get_nested(d, ["validation", "vqe", "best_energy"]))


def _extract_exact(d: Json) -> Optional[float]:
    return _as_float(_get_nested(d, ["validation", "exact_qubit_ground_energy", "energy"]))


def _extract_mapping(d: Json) -> Optional[str]:
    return _as_str(_get_nested(d, ["problem", "mapping"])) or _as_str(_get_nested(d, ["settings", "mapping", "type"]))


def _extract_basis(d: Json) -> Optional[str]:
    return _as_str(_get_nested(d, ["problem", "basis"])) or _as_str(_get_nested(d, ["settings", "chemistry", "basis"]))


def _extract_ansatz_type(d: Json) -> Optional[str]:
    return _as_str(_get_nested(d, ["settings", "ansatz", "type"])) or _as_str(_get_nested(d, ["settings", "ansatz_type"]))


def _extract_ansatz_reps(d: Json) -> Optional[int]:
    reps = _get_nested(d, ["settings", "ansatz", "reps"])
    if isinstance(reps, bool):
        return None
    if isinstance(reps, int):
        return reps
    if isinstance(reps, float) and reps.is_integer():
        return int(reps)
    if isinstance(reps, str) and reps.strip().isdigit():
        return int(reps.strip())
    reps2 = _get_nested(d, ["settings", "ansatz_reps"])
    if isinstance(reps2, int):
        return reps2
    if isinstance(reps2, float) and reps2.is_integer():
        return int(reps2)
    return None


def _has_legacy(d: Json) -> bool:
    legacy = _get_nested(d, ["validation", "legacy"], default={})
    return isinstance(legacy, dict) and len(legacy) > 0


def _fmt(x: Any) -> str:
    if x is None:
        return "None"
    if isinstance(x, float):
        if math.isfinite(x):
            return f"{x:.6f}"
        return str(x)
    return str(x)


@dataclass
class AuditRow:
    file: str
    molecule: Optional[str]
    basis: Optional[str]
    mapping: Optional[str]
    ansatz_type: Optional[str]
    ansatz_reps: Optional[int]
    hf_energy: Optional[float]
    vqe_energy: Optional[float]
    exact_energy: Optional[float]
    has_legacy: bool
    hf_eq_vqe: bool
    vqe_gap: Optional[float]
    abs_vqe_gap: Optional[float]
    flags: str


def _compute_row(p: Path, d: Json, gap_threshold: float, eq_eps: float) -> AuditRow:
    molecule = _as_str(_get_nested(d, ["problem", "name"]))
    basis = _extract_basis(d)
    mapping = _extract_mapping(d)
    ansatz_type = _extract_ansatz_type(d)
    ansatz_reps = _extract_ansatz_reps(d)

    hf = _extract_hf(d)
    vqe = _extract_vqe(d)
    exact = _extract_exact(d)
    has_legacy = _has_legacy(d)

    hf_eq_vqe = False
    if hf is not None and vqe is not None and math.isfinite(hf) and math.isfinite(vqe):
        hf_eq_vqe = abs(hf - vqe) <= eq_eps

    vqe_gap = None
    abs_gap = None
    if vqe is not None and exact is not None and math.isfinite(vqe) and math.isfinite(exact):
        vqe_gap = vqe - exact
        abs_gap = abs(vqe_gap)

    flag_parts: List[str] = []
    if hf is None:
        flag_parts.append("missing_hf")
    if vqe is None:
        flag_parts.append("missing_vqe")
    if exact is None:
        flag_parts.append("missing_exact")
    if has_legacy:
        flag_parts.append("has_legacy")
    if hf_eq_vqe and vqe is not None:
        flag_parts.append("hf_eq_vqe")
    if abs_gap is not None and abs_gap > gap_threshold:
        flag_parts.append(f"vqe_gap>{gap_threshold:g}")

    return AuditRow(
        file=p.name,
        molecule=molecule,
        basis=basis,
        mapping=mapping,
        ansatz_type=ansatz_type,
        ansatz_reps=ansatz_reps,
        hf_energy=hf,
        vqe_energy=vqe,
        exact_energy=exact,
        has_legacy=has_legacy,
        hf_eq_vqe=hf_eq_vqe,
        vqe_gap=vqe_gap,
        abs_vqe_gap=abs_gap,
        flags=",".join(flag_parts) if flag_parts else "",
    )


def _print_table(rows: List[AuditRow]) -> None:
    headers = [
        "molecule",
        "basis",
        "mapping",
        "ansatz_type",
        "reps",
        "hf",
        "vqe",
        "exact",
        "abs(vqe-exact)",
        "legacy?",
        "flags",
        "file",
    ]
    print(" | ".join(headers))
    print("-" * 160)
    for r in rows:
        print(
            " | ".join(
                [
                    _fmt(r.molecule),
                    _fmt(r.basis),
                    _fmt(r.mapping),
                    _fmt(r.ansatz_type),
                    _fmt(r.ansatz_reps),
                    _fmt(r.hf_energy),
                    _fmt(r.vqe_energy),
                    _fmt(r.exact_energy),
                    _fmt(r.abs_vqe_gap),
                    "Y" if r.has_legacy else "N",
                    r.flags or "",
                    r.file,
                ]
            )
        )


def _write_csv(path: Path, rows: List[AuditRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        if rows:
            w.writeheader()
            for r in rows:
                w.writerow(asdict(r))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="DB directory like releases/v1/db")
    ap.add_argument("--gap-threshold", type=float, default=1e-2, help="Flag if |VQE-exact| > threshold")
    ap.add_argument("--eq-eps", type=float, default=1e-9, help="Treat HF==VQE if abs diff <= eps")
    ap.add_argument(
        "--fail-on",
        action="append",
        default=[],
        help="Fail conditions: missing_hf, missing_vqe, missing_exact, has_legacy, hf_eq_vqe, vqe_gap",
    )
    ap.add_argument("--out-csv", default=None, help="Write a CSV audit report")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    files = _iter_entry_files(db_dir)
    rows: List[AuditRow] = []
    bad = 0

    fail_on = set(args.fail_on or [])
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        row = _compute_row(p, d, gap_threshold=float(args.gap_threshold), eq_eps=float(args.eq_eps))
        rows.append(row)

        # Evaluate fail rules
        flags = set([x for x in row.flags.split(",") if x])
        if "missing_hf" in flags and "missing_hf" in fail_on:
            bad += 1
        if "missing_vqe" in flags and "missing_vqe" in fail_on:
            bad += 1
        if "missing_exact" in flags and "missing_exact" in fail_on:
            bad += 1
        if row.has_legacy and "has_legacy" in fail_on:
            bad += 1
        if row.hf_eq_vqe and "hf_eq_vqe" in fail_on:
            bad += 1
        if row.abs_vqe_gap is not None and row.abs_vqe_gap > float(args.gap_threshold) and "vqe_gap" in fail_on:
            bad += 1

    _print_table(rows)

    if args.out_csv:
        _write_csv(Path(args.out_csv), rows)
        print(f"✅ Wrote audit CSV: {args.out_csv}")

    print(f"\nDone. entries={len(rows)} fail_hits={bad}")
    if bad > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
