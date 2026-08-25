"""Phase 20: Leaderboard view — Accuracy, Cost, Balanced tables."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def render_leaderboard(repo_root: Path) -> None:
    """Render leaderboard view from datasets/leaderboard CSVs."""
    st.header("Leaderboard")
    st.caption("View best accuracy, lowest hardware cost, and best balanced configurations.")

    lb_dir = (repo_root / "datasets" / "leaderboard").resolve()
    acc_path = lb_dir / "leaderboard_accuracy.csv"
    cost_path = lb_dir / "leaderboard_hardware_cost.csv"
    bal_path = lb_dir / "leaderboard_balanced.csv"

    df_acc = _load_csv(acc_path)
    df_cost = _load_csv(cost_path)
    df_bal = _load_csv(bal_path)

    if df_acc.empty and df_cost.empty and df_bal.empty:
        st.warning(
            "No leaderboard CSVs found. "
            "Run `python scripts/generate_leaderboard.py` to generate leaderboard datasets."
        )
        return

    molecules = set()
    for df in (df_acc, df_cost, df_bal):
        if "molecule" in df.columns:
            molecules.update(df["molecule"].dropna().unique().tolist())
    molecules = sorted(molecules)
    mol_sel = st.selectbox("Molecule", ["All"] + molecules, key="lb_mol")

    def _filter(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        if mol_sel != "All":
            df = df[df["molecule"] == mol_sel]
        return df.sort_values(["molecule", "rank"])

    st.subheader("Best Accuracy")
    df_acc_view = _filter(df_acc)
    if df_acc_view.empty:
        st.info("No accuracy leaderboard data for this selection.")
    else:
        st.dataframe(
            df_acc_view[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "2q_gates"]],
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Lowest Hardware Cost (2Q gates)")
    df_cost_view = _filter(df_cost)
    if df_cost_view.empty:
        st.info("No hardware cost leaderboard data for this selection.")
    else:
        st.dataframe(
            df_cost_view[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "2q_gates"]],
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Best Balanced Score (gap × depth)")
    df_bal_view = _filter(df_bal)
    if df_bal_view.empty:
        st.info("No balanced leaderboard data for this selection.")
    else:
        st.dataframe(
            df_bal_view[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "2q_gates", "balanced_score"]],
            hide_index=True,
            use_container_width=True,
        )

