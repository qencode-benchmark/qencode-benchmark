#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    # occasionally numbers can appear as strings
    try:
        return float(x)
    except Exception:
        return None


def _get_nested(d: Dict[str, Any], path: List[str]) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _get_mapping_type(d: Dict[str, Any], filename: str) -> str:
    m = _get_nested(d, ["settings", "mapping"])
    if isinstance(m, dict):
        t = m.get("type")
        if isinstance(t, str) and t.strip():
            return t

    # fallback: infer from filename tokens
    name = filename.upper()
    if "_JW_" in name or "_JW" in name:
        return "jordan_wigner"
    if "_BK_" in name or "_BK" in name:
        return "bravyi_kitaev"
    return "UNKNOWN"


def _get_basis(d: Dict[str, Any], filename: str) -> str:
    b = _get_nested(d, ["settings", "chemistry", "basis"])
    if isinstance(b, str) and b.strip():
        return b

    # fallback: parse from filename like H2_sto3g_...
    parts = filename.split("_")
    for p in parts:
        p2 = p.lower()
        if p2 in {"sto3g", "6-31g", "6-31g*", "ccpvdz", "cc-pvdz"}:
            return p2
    return "UNKNOWN"


def _get_molecule(d: Dict[str, Any], filename: str) -> str:
    n = _get_nested(d, ["problem", "name"])
    if isinstance(n, str) and n.strip():
        return n
    # fallback: filename prefix before first underscore
    return filename.split("_", 1)[0] if "_" in filename else "UNKNOWN"


def _get_ansatz(d: Dict[str, Any], filename: str) -> Tuple[str, Optional[int], str]:
    """
    Returns (ansatz_type, ansatz_reps, storage)
    """
    storage = "UNKNOWN"
    # you store qpy base64, so treat as qpy by default if present
    circuits = _get_nested(d, ["artifacts", "circuits"])
    if isinstance(circuits, dict):
        if isinstance(circuits.get("ansatz_template_qpy_b64"), str):
            storage = "qpy"
        elif isinstance(circuits.get("ansatz_template_qpy_hex"), str):
            storage = "qpy"
        elif isinstance(circuits.get("ansatz_template_qasm"), str):
            storage = "qasm"

    a = _get_nested(d, ["settings", "ansatz"])
    if isinstance(a, dict):
        a_type = a.get("type")
        reps = a.get("reps")
        if isinstance(a_type, str) and a_type.strip():
            return a_type, int(reps) if isinstance(reps, int) else (int(reps) if isinstance(reps, str) and reps.isdigit() else None), storage

    # fallback from filename
    low = filename.lower()
    if "uccsd" in low:
        return "uccsd", 1, storage
    if "hardware_efficient" in low:
        return "hardware_efficient", None, storage
    return "UNKNOWN", None, storage


def _get_active_space_enabled(d: Dict[str, Any]) -> Optional[bool]:
    # your DB uses settings.chemistry.active_space_enabled (True/False/None)
    v = _get_nested(d, ["settings", "chemistry", "active_space_enabled"])
    if isinstance(v, bool) or v is None:
        return v
    return None


