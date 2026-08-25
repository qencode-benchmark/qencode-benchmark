"""
Phase 3: Benchmark comparison engine — turn data into insight.

- compare_mappings(): rank mappings (JW vs Parity vs BK) by gap, depth, 2q gates
- compare_ansatz(): rank ansatz types (UCCSD vs hardware_efficient)
- compare_noise_models(): compare ideal vs shots vs noisy vs mitigated
- Derived metrics: accuracy_per_depth, accuracy_per_2q_gate, noise_sensitivity
- SQLite backend for fast queries (sync from db dir)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Official certification receipts (option B)
from qencode.attestation import require_official_receipts, verify_entry_receipt

# Display names for mappings
MAPPING_DISPLAY = {"jordan_wigner": "JW", "parity": "Parity", "bravyi_kitaev": "BK"}


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


def _row_from_entry(d: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Extract one flat row from a v2 entry JSON (same logic as report_comparison_v2._row)."""
    def _get(path: List[str], default: Any = None) -> Any:
        cur = d
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    molecule = (d.get("problem") or {}).get("name") or "UNKNOWN"
    variant = (d.get("problem") or {}).get("variant") or "default"
    basis = (d.get("problem") or {}).get("basis") or "UNKNOWN"
    enc = d.get("encoding") or {}
    mapping = (enc.get("mapping") or "UNKNOWN").strip().lower().replace("-", "_")
    ansatz_type = (enc.get("ansatz_type") or "UNKNOWN").strip().lower().replace("-", "_")
    ansatz_reps = enc.get("ansatz_reps")
    if ansatz_reps is not None:
        try:
            ansatz_reps = int(float(ansatz_reps))
        except Exception:
            ansatz_reps = 1
    else:
        ansatz_reps = 1

    vqe = _as_float(_get(["results", "vqe", "best_energy_hartree_like"]))
    exact = _as_float(_get(["results", "reference", "exact_qubit_ground_energy_hartree_like"]))
    q = _get(["results", "quality"]) or {}
    trusted = bool(q.get("trusted", False))
    gap = _as_float(q.get("abs_vqe_exact_gap"))
    if gap is None and vqe is not None and exact is not None:
        gap = abs(vqe - exact)

    vqe_shots = _as_float(_get(["results", "vqe_shots", "best_energy"]))
    vqe_noisy = _as_float(_get(["results", "vqe_noisy", "best_energy"]))
    vqe_mit = _as_float(_get(["results", "vqe_mitigated", "best_energy"]))
    if exact is None:
        gap_ideal = gap_shots = gap_noisy = gap_mit = None
    else:
        gap_ideal = gap if gap is not None else (abs(vqe - exact) if vqe is not None else None)
        gap_shots = abs(vqe_shots - exact) if vqe_shots is not None else None
        gap_noisy = abs(vqe_noisy - exact) if vqe_noisy is not None else None
        gap_mit = abs(vqe_mit - exact) if vqe_mit is not None else None

    cs = d.get("circuit_stats") or {}
    depth = _as_float(cs.get("ansatz_depth_transpiled") or cs.get("ansatz_depth"))
    n2q = _as_float(cs.get("ansatz_num_2q_gates_transpiled") or cs.get("ansatz_num_2q_gates"))
    if depth is None and n2q is None:
        vqe_cm = _get(["results", "vqe", "circuit_metrics"]) or {}
        depth = _as_float(vqe_cm.get("ansatz_depth"))
        n2q = _as_float(vqe_cm.get("ansatz_num_2q_gates"))
    meas = (d.get("execution") or {}).get("measurement") or {}
    terms = _get(["artifacts", "qubit_hamiltonian", "num_pauli_terms"])
    if terms is None and _get(["artifacts", "qubit_hamiltonian", "pauli_terms"]):
        terms = len(_get(["artifacts", "qubit_hamiltonian", "pauli_terms"]))
    groups = meas.get("num_groups")
    if terms is not None:
        try:
            terms = int(float(terms))
        except Exception:
            terms = None
    if groups is not None:
        try:
            groups = int(float(groups))
        except Exception:
            groups = None

    trust_level = (d.get("trust") or {}).get("level") or "experimental"

    # Option B gating:
    # In "official" mode, entries are only eligible for trust_level == "certified"
    # if they carry a valid signed receipt.
    if require_official_receipts() and trust_level == "certified":
        ok, _reason = verify_entry_receipt(d)
        if not ok:
            trust_level = "validated"

    return {
        "molecule": molecule,
        "variant": variant or "default",
        "basis": basis,
        "mapping": mapping,
        "ansatz_type": ansatz_type,
        "ansatz_reps": ansatz_reps or 1,
        "vqe_energy": vqe,
        "exact_energy": exact,
        "gap_ideal": gap_ideal,
        "gap_shots": gap_shots,
        "gap_noisy": gap_noisy,
        "gap_mit": gap_mit,
        "trusted": trusted,
        "depth": int(depth) if depth is not None else None,
        "num_2q_gates": int(n2q) if n2q is not None else None,
        "terms": terms,
        "groups": groups,
        "file": filename,
        "entry_id": d.get("entry_id"),
        "trust_level": trust_level,
    }


