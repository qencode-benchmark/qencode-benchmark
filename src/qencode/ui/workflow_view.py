"""Phase 16: Workflows view — compare named VQE strategies."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qencode.workflows import (
    list_workflows,
    load_workflow,
    load_workflow_results,
    rank_by_accuracy,
    rank_by_balanced_score,
    rank_by_hardware_cost,
)


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def render_workflows(repo_root: Path) -> None:
    """Render Workflows page: list workflows, compare by molecule, best accuracy/cost/balanced."""
    st.header("Workflows")
    st.caption("Compare named VQE workflow strategies across molecules.")

    workflows_dir = repo_root / "workflows"
    results_dir = repo_root / "workflows" / "results"

    workflow_names = list_workflows(workflows_dir)
    if not workflow_names:
        st.warning("No workflows found in workflows/ directory.")
        return

    # List available workflows with descriptions
    st.subheader("Available workflows")
    for name in workflow_names:
        try:
            wf = load_workflow(name, workflows_dir=workflows_dir)
            desc = (wf.get("metadata") or {}).get("description") or "No description"
            st.markdown(f"- **{name}**: {desc}")
        except Exception:
            st.markdown(f"- **{name}**")

    # Discover molecules from workflow results
    if not results_dir.is_dir():
        st.info(
            "No workflow results yet. Run workflows for a molecule to compare:\n\n"
            "```bash\npython scripts/run_workflow.py --workflow vqe_standard --molecule H2\n"
            "python scripts/run_workflow.py --workflow vqe_fast --molecule H2\n```"
        )
        return

    molecules = sorted({p.stem.split("_", 1)[0] for p in results_dir.glob("*_*.json")})
    if not molecules:
        st.info("No workflow results found. Run `run_workflow.py` for each workflow and molecule.")
        return

    mol_sel = st.selectbox("Molecule", molecules, key="wf_mol")

    results = load_workflow_results(mol_sel, results_dir=results_dir)
    if not results:
        st.info(f"No workflow results for {mol_sel}.")
        return

    # Rankings
    st.subheader("Compare workflows")
    acc_rank = rank_by_accuracy(results)
    cost_rank = rank_by_hardware_cost(results)
    balanced_rank = rank_by_balanced_score(results)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Best accuracy** (lowest error)")
        for i, w in enumerate(acc_rank, 1):
            r = next((x for x in results if x["workflow_name"] == w), {})
            st.markdown(f"{i}. {w} ({_fmt(r.get('gap_noisy'))})")
    with col2:
        st.markdown("**Best cost** (lowest depth)")
        for i, w in enumerate(cost_rank, 1):
            r = next((x for x in results if x["workflow_name"] == w), {})
            st.markdown(f"{i}. {w} (depth: {_fmt(r.get('depth'))})")
    with col3:
        st.markdown("**Best balanced** (accuracy × cost)")
        for i, w in enumerate(balanced_rank, 1):
            r = next((x for x in results if x["workflow_name"] == w), {})
            g, d = r.get("gap_noisy"), r.get("depth")
            score = f"{float(g)*float(d):.2f}" if g is not None and d is not None else "—"
            st.markdown(f"{i}. {w} ({score})")

    # Table
    st.subheader("Workflow results table")
    rows = []
    for r in results:
        rows.append({
            "workflow": r["workflow_name"],
            "error (gap_noisy)": r.get("gap_noisy"),
            "depth": r.get("depth"),
            "2q gates": r.get("num_2q_gates"),
            "shots": r.get("shots"),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv_bytes,
        file_name=f"workflows_{mol_sel}.csv",
        mime="text/csv",
        key="wf_csv",
    )
