"""
Phase 17: Leaderboard data model.

This module defines a canonical, rankable record shape for leaderboards.

Inputs can be:
- Benchmark rows from `qencode.comparison_engine` / SQLite sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


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


def _as_int(x: Any) -> Optional[int]:
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return int(x)
    if isinstance(x, str):
        try:
            return int(float(x.strip()))
        except Exception:
            return None
    return None


def compute_balanced_score(entry: Dict[str, Any]) -> Optional[float]:
    """
    Compute v1 balanced score.

    v1 formula: score = gap * depth  (lower is better)
    """
    gap = _as_float(entry.get("gap"))
    depth = _as_int(entry.get("depth"))
    if gap is None or depth is None:
        return None
    return float(gap) * float(depth)


def create_leaderboard_entry(
    result: Dict[str, Any],
    *,
    gap_key: str = "gap_ideal",
    backend: Optional[str] = None,
    workflow: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a benchmark/workflow result dict into a leaderboard entry record.

    - gap_key: which metric to use for `gap` (default: gap_ideal)
    - backend: label like 'ideal' or 'noisy' (optional; informational)
    - workflow: workflow name if applicable
    - timestamp: ISO date (YYYY-MM-DD). If not provided, uses today's UTC date.
    """
    # Benchmark-row naming
    molecule = result.get("molecule")
    mapping = result.get("mapping")
    ansatz = result.get("ansatz_type") or result.get("ansatz")
    trust_level = result.get("trust_level")

    # Workflow-row naming
    if molecule is None:
        molecule = (result.get("_raw") or {}).get("molecule") or result.get("molecule")
    if workflow is None:
        workflow = result.get("workflow") or result.get("workflow_name")

    gap = result.get(gap_key)
    if gap is None and gap_key != "gap":
        gap = result.get("gap")
    depth = result.get("depth")
    two_q = result.get("two_qubit_gates")
    if two_q is None:
        two_q = result.get("num_2q_gates")
    if two_q is None:
        two_q = result.get("2q_gates")

    if backend is None:
        # If the chosen gap key is noisy, label backend accordingly.
        backend = "noisy" if gap_key == "gap_noisy" else "ideal"

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).date().isoformat()

    entry = {
        "molecule": str(molecule) if molecule is not None else None,
        "mapping": str(mapping) if mapping is not None else None,
        "ansatz": str(ansatz) if ansatz is not None else None,
        "workflow": str(workflow) if workflow is not None else None,
        "backend": str(backend) if backend is not None else None,
        "gap": _as_float(gap),
        "depth": _as_int(depth),
        "two_qubit_gates": _as_int(two_q),
        "trust_level": str(trust_level) if trust_level is not None else None,
        "timestamp": timestamp,
    }
    # Traceability if present
    if result.get("file") is not None:
        entry["entry_file"] = result.get("file")
    if result.get("entry_id") is not None:
        entry["entry_id"] = result.get("entry_id")

    return entry

