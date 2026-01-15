#!/usr/bin/env python3
"""
Migrate v1 entries into v2 entries (non-destructive).

- Reads v1 JSON entries from --in-dir
- Writes v2 JSON entries to --out-dir
- Adds results.quality with:
  - trusted boolean
  - abs_vqe_exact_gap
  - flags list
- Computes a stable entry_hash_sha256 over v2 content excluding provenance timestamps/hash.

Usage:
  python3 scripts/migrate_v1_to_v2.py --in-dir releases/v1/db --out-dir releases/v2/db --gap-threshold 0.01
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

Json = Dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_nested(d: Json, path: Sequence[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def as_float(x: Any) -> Optional[float]:
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


def as_str(x: Any) -> Optional[str]:
    if isinstance(x, str) and x.strip():
        return x.strip()
    return None


def iter_entry_files(db_dir: Path) -> List[Path]:
    ignore = {"index.json", "benchmarks.csv"}
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def stable_hash_sha256(obj: Json) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_quality(
    hf: Optional[float],
    vqe: Optional[float],
    exact: Optional[float],
    has_legacy: bool,
    gap_threshold: float,
) -> Tuple[bool, Optional[float], List[str], Optional[str]]:
    flags: List[str] = []

    if hf is None:
        flags.append("missing_hf")
    if vqe is None:
        flags.append("missing_vqe")
    if exact is None:
        flags.append("missing_exact")
    if has_legacy:
        flags.append("has_legacy")

    abs_gap: Optional[float] = None
    if vqe is not None and exact is not None:
        abs_gap = abs(vqe - exact)
        if abs_gap > gap_threshold:
            flags.append(f"vqe_gap>{gap_threshold:g}")

    # Trusted definition (company-safe default):
    # - must have exact AND vqe
    # - must be within threshold
    trusted = (exact is not None) and (vqe is not None) and (abs_gap is not None) and (abs_gap <= gap_threshold)

    notes = None
    if trusted:
        notes = "Trusted: exact+vqe present and within gap threshold."
    elif "missing_vqe" in flags or "missing_exact" in flags:
        notes = "Incomplete: missing vqe and/or exact reference."
    elif abs_gap is not None and abs_gap > gap_threshold:
        notes = "Not trusted: vqe-exact gap exceeds threshold."

    return trusted, abs_gap, flags, notes


def migrate_one(v1: Json, filename: str, gap_threshold: float) -> Json:
    created_utc = as_str(v1.get("created_utc")) or utc_now_iso()
    entry_id = as_str(v1.get("entry_id")) or filename.replace(".json", "")

    # v1 fields (best-effort)
    molecule = as_str(get_nested(v1, ["problem", "name"])) or as_str(v1.get("name"))
    basis = as_str(get_nested(v1, ["problem", "basis"]))
    mapping = as_str(get_nested(v1, ["problem", "mapping"])) or as_str(get_nested(v1, ["settings", "mapping"]))

    active_enabled = get_nested(v1, ["settings", "reduction", "active_space", "enabled"], None)
    active_ne = get_nested(v1, ["settings", "reduction", "active_space", "num_electrons"], None)
    active_nso = get_nested(v1, ["settings", "reduction", "active_space", "num_spatial_orbitals"], None)

    num_qubits = get_nested(v1, ["artifacts", "qubit_hamiltonian", "num_qubits"])
    pauli_terms = get_nested(v1, ["artifacts", "qubit_hamiltonian", "pauli_terms"], [])

    hf_qpy = as_str(get_nested(v1, ["artifacts", "circuits", "hf_qpy_b64"]))
    ans_qpy = as_str(get_nested(v1, ["artifacts", "circuits", "ansatz_template_qpy_b64"]))
    ans_includes_hf = get_nested(v1, ["artifacts", "circuits", "ansatz_includes_hf"], None)

    hf = as_float(get_nested(v1, ["validation", "classical_reference", "hf_energy_hartree"]))
    if hf is None:
        hf = as_float(get_nested(v1, ["validation", "classical_reference", "hf_energy_hartree_like"]))

    exact = as_float(get_nested(v1, ["validation", "exact_qubit_ground_energy", "energy"]))
    vqe = as_float(get_nested(v1, ["validation", "vqe", "best_energy"]))
    vqe_method = as_str(get_nested(v1, ["validation", "vqe", "method"]))
    vqe_mode = as_str(get_nested(v1, ["validation", "vqe", "chosen_mode"]))
    vqe_utc = as_str(get_nested(v1, ["validation", "vqe", "computed_utc"]))

    legacy_block = get_nested(v1, ["validation", "legacy"], {})
    has_legacy = isinstance(legacy_block, dict) and len(legacy_block) > 0

    trusted, abs_gap, flags, notes = build_quality(hf, vqe, exact, has_legacy, gap_threshold)

    v2: Json = {
        "schema_version": "2.0.0",
        "entry_id": entry_id,
        "created_utc": created_utc,
        "problem": {
            "name": molecule or "UNKNOWN",
            "basis": basis or "UNKNOWN",
            "active_space": {
                "enabled": active_enabled,
                "num_electrons": active_ne,
                "num_spatial_orbitals": active_nso,
            },
        },
        "encoding": {
            "mapping": mapping or "UNKNOWN",
        },
        "artifacts": {
            "qubit_hamiltonian": {
                "num_qubits": num_qubits if num_qubits is not None else 0,
                "pauli_terms": pauli_terms if isinstance(pauli_terms, list) else [],
            },
            "circuits": {
                "hf_qpy_b64": hf_qpy,
                "ansatz_template_qpy_b64": ans_qpy,
                "ansatz_includes_hf": ans_includes_hf,
            },
        },
        "results": {
            "reference": {
                "hf_energy_hartree_like": hf,
                "exact_qubit_ground_energy_hartree_like": exact,
            },
            "vqe": {
                "best_energy_hartree_like": vqe,
                "method": vqe_method,
                "chosen_mode": vqe_mode,
                "computed_utc": vqe_utc,
            } if (vqe is not None or vqe_method or vqe_mode) else None,
            "quality": {
                "gap_threshold": float(gap_threshold),
                "trusted": bool(trusted),
                "abs_vqe_exact_gap": abs_gap,
                "flags": flags,
                "notes": notes,
            },
            "experimental": {
                "legacy_validation": legacy_block if has_legacy else None
            } if has_legacy else None,
        },
        "provenance": {
            "source_schema_version": as_str(v1.get("version")) or "v1",
            "migrated_utc": utc_now_iso(),
            "entry_hash_sha256": "PENDING",
            "migration": {
                "tool": "migrate_v1_to_v2.py",
                "from_file": filename,
                "gap_threshold": float(gap_threshold),
            },
            "environment": None,
        },
    }

    # Compute stable hash over content excluding provenance timestamps/hash itself
    hash_obj = json.loads(json.dumps(v2))  # deep-ish copy
    hash_obj["provenance"]["migrated_utc"] = None
    hash_obj["provenance"]["entry_hash_sha256"] = None
    entry_hash = stable_hash_sha256(hash_obj)
    v2["provenance"]["entry_hash_sha256"] = entry_hash

    return v2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True, help="Input v1 db dir, e.g. releases/v1/db")
    ap.add_argument("--out-dir", required=True, help="Output v2 db dir, e.g. releases/v2/db")
    ap.add_argument("--gap-threshold", type=float, default=1e-2, help="Trusted if |VQE-exact| <= threshold")
    ap.add_argument("--dry-run", action="store_true", help="Compute but do not write files")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    if not in_dir.exists():
        raise SystemExit(f"in-dir not found: {in_dir}")

    files = iter_entry_files(in_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    changed = 0
    for p in files:
        v1 = json.loads(p.read_text(encoding="utf-8"))
        v2 = migrate_one(v1, filename=p.name, gap_threshold=float(args.gap_threshold))
        out_path = out_dir / p.name

        if args.dry_run:
            print(f"DRY-RUN would write: {out_path.name} trusted={v2['results']['quality']['trusted']}")
            continue

        out_path.write_text(json.dumps(v2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += 1

    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(f"\nDone. mode={mode} migrated={changed} out_dir={out_dir}")


if __name__ == "__main__":
    main()