def init_sqlite(conn: sqlite3.Connection) -> None:
    """Create benchmarks table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            molecule TEXT,
            variant TEXT,
            basis TEXT,
            mapping TEXT,
            ansatz_type TEXT,
            ansatz_reps INTEGER,
            vqe_energy REAL,
            exact_energy REAL,
            gap_ideal REAL,
            gap_shots REAL,
            gap_noisy REAL,
            gap_mit REAL,
            trusted INTEGER,
            depth INTEGER,
            num_2q_gates INTEGER,
            terms INTEGER,
            groups INTEGER,
            file TEXT,
            entry_id TEXT,
            trust_level TEXT,
            PRIMARY KEY (molecule, variant, basis, mapping, ansatz_type, ansatz_reps)
        )
    """)
    # Phase 15: add trust_level column if table already existed without it
    try:
        conn.execute("ALTER TABLE benchmarks ADD COLUMN trust_level TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.commit()


def _row_richness(row: Dict[str, Any]) -> int:
    """Prefer row with more backend data (noisy, shots, mit) for sync merge."""
    r = 0
    if row.get("gap_noisy") is not None:
        r += 4
    if row.get("gap_shots") is not None:
        r += 2
    if row.get("gap_mit") is not None:
        r += 1
    return r


def list_molecules(sqlite_path: Path) -> List[str]:
    """Return distinct molecules from benchmarks table, sorted."""
    conn = sqlite3.connect(str(sqlite_path))
    init_sqlite(conn)
    try:
        cur = conn.execute("SELECT DISTINCT molecule FROM benchmarks WHERE molecule IS NOT NULL ORDER BY molecule")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def count_certified(sqlite_path: Path) -> int:
    """Return number of certified entries (Phase 15/16)."""
    conn = sqlite3.connect(str(sqlite_path))
    init_sqlite(conn)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM benchmarks WHERE trust_level = ?", ("certified",))
        return cur.fetchone()[0] or 0
    finally:
        conn.close()


def sync_from_dir(db_dir: Path, sqlite_path: Path) -> int:
    """Scan db_dir for v2 entry JSONs, upsert into SQLite. When multiple entries share the same
    (molecule, variant, basis, mapping, ansatz_type, ansatz_reps), keep the richest row (has
    gap_noisy > gap_shots > gap_mit). Returns number of rows upserted."""
    db_dir = Path(db_dir).resolve()
    sqlite_path = Path(sqlite_path).resolve()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    ignore = {"index.json", "benchmarks.csv", "manifest.json", "entry_content_hashes.json",
              "trusted_index.json", "trusted_benchmarks.csv", "canonical_index.json"}
    by_key: Dict[Tuple[str, str, str, str, str, int], Dict[str, Any]] = {}
    for p in sorted(db_dir.glob("*.json")):
        if p.name in ignore or "__sha256_" not in p.name or "_v2__sha256_" not in p.name:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            row = _row_from_entry(d, p.name)
        except Exception:
            continue
        key = (
            row["molecule"], row["variant"], row["basis"], row["mapping"],
            row["ansatz_type"], row.get("ansatz_reps") or 1,
        )
        if key not in by_key or _row_richness(row) > _row_richness(by_key[key]):
            by_key[key] = row
    conn = sqlite3.connect(str(sqlite_path))
    init_sqlite(conn)
    try:
        for key, row in by_key.items():
            trust_level = row.get("trust_level") or "experimental"
            conn.execute("""
                INSERT OR REPLACE INTO benchmarks (
                    molecule, variant, basis, mapping, ansatz_type, ansatz_reps,
                    vqe_energy, exact_energy, gap_ideal, gap_shots, gap_noisy, gap_mit,
                    trusted, depth, num_2q_gates, terms, groups, file, entry_id, trust_level
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["molecule"], row["variant"], row["basis"], row["mapping"],
                row["ansatz_type"], row["ansatz_reps"],
                row["vqe_energy"], row["exact_energy"], row["gap_ideal"], row["gap_shots"],
                row["gap_noisy"], row["gap_mit"],
                1 if row["trusted"] else 0,
                row["depth"], row["num_2q_gates"], row["terms"], row["groups"],
                row["file"], row.get("entry_id"), trust_level,
            ))
        conn.commit()
    finally:
        conn.close()
    return len(by_key)


def _rows_from_sqlite(sqlite_path: Path, molecule: Optional[str] = None, variant: Optional[str] = None,
                      basis: Optional[str] = None, mapping: Optional[str] = None,
                      ansatz_type: Optional[str] = None,
                      trust_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query benchmarks table; return list of dicts. trust_level: 'certified' or 'validated' filters (Phase 15)."""
    conn = sqlite3.connect(str(sqlite_path))
    init_sqlite(conn)  # ensure schema (e.g. trust_level) exists for existing DBs
    conn.row_factory = sqlite3.Row
    try:
        q = "SELECT * FROM benchmarks WHERE 1=1"
        params: List[Any] = []
        if molecule is not None:
            q += " AND molecule = ?"
            params.append(molecule)
        if variant is not None:
            q += " AND variant = ?"
            params.append(variant)
        if basis is not None:
            q += " AND basis = ?"
            params.append(basis)
        if mapping is not None:
            q += " AND mapping = ?"
            params.append(mapping)
        if ansatz_type is not None:
            q += " AND ansatz_type = ?"
            params.append(ansatz_type)
        if trust_level == "certified":
            q += " AND trust_level = ?"
            params.append("certified")
        elif trust_level == "validated":
            q += " AND (trust_level = ? OR trust_level = ?)"
            params.append("validated")
            params.append("certified")
        q += " ORDER BY molecule, variant, basis, ansatz_type, mapping"
        cur = conn.execute(q, params)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["trusted"] = bool(r.get("trusted"))
            r["trust_level"] = r.get("trust_level") or "experimental"
        return rows
    finally:
        conn.close()


def _add_derived_metrics(rows: List[Dict[str, Any]]) -> None:
    """In-place add accuracy_per_depth, accuracy_per_2q_gate, noise_sensitivity,
    hardware_efficiency_by_depth, hardware_efficiency_by_2q."""
    for r in rows:
        gap = r.get("gap_ideal")
        depth = r.get("depth")
        n2q = r.get("num_2q_gates")
        gap_noisy = r.get("gap_noisy")
        if gap is not None and depth is not None and depth > 0:
            r["accuracy_per_depth"] = gap / depth  # lower is better (smaller gap per unit depth)
        else:
            r["accuracy_per_depth"] = None
        if gap is not None and n2q is not None and n2q > 0:
            r["accuracy_per_2q_gate"] = gap / n2q
        else:
            r["accuracy_per_2q_gate"] = None
        if gap is not None and gap_noisy is not None:
            r["noise_sensitivity"] = gap_noisy - gap  # positive = noise hurts
        else:
            r["noise_sensitivity"] = None
        # Hardware efficiency: gap * cost — lower = better (cost-aware ranking)
        r["hardware_efficiency_by_depth"] = gap * depth if (gap is not None and depth is not None) else None
        r["hardware_efficiency_by_2q"] = gap * n2q if (gap is not None and n2q is not None) else None


def compare_mappings(
    sqlite_path: Path,
    molecule: str,
    ansatz_type: Optional[str] = None,
    variant: str = "default",
    basis: Optional[str] = None,
    add_derived: bool = True,
    trust_level: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Compare mappings (JW, Parity, BK) for a molecule (and optional ansatz filter).
    Returns (rows, ranking) where ranking is e.g. ["Parity", "BK", "JW"] best first.
    trust_level: 'certified' or 'validated' to filter (Phase 15).
    """
    rows = _rows_from_sqlite(sqlite_path, molecule=molecule, variant=variant, basis=basis, ansatz_type=ansatz_type, trust_level=trust_level)
    if add_derived:
        _add_derived_metrics(rows)
    # Rank by: trusted first, then lower gap_ideal, then lower depth, then lower num_2q_gates
    def rank_key(r: Dict[str, Any]) -> Tuple[int, float, int, int]:
        trusted = 0 if r.get("trusted") else 1
        gap = r.get("gap_ideal")
        gap_val = float("inf") if gap is None else gap
        depth = r.get("depth") or 999999
        n2q = r.get("num_2q_gates") or 999999
        return (trusted, gap_val, depth, n2q)
    by_mapping: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        m = r["mapping"]
        if m not in by_mapping or rank_key(r) < rank_key(by_mapping[m]):
            by_mapping[m] = r
    sorted_mappings = sorted(by_mapping.keys(), key=lambda m: rank_key(by_mapping[m]))
    ranking = [MAPPING_DISPLAY.get(m, m) for m in sorted_mappings]
    return list(by_mapping.values()), ranking


def compare_ansatz(
    sqlite_path: Path,
    molecule: str,
    mapping: Optional[str] = None,
    variant: str = "default",
    basis: Optional[str] = None,
    add_derived: bool = True,
    trust_level: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Compare ansatz types (UCCSD vs hardware_efficient) for a molecule.
    Returns (rows, ranking) e.g. ["uccsd", "hardware_efficient"] best first.
    trust_level: 'certified' or 'validated' to filter (Phase 15).
    """
    rows = _rows_from_sqlite(sqlite_path, molecule=molecule, variant=variant, basis=basis, mapping=mapping, trust_level=trust_level)
    if add_derived:
        _add_derived_metrics(rows)
    def rank_key(r: Dict[str, Any]) -> Tuple[int, float, int, int]:
        trusted = 0 if r.get("trusted") else 1
        gap = r.get("gap_ideal") or float("inf")
        depth = r.get("depth") or 999999
        n2q = r.get("num_2q_gates") or 999999
        return (trusted, gap, depth, n2q)
    by_ansatz: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = r["ansatz_type"]
        if a not in by_ansatz or rank_key(r) < rank_key(by_ansatz[a]):
            by_ansatz[a] = r
    sorted_ansatz = sorted(by_ansatz.keys(), key=lambda a: rank_key(by_ansatz[a]))
    return list(by_ansatz.values()), sorted_ansatz


def compare_noise_models(
    sqlite_path: Path,
    molecule: str,
    mapping: Optional[str] = None,
    ansatz_type: Optional[str] = None,
    variant: str = "default",
    basis: Optional[str] = None,
    add_derived: bool = True,
    trust_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Compare ideal vs shots vs noisy vs mitigated for entries matching filters.
    Returns rows with gap_ideal, gap_shots, gap_noisy, gap_mit and noise_sensitivity.
    trust_level: 'certified' or 'validated' to filter (Phase 15).
    """
    rows = _rows_from_sqlite(sqlite_path, molecule=molecule, variant=variant, basis=basis,
                             mapping=mapping, ansatz_type=ansatz_type, trust_level=trust_level)
    if add_derived:
        _add_derived_metrics(rows)
    return rows


def full_comparison(
    sqlite_path: Path,
    molecule: str,
    variant: str = "default",
    basis: Optional[str] = None,
    trust_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run full comparison for a molecule: mapping ranking per ansatz, ansatz ranking per mapping,
    derived metrics, noise comparison. trust_level: 'certified' or 'validated' to restrict (Phase 15).
    """
    result: Dict[str, Any] = {
        "molecule": molecule,
        "variant": variant,
        "basis": basis,
        "mapping_ranking_by_ansatz": {},
        "ansatz_ranking_by_mapping": {},
        "rows": [],
        "derived_metrics": [],
    }
    rows = _rows_from_sqlite(sqlite_path, molecule=molecule, variant=variant, basis=basis, trust_level=trust_level)
    _add_derived_metrics(rows)
    result["rows"] = rows

    ansatz_types = sorted({r["ansatz_type"] for r in rows})
    for at in ansatz_types:
        _, ranking = compare_mappings(sqlite_path, molecule, ansatz_type=at, variant=variant, basis=basis, add_derived=False, trust_level=trust_level)
        result["mapping_ranking_by_ansatz"][at] = ranking

    mappings = sorted({r["mapping"] for r in rows})
    for m in mappings:
        _, ranking = compare_ansatz(sqlite_path, molecule, mapping=m, variant=variant, basis=basis, add_derived=False, trust_level=trust_level)
        result["ansatz_ranking_by_mapping"][m] = ranking

    # One row per (molecule, variant, basis, mapping, ansatz) with derived metrics
    result["derived_metrics"] = [
        {k: r.get(k) for k in ["mapping", "ansatz_type", "gap_ideal", "depth", "num_2q_gates",
                                "accuracy_per_depth", "accuracy_per_2q_gate", "noise_sensitivity",
                                "hardware_efficiency_by_depth", "hardware_efficiency_by_2q"]}
        for r in rows
    ]
    return result


def get_rows_for_report(sqlite_path: Path, molecule: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return rows with legacy key names for report_comparison_v2 / CSV compatibility.
    """
    raw = _rows_from_sqlite(sqlite_path, molecule=molecule)
    out = []
    for r in raw:
        out.append({
            "molecule": r.get("molecule"),
            "variant": r.get("variant"),
            "basis": r.get("basis"),
            "mapping": r.get("mapping"),
            "ansatz_type": r.get("ansatz_type"),
            "ansatz_reps": r.get("ansatz_reps"),
            "vqe": r.get("vqe_energy"),
            "exact": r.get("exact_energy"),
            "gap": r.get("gap_ideal"),
            "trusted": r.get("trusted"),
            "gap_ideal": r.get("gap_ideal"),
            "gap_shots": r.get("gap_shots"),
            "gap_noisy": r.get("gap_noisy"),
            "gap_mitigated": r.get("gap_mit"),
            "ansatz_depth": r.get("depth"),
            "ansatz_num_2q_gates": r.get("num_2q_gates"),
            "ansatz_depth_transpiled": r.get("depth"),
            "ansatz_num_2q_gates_transpiled": r.get("num_2q_gates"),
            "num_pauli_terms": r.get("terms"),
            "num_groups": r.get("groups"),
            "file": r.get("file"),
            "exact_missing": r.get("exact_energy") is None,
            "vqe_shots_stderr": None,
            "vqe_noisy_stderr": None,
            "vqe_mitigated_stderr": None,
            "transpile_basis_gates": None,
            "transpile_optimization_level": None,
            "shots_per_group": None,
            "estimated_shots_total": None,
        })
    return out


__all__ = [
    "MAPPING_DISPLAY",
    "count_certified",
    "init_sqlite",
    "list_molecules",
    "sync_from_dir",
    "compare_mappings",
    "compare_ansatz",
    "compare_noise_models",
    "full_comparison",
    "get_rows_for_report",
    "_row_from_entry",
]
