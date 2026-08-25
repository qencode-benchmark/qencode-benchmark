"""
Phase 7: Ranking engine — turn benchmarks into ranked recommendations.

- rank_mappings(molecule, ansatz): best mapping per ansatz (with hardware efficiency score)
- rank_ansatz(molecule, mapping): best ansatz per mapping
- rank_noise_resilience(molecule): best configs by noise resilience (lowest noise_sensitivity)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qencode.comparison_engine import (
    MAPPING_DISPLAY,
    compare_ansatz,
    compare_mappings,
    compare_noise_models,
    full_comparison,
    sync_from_dir,
)


def rank_mappings(
    sqlite_path: Path,
    molecule: str,
    ansatz_type: Optional[str] = None,
    variant: str = "default",
    basis: Optional[str] = None,
    use_hardware_efficiency: str = "depth",
    trust_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Rank mappings (JW, BK, Parity) for a molecule, optionally filtered by ansatz.
    Returns list of {"mapping_display": str, "mapping": str, "rank": int, "gap_ideal": float,
    "hardware_efficiency": float} best first. trust_level: 'certified' or 'validated' (Phase 15).
    """
    rows, ranking = compare_mappings(
        sqlite_path, molecule, ansatz_type=ansatz_type, variant=variant, basis=basis, trust_level=trust_level
    )
    # Build per-mapping best row (for gap, depth, 2q)
    by_mapping: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        m = r["mapping"]
        if m not in by_mapping or (r.get("gap_ideal") or 999) < (by_mapping[m].get("gap_ideal") or 999):
            by_mapping[m] = r
    # Re-rank using hardware efficiency if available
    he_key = "hardware_efficiency_by_depth" if use_hardware_efficiency == "depth" else "hardware_efficiency_by_2q"
    out: List[Dict[str, Any]] = []
    for i, disp in enumerate(ranking):
        mapping = next((k for k, v in MAPPING_DISPLAY.items() if v == disp), disp)
        row = by_mapping.get(mapping, {})
        gap = row.get("gap_ideal")
        he = row.get(he_key)
        out.append({
            "rank": i + 1,
            "mapping_display": disp,
            "mapping": mapping,
            "gap_ideal": gap,
            "hardware_efficiency": he,
        })
    return out


def rank_ansatz(
    sqlite_path: Path,
    molecule: str,
    mapping: Optional[str] = None,
    variant: str = "default",
    basis: Optional[str] = None,
    trust_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Rank ansatz types for a molecule, optionally filtered by mapping.
    Returns list of {"ansatz_type": str, "rank": int, "gap_ideal": float} best first. trust_level: Phase 15.
    """
    rows, ranking = compare_ansatz(
        sqlite_path, molecule, mapping=mapping, variant=variant, basis=basis, trust_level=trust_level
    )
    by_ansatz: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = r["ansatz_type"]
        if a not in by_ansatz or (r.get("gap_ideal") or 999) < (by_ansatz[a].get("gap_ideal") or 999):
            by_ansatz[a] = r
    out: List[Dict[str, Any]] = []
    for i, ans in enumerate(ranking):
        row = by_ansatz.get(ans, {})
        out.append({
            "rank": i + 1,
            "ansatz_type": ans,
            "gap_ideal": row.get("gap_ideal"),
        })
    return out


def rank_noise_resilience(
    sqlite_path: Path,
    molecule: str,
    variant: str = "default",
    basis: Optional[str] = None,
    trust_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Rank configs by noise resilience. Lower noise_sensitivity = more resilient.
    Returns list of {"mapping_display", "ansatz_type", "rank", "noise_sensitivity", "gap_ideal", "gap_noisy"}.
    trust_level: 'certified' or 'validated' (Phase 15).
    """
    rows = compare_noise_models(sqlite_path, molecule, variant=variant, basis=basis, trust_level=trust_level)
    # Only rows with noise_sensitivity
    with_noise = [r for r in rows if r.get("noise_sensitivity") is not None]
    if not with_noise:
        return []
    # Sort by noise_sensitivity ascending (lower = more resilient)
    sorted_rows = sorted(with_noise, key=lambda r: (r.get("noise_sensitivity") or 999))
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(sorted_rows):
        m = r.get("mapping", "")
        out.append({
            "rank": i + 1,
            "mapping_display": MAPPING_DISPLAY.get(m, m),
            "ansatz_type": r.get("ansatz_type", ""),
            "noise_sensitivity": r.get("noise_sensitivity"),
            "gap_ideal": r.get("gap_ideal"),
            "gap_noisy": r.get("gap_noisy"),
        })
    return out


def full_ranking(
    sqlite_path: Path,
    molecule: str,
    variant: str = "default",
    basis: Optional[str] = None,
    trust_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full ranking: best mapping per ansatz, best ansatz per mapping, best noise resilience.
    trust_level: 'certified' or 'validated' to use only those entries for official rankings (Phase 15).
    """
    result = full_comparison(sqlite_path, molecule, variant=variant, basis=basis, trust_level=trust_level)
    mapping_by_ansatz: Dict[str, List[Dict[str, Any]]] = {}
    for ans in result.get("mapping_ranking_by_ansatz", {}):
        mapping_by_ansatz[ans] = rank_mappings(sqlite_path, molecule, ansatz_type=ans, variant=variant, basis=basis, trust_level=trust_level)
    ansatz_by_mapping: Dict[str, List[Dict[str, Any]]] = {}
    for m in result.get("ansatz_ranking_by_mapping", {}):
        ansatz_by_mapping[m] = rank_ansatz(sqlite_path, molecule, mapping=m, variant=variant, basis=basis, trust_level=trust_level)
    noise = rank_noise_resilience(sqlite_path, molecule, variant=variant, basis=basis, trust_level=trust_level)
    return {
        "molecule": molecule,
        "variant": variant,
        "mapping_by_ansatz": mapping_by_ansatz,
        "ansatz_by_mapping": ansatz_by_mapping,
        "noise_resilience": noise,
    }
