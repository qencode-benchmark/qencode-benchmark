"""
Phase 14: Cache layer — Layer 1 (result cache) and Layer 2 (intermediate) stubs.

Layer 1: Before running a benchmark, check if exact config already has a result;
if so return the existing entry path. After a successful run, store config -> entry path.
Layer 2 (stubs): Intermediate artifacts (Hamiltonian, exact energy, groups, etc.) — to be implemented later.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

# cache.py lives at src/qencode/cache.py
# parents[0] = src/qencode, parents[1] = src, parents[2] = repo root
_REPO = Path(__file__).resolve().parents[2]

# Keys that define a benchmark run (deterministic order for hashing)
_CONFIG_KEYS = [
    "molecule", "variant", "basis", "active_space",
    "mapping", "ansatz_type", "ansatz_reps",
    "backend", "optimizer", "maxiter", "shots",
    "grouping", "mitigation", "profile", "workflow",
    "out_dir",
]


def _norm_mapping(s: str) -> str:
    m = (s or "").strip().lower()
    if m in ("jw", "jordan-wigner"):
        return "jordan_wigner"
    if m in ("bk", "bravyi-kitaev"):
        return "bravyi_kitaev"
    if m == "parity":
        return "parity"
    return m or "jordan_wigner"


def _norm_ansatz(s: str) -> str:
    a = (s or "").strip().lower()
    if a in ("he", "hardware-efficient"):
        return "hardware_efficient"
    if a == "uccsd":
        return "uccsd"
    return a or "uccsd"


def get_cache_dir(repo_root: Optional[Path] = None) -> Path:
    """Default cache root: releases/v2/cache (result index + intermediates)."""
    repo = (repo_root or _REPO).resolve()
    return repo / "releases" / "v2" / "cache"


def normalize_benchmark_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a canonical dict for hashing (sorted keys, normalized values)."""
    out: Dict[str, Any] = {}
    for k in _CONFIG_KEYS:
        v = config.get(k)
        if v is None:
            out[k] = None
            continue
        if k == "mapping":
            out[k] = _norm_mapping(str(v))
        elif k == "ansatz_type":
            out[k] = _norm_ansatz(str(v))
        elif k == "out_dir":
            out[k] = str(Path(v).resolve()) if v else None
        elif k in ("maxiter", "ansatz_reps", "shots") and v is not None:
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = str(v)
        else:
            out[k] = str(v).strip() if isinstance(v, str) else v
    return out


def compute_config_hash(config: Dict[str, Any]) -> str:
    """Deterministic hash of a benchmark config (for Layer 1 result cache)."""
    normalized = normalize_benchmark_config(config)
    blob = json.dumps(normalized, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _results_index_path(cache_dir: Path) -> Path:
    return cache_dir / "results_index.json"


def lookup_cached_result(
    config: Dict[str, Any],
    cache_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Optional[Path]:
    """
    Layer 1: If we have a cached result for this exact config, return the entry path.
    Returns None if no cache or entry file no longer exists.
    """
    cache_dir = cache_dir or get_cache_dir(repo_root)
    index_path = _results_index_path(cache_dir)
    if not index_path.exists():
        return None
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    h = compute_config_hash(config)
    entry_path_str = data.get(h)
    if not entry_path_str:
        return None
    p = Path(entry_path_str)
    return p if p.exists() else None


def store_cached_result(
    config: Dict[str, Any],
    entry_path: Path,
    cache_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """Layer 1: Record that this config produced this entry (so future runs can skip)."""
    cache_dir = cache_dir or get_cache_dir(repo_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path = _results_index_path(cache_dir)
    data: Dict[str, Any] = {}
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    h = compute_config_hash(config)
    data[h] = str(entry_path.resolve())
    index_path.write_text(json.dumps(data, sort_keys=True, indent=0), encoding="utf-8")


# --- Layer 2 (intermediate artifact cache) — stubs for future use ---


def lookup_intermediate_artifact(
    key: str,
    cache_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Optional[Any]:
    """
    Layer 2: Look up a cached intermediate (e.g. Hamiltonian, exact energy, groups).
    Currently returns None; implement in Phase 14b when pipeline is refactored to use it.
    """
    # Stub: no intermediate cache yet
    return None


def store_intermediate_artifact(
    key: str,
    value: Any,
    cache_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """
    Layer 2: Store an intermediate artifact for reuse.
    Currently no-op; implement in Phase 14b.
    """
    # Stub
    pass
