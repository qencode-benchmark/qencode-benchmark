"""Phase 21: Leaderboard API (Python-level).

Provides helper functions to load leaderboard rankings as JSON-serializable dicts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


_REPO = Path(__file__).resolve().parents[2]


def _lb_dir() -> Path:
    return (_REPO / "datasets" / "leaderboard").resolve()


def _load(category: str) -> pd.DataFrame:
    path = _lb_dir() / f"leaderboard_{category}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _to_rankings(df: pd.DataFrame, molecule: Optional[str], limit: Optional[int]) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    if molecule:
        df = df[df["molecule"] == molecule]
    df = df.sort_values(["molecule", "rank"])
    if limit is not None and limit > 0:
        df = df.groupby("molecule").head(limit)
    rankings: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        rankings.append(
            {
                "rank": int(r["rank"]),
                "molecule": r["molecule"],
                "mapping": r["mapping"],
                "ansatz": r["ansatz"],
                "gap": float(r["gap"]),
                "depth": int(r["depth"]),
                "two_qubit_gates": int(r["2q_gates"]),
                **({"balanced_score": float(r["balanced_score"])} if "balanced_score" in r and not pd.isna(r["balanced_score"]) else {}),
            }
        )
    return rankings


def get_accuracy_leaderboard(molecule: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Return accuracy leaderboard rankings."""
    df = _load("accuracy")
    return {
        "category": "accuracy",
        "molecule": molecule,
        "rankings": _to_rankings(df, molecule, limit),
    }


def get_cost_leaderboard(molecule: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Return hardware cost leaderboard rankings (2Q gates)."""
    df = _load("hardware_cost")
    return {
        "category": "hardware_cost",
        "molecule": molecule,
        "rankings": _to_rankings(df, molecule, limit),
    }


def get_balanced_leaderboard(molecule: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Return balanced-score leaderboard rankings."""
    df = _load("balanced")
    return {
        "category": "balanced",
        "molecule": molecule,
        "rankings": _to_rankings(df, molecule, limit),
    }

