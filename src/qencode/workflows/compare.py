"""
Phase 12: Workflow comparison — rank workflows by accuracy, hardware cost, balanced score.

Loads workflow result JSONs (from Phase 11), compares gap_noisy, depth, 2q_gates, shots,
and produces rankings: best accuracy, best hardware efficiency, best balanced.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[2]


def load_workflow_results(
    molecule: str,
    results_dir: Optional[Path] = None,
    workflows_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Load all workflow result JSONs for a molecule.

    Looks for workflows/results/<molecule>_<workflow>.json.
    Returns list of dicts with: workflow_name, molecule, gap_noisy, depth, num_2q_gates, shots,
    plus raw results/execution for display. If workflows_filter is set, only include those
    workflow names (and only if file exists).
    """
    results_dir = (results_dir or _REPO / "workflows" / "results").resolve()
    if not results_dir.is_dir():
        return []

    out: List[Dict[str, Any]] = []
    pattern = f"{molecule}_*.json"
    for path in results_dir.glob(pattern):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        wf_name = doc.get("workflow_name") or path.stem.replace(f"{molecule}_", "", 1)
        if doc.get("molecule") != molecule and path.stem != f"{molecule}_{wf_name}":
            continue
        if workflows_filter is not None and wf_name not in workflows_filter:
            continue
        res = doc.get("results") or {}
        exec_cfg = doc.get("execution") or {}
        out.append({
            "workflow_name": wf_name,
            "molecule": molecule,
            "gap_noisy": res.get("gap_noisy"),
            "gap_ideal": res.get("gap_ideal"),
            "gap_mit": res.get("gap_mit"),
            "depth": res.get("depth"),
            "num_2q_gates": res.get("num_2q_gates"),
            "shots": exec_cfg.get("shots"),
            "_raw": doc,
        })
    return out


def _gap_sort_key(item: Dict[str, Any]) -> float:
    g = item.get("gap_noisy")
    if g is None:
        return float("inf")
    try:
        return float(g)
    except (TypeError, ValueError):
        return float("inf")


def _depth_sort_key(item: Dict[str, Any]) -> tuple:
    d = item.get("depth")
    n = item.get("num_2q_gates")
    try:
        depth = float(d) if d is not None else float("inf")
    except (TypeError, ValueError):
        depth = float("inf")
    try:
        n2q = float(n) if n is not None else float("inf")
    except (TypeError, ValueError):
        n2q = float("inf")
    return (depth, n2q)


def _balanced_sort_key(item: Dict[str, Any]) -> float:
    g = item.get("gap_noisy")
    d = item.get("depth")
    if g is None or d is None:
        return float("inf")
    try:
        return float(g) * float(d)
    except (TypeError, ValueError):
        return float("inf")


def rank_by_accuracy(results: List[Dict[str, Any]]) -> List[str]:
    """Rank workflows by best accuracy (lowest gap_noisy first)."""
    ordered = sorted(results, key=_gap_sort_key)
    return [r["workflow_name"] for r in ordered]


def rank_by_hardware_cost(results: List[Dict[str, Any]]) -> List[str]:
    """Rank workflows by hardware efficiency (lowest depth, then 2q_gates)."""
    ordered = sorted(results, key=_depth_sort_key)
    return [r["workflow_name"] for r in ordered]


def rank_by_balanced_score(results: List[Dict[str, Any]]) -> List[str]:
    """Rank workflows by balanced score (gap_noisy * depth, lower is better)."""
    ordered = sorted(results, key=_balanced_sort_key)
    return [r["workflow_name"] for r in ordered]