def _get_num_qubits_and_terms(d: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    qh = _get_nested(d, ["artifacts", "qubit_hamiltonian"])
    if not isinstance(qh, dict):
        return None, None
    nq = qh.get("num_qubits")
    terms = qh.get("pauli_terms")
    n_terms = len(terms) if isinstance(terms, list) else None
    return (int(nq) if isinstance(nq, int) else _as_float(nq) and int(_as_float(nq))), n_terms


def _get_hf_energy(d: Dict[str, Any]) -> Optional[float]:
    # Prefer the canonical field used by current entries
    v = _as_float(_get_nested(d, ["validation", "classical_reference", "hf_energy_hartree"]))
    if v is not None:
        return v

    # Older / alternate naming used in some entries/scripts
    v = _as_float(_get_nested(d, ["validation", "classical_reference", "hf_energy_hartree_like"]))
    if v is not None:
        return v

    # Extra fallbacks (harmless)
    v = _as_float(_get_nested(d, ["validation", "hf_energy_hartree"]))
    if v is not None:
        return v

    v = _as_float(_get_nested(d, ["validation", "hartree_fock_energy_hartree"]))
    if v is not None:
        return v

    return None


def _get_exact_energy(d: Dict[str, Any]) -> Optional[float]:
    e = _get_nested(d, ["validation", "exact_qubit_ground_energy", "energy"])
    return _as_float(e)


def _get_vqe_best_energy(d: Dict[str, Any]) -> Optional[float]:
    """
    Prefer validation.vqe.best_energy (your corrected run),
    fall back to validation.vqe_result.best_energy,
    then (last resort) validation.vqe_run.best_energy_hartree_like.
    """
    vqe = _get_nested(d, ["validation", "vqe"])
    if isinstance(vqe, dict):
        e = vqe.get("best_energy")
        ef = _as_float(e)
        if ef is not None:
            return ef

    vqe_res = _get_nested(d, ["validation", "vqe_result"])
    if isinstance(vqe_res, dict):
        e = vqe_res.get("best_energy")
        ef = _as_float(e)
        if ef is not None:
            return ef

    vqe_run = _get_nested(d, ["validation", "vqe_run"])
    if isinstance(vqe_run, dict):
        e = vqe_run.get("best_energy_hartree_like")
        ef = _as_float(e)
        if ef is not None:
            # NOTE: if someone accidentally stored a near-zero bogus run, this will still show it.
            # Your DB cleanup removed vqe_run for BeH2, so vqe will be used.
            return ef

    return None


def _get_vqe_method(d: Dict[str, Any]) -> Optional[str]:
    vqe = _get_nested(d, ["validation", "vqe"])
    if isinstance(vqe, dict):
        m = vqe.get("method")
        if isinstance(m, str) and m.strip():
            return m

    vqe_res = _get_nested(d, ["validation", "vqe_result"])
    if isinstance(vqe_res, dict):
        m = vqe_res.get("method")
        if isinstance(m, str) and m.strip():
            return m

    vqe_run = _get_nested(d, ["validation", "vqe_run"])
    if isinstance(vqe_run, dict):
        opt = vqe_run.get("optimizer")
        if isinstance(opt, str) and opt.strip():
            return opt
        m = vqe_run.get("method")
        if isinstance(m, str) and m.strip():
            return m

    return None


def _fmt(x: Any, ndigits: int = 6) -> str:
    if x is None:
        return "None"
    if isinstance(x, bool):
        return "True" if x else "False"
    if isinstance(x, (int, float)):
        return f"{float(x):.{ndigits}f}"
    return str(x)


def _print_table(headers: List[str], rows: List[List[Any]]) -> None:
    # fixed-width columns
    str_rows = [[str(h) for h in headers]] + [[str(_fmt(v) if isinstance(v, (int, float, bool)) or v is None else v) for v in r] for r in rows]
    widths = [max(len(r[i]) for r in str_rows) for i in range(len(headers))]

    def _line(vals: List[str]) -> str:
        return " | ".join(vals[i].ljust(widths[i]) for i in range(len(vals)))

    print(_line(str_rows[0]))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for r in str_rows[1:]:
        print(_line(r))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="Path to releases/vX/db directory")
    ap.add_argument("--sort", default="molecule", choices=["molecule", "basis", "num_qubits", "file"])
    ap.add_argument("--csv", action="store_true", help="Also write benchmarks.csv into db-dir")
    args = ap.parse_args()

    db_dir = Path(args.db_dir).resolve()
    files = sorted(db_dir.glob("*.json"))

    rows: List[List[Any]] = []
    for f in files:
        if f.name == "index.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        molecule = _get_molecule(d, f.name)
        basis = _get_basis(d, f.name)
        mapping = _get_mapping_type(d, f.name)
        ansatz_type, ansatz_reps, ansatz_storage = _get_ansatz(d, f.name)
        active_space_enabled = _get_active_space_enabled(d)
        num_qubits, num_pauli_terms = _get_num_qubits_and_terms(d)
        hf_energy = _get_hf_energy(d)
        vqe_best = _get_vqe_best_energy(d)
        vqe_method = _get_vqe_method(d)
        exact_e = _get_exact_energy(d)

        rows.append([
            molecule,
            basis,
            mapping,
            ansatz_type,
            ansatz_reps,
            ansatz_storage,
            active_space_enabled,
            num_qubits,
            num_pauli_terms,
            hf_energy,
            vqe_best,
            vqe_method,
            exact_e,
            f.name,
        ])

    # sorting
    key_map = {
        "molecule": lambda r: (str(r[0]), str(r[1]), str(r[-1])),
        "basis": lambda r: (str(r[1]), str(r[0]), str(r[-1])),
        "num_qubits": lambda r: (r[7] if isinstance(r[7], int) else 10**9, str(r[0]), str(r[-1])),
        "file": lambda r: str(r[-1]),
    }
    rows.sort(key=key_map[args.sort])

    headers = [
        "molecule",
        "basis",
        "mapping",
        "ansatz_type",
        "ansatz_reps",
        "ansatz_storage",
        "active_space_enabled",
        "num_qubits",
        "num_pauli_terms",
        "hf_energy_hartree",
        "vqe_best_energy_hartree",
        "vqe_method",
        "exact_qubit_min_eig_hartree_like",
        "file",
    ]

    _print_table(headers, rows)

    if args.csv:
        out_csv = db_dir / "benchmarks.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(headers)
            for r in rows:
                w.writerow([_fmt(x) if isinstance(x, (int, float, bool)) or x is None else x for x in r])
        print(f"\n✅ Wrote CSV: {out_csv}")


if __name__ == "__main__":
    main()

