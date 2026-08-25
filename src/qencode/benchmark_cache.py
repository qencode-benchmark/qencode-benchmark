"""
Phase 2: Cache expensive benchmark steps — Hamiltonian (via entry file), exact energy, measurement grouping.
Cache key: (molecule, variant, basis, mapping, ansatz_type, ansatz_reps[, active_space]).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _cache_key(molecule: str, variant: str, basis: str, mapping: str, ansatz_type: str, ansatz_reps: int, active_space: Optional[str] = None) -> str:
    parts = [molecule, variant, basis, mapping, ansatz_type, str(ansatz_reps)]
    if active_space:
        parts.append(active_space)
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_cached_exact(cache_dir: Path, molecule: str, variant: str, basis: str, mapping: str, ansatz_type: str, ansatz_reps: int = 1, active_space: Optional[str] = None) -> Optional[float]:
    """Return cached exact energy if present."""
    if not cache_dir or not cache_dir.is_dir():
        return None
    key = _cache_key(molecule, variant, basis, mapping, ansatz_type, ansatz_reps, active_space)
    path = cache_dir / "exact" / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("exact_qubit_ground_energy_hartree_like")
    except Exception:
        return None


def set_cached_exact(cache_dir: Path, molecule: str, variant: str, basis: str, mapping: str, ansatz_type: str, ansatz_reps: int, exact_energy: float, active_space: Optional[str] = None) -> None:
    """Store exact energy in cache."""
    if not cache_dir:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "exact").mkdir(parents=True, exist_ok=True)
    key = _cache_key(molecule, variant, basis, mapping, ansatz_type, ansatz_reps, active_space)
    path = cache_dir / "exact" / f"{key}.json"
    path.write_text(json.dumps({"exact_qubit_ground_energy_hartree_like": exact_energy}, indent=0), encoding="utf-8")


def get_cached_grouping(cache_dir: Path, molecule: str, variant: str, basis: str, mapping: str, ansatz_type: str, ansatz_reps: int = 1, active_space: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return cached grouping stats (num_terms, num_groups, etc.) if present."""
    if not cache_dir or not cache_dir.is_dir():
        return None
    key = _cache_key(molecule, variant, basis, mapping, ansatz_type, ansatz_reps, active_space)
    path = cache_dir / "grouping" / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def set_cached_grouping(cache_dir: Path, molecule: str, variant: str, basis: str, mapping: str, ansatz_type: str, ansatz_reps: int, stats: Dict[str, Any], active_space: Optional[str] = None) -> None:
    """Store grouping stats in cache."""
    if not cache_dir:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "grouping").mkdir(parents=True, exist_ok=True)
    key = _cache_key(molecule, variant, basis, mapping, ansatz_type, ansatz_reps, active_space)
    path = cache_dir / "grouping" / f"{key}.json"
    path.write_text(json.dumps(stats, indent=0), encoding="utf-8")


__all__ = [
    "get_cached_exact",
    "set_cached_exact",
    "get_cached_grouping",
    "set_cached_grouping",
]
