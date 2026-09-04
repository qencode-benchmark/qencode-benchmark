#!/usr/bin/env python3
"""
Builds an index.json for the v1 DB directory.

Usage:
  python3 scripts/build_index.py --db-dir releases/v1/db
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

Json = Dict[str, Any]


def safe_get(d: Json, path: Iterable[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_entry_files(db_dir: Path) -> List[Path]:
    return sorted([p for p in db_dir.rglob("*.json") if p.name != "index.json"])


def extract_vqe_best_energy(data: Json) -> Optional[float]:
    # Canonical
    v = as_float(safe_get(data, ["validation", "vqe", "best_energy"]))
    if v is not None:
        return v

    # Older-but-ok
    v = as_float(safe_get(data, ["validation", "vqe_result", "best_energy"]))
    if v is not None:
        return v

    # Legacy (after migration it lives under validation.legacy.*)
    v = as_float(safe_get(data, ["validation", "legacy", "vqe_run", "best_energy_hartree_like"]))
    if v is not None:
        return v

    return None


def extract_vqe_method(data: Json) -> Optional[str]:
    v = safe_get(data, ["validation", "vqe", "method"])
    if isinstance(v, str) and v.strip():
        return v.strip()

    v = safe_get(data, ["validation", "vqe_result", "optimizer"])
    if isinstance(v, str) and v.strip():
        return v.strip()

    v = safe_get(data, ["validation", "legacy", "vqe_run", "optimizer"])
    if isinstance(v, str) and v.strip():
        return v.strip()

    return None

def extract_hf_energy(data: Json) -> Optional[float]:
    # Canonical in your entries
    v = as_float(safe_get(data, ["validation", "classical_reference", "hf_energy_hartree"]))
    if v is not None:
        return v

    v = as_float(safe_get(data, ["validation", "classical_reference", "hf_energy_hartree_like"]))
    if v is not None:
        return v

    # Extra fallbacks (harmless)
    v = as_float(safe_get(data, ["validation", "hf_energy_hartree"]))
    if v is not None:
        return v

    v = as_float(safe_get(data, ["validation", "hartree_fock_energy_hartree"]))
    if v is not None:
        return v

    return None



def build_index_entry(path: Path, data: Json) -> Json:
    pauli_terms = safe_get(data, ["artifacts", "qubit_hamiltonian", "pauli_terms"])
    num_qubits = safe_get(data, ["artifacts", "qubit_hamiltonian", "num_qubits"])
    if not isinstance(num_qubits, (int, float)):
        num_qubits = safe_get(data, ["artifacts", "qubit_hamiltonian", "num_qubits_int"])

    molecule = safe_get(data, ["problem", "name"])
    basis = safe_get(data, ["problem", "basis"])
    mapping = safe_get(data, ["problem", "mapping"])

    ansatz_type = safe_get(data, ["settings", "ansatz", "type"])
    ansatz_reps = safe_get(data, ["settings", "ansatz", "reps"])
    if ansatz_reps is None:
        ansatz_reps = safe_get(data, ["settings", "ansatz_reps"])

    active_space_enabled = safe_get(data, ["settings", "reduction", "active_space", "enabled"])
    active_space_ne = safe_get(data, ["settings", "reduction", "active_space", "num_electrons"])
    active_space_nso = safe_get(data, ["settings", "reduction", "active_space", "num_spatial_orbitals"])

    exact_min = as_float(safe_get(data, ["validation", "exact_qubit_ground_energy", "energy"]))

    ansatz_qpy = safe_get(data, ["artifacts", "circuits", "ansatz_template_qpy_b64"])
    ansatz_storage = "qpy" if isinstance(ansatz_qpy, str) and ansatz_qpy.strip() else "recipe"

    return {
        "file": path.name,
        "entry_id": data.get("entry_id"),
        "created_utc": data.get("created_utc"),

        "molecule": molecule,
        "basis": basis,
        "mapping": mapping,

        "ansatz_type": ansatz_type,
        "ansatz_reps": ansatz_reps,
        "ansatz_storage": ansatz_storage,

        "active_space_enabled": active_space_enabled,
        "active_space_num_electrons": active_space_ne,
        "active_space_num_spatial_orbitals": active_space_nso,

        "num_qubits": num_qubits,
        "num_pauli_terms": len(pauli_terms) if isinstance(pauli_terms, list) else None,

        "hf_energy_hartree": extract_hf_energy(data),
        "vqe_best_energy_hartree": extract_vqe_best_energy(data),
        "vqe_method": extract_vqe_method(data),

        "exact_qubit_min_eig_hartree_like": exact_min,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True, help="DB dir like releases/v1/db")
    parser.add_argument("--out", default=None, help="Output path (default: <db-dir>/index.json)")
    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    out_path = Path(args.out) if args.out else (db_dir / "index.json")

    entries: List[Json] = []
    for p in iter_entry_files(db_dir):
        data = json.loads(p.read_text(encoding="utf-8"))
        entries.append(build_index_entry(p, data))

    index = {
        "index_schema_version": "1.0.0",
        "generated_utc": utc_now_iso(),
        "count": len(entries),
        "entries": entries,
    }

    out_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Wrote index: {out_path} (entries={len(entries)})")


if __name__ == "__main__":
    main()

