"""Phase 16: Standard Suite view — certified results centerpiece."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from qencode.comparison_engine import (
    MAPPING_DISPLAY,
    count_certified,
    full_comparison,
    list_molecules,
    sync_from_dir,
)
from qencode.standard_suite import get_suite_summary, load_standard_suite


def _disp_mapping(m: str) -> str:
    return MAPPING_DISPLAY.get(m, m)


def _best_certified_summary(
    sqlite_path: Path,
    molecule: str,
    rows: List[Dict[str, Any]],
    results_dir: Path,
) -> Dict[str, str]:
    """Build best-result summary for a molecule from certified rows."""
    out: Dict[str, str] = {}
    if not rows:
        return out
    # Best certified accuracy: lowest gap
    best_acc = min(
        (r for r in rows if r.get("gap_ideal") is not None),
        key=lambda r: float(r["gap_ideal"]),
        default=None,
    )
    if best_acc:
        out["best_accuracy"] = f"{_disp_mapping(best_acc['mapping'])} + {best_acc['ansatz_type']}"

    # Lowest circuit cost: min depth
    best_cost = min(
        (r for r in rows if r.get("depth") is not None),
        key=lambda r: int(r["depth"]),
        default=None,
    )
    if best_cost:
        out["lowest_cost"] = f"{_disp_mapping(best_cost['mapping'])} + {best_cost['ansatz_type']}"

    # Best balanced workflow (from workflow results if available)
    try:
        from qencode.workflows import load_workflow_results, rank_by_balanced_score
        wf_results = load_workflow_results(molecule, results_dir=results_dir)
        if wf_results:
            ranked = rank_by_balanced_score(wf_results)
            if ranked:
                out["best_workflow"] = ranked[0]
    except Exception:
        pass
    return out


def render_standard_suite(
    db_dir: Path,
    sqlite_path: Path,
    repo_root: Path,
) -> None:
    """Render Standard Suite page: certified results, best mapping/ansatz, accuracy vs depth."""
    st.header("Standard Suite")
    sync_from_dir(db_dir, sqlite_path)

    # Suite metadata
    suite_path = repo_root / "benchmarks" / "standard" / "suite_v1.yaml"
    if suite_path.exists():
        try:
            suite = load_standard_suite(suite_path)
            summary = get_suite_summary(suite)
            st.caption(
                f"**{summary.get('name', '')}** v{summary.get('version', '')} — "
                f"{summary.get('total_run_jobs', 0)} benchmark runs"
            )
        except Exception:
            st.caption("Standard Suite v1")
    else:
        st.caption("Standard Suite v1")

    certified_count = count_certified(sqlite_path)
    st.metric("Certified results", certified_count)

    molecules = list_molecules(sqlite_path)
    if not molecules:
        st.warning("No benchmark data. Run the standard suite and assign trust levels.")
        return

    mol_sel = st.selectbox("Molecule", molecules, key="suite_mol")

    # Certified-only comparison (needed for summary and table)
    result = full_comparison(sqlite_path, mol_sel, trust_level="certified")
    rows = result["rows"]

    if not rows:
        st.info(f"No certified results for {mol_sel}. Run `assign_trust_levels.py` and sync.")
        return

    # Best result summary panel
    results_dir = repo_root / "workflows" / "results"
    summary_panel = _best_certified_summary(sqlite_path, mol_sel, rows, results_dir)
    if summary_panel:
        with st.container(border=True):
            st.subheader(f"{mol_sel} Summary")
            if summary_panel.get("best_accuracy"):
                st.markdown(f"**Best certified accuracy:** {summary_panel['best_accuracy']}")
            if summary_panel.get("lowest_cost"):
                st.markdown(f"**Lowest circuit cost:** {summary_panel['lowest_cost']}")
            if summary_panel.get("best_workflow"):
                st.markdown(f"**Best balanced workflow:** {summary_panel['best_workflow']}")

    # Best mapping / best ansatz
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Best mapping for certified results")
        for ans, mapping_list in result.get("mapping_ranking_by_ansatz", {}).items():
            st.markdown(f"**{ans}:** {' > '.join(mapping_list)}")
    with col2:
        st.subheader("Best ansatz for certified results")
        for m, ans_list in result.get("ansatz_ranking_by_mapping", {}).items():
            st.markdown(f"**{_disp_mapping(m)}:** {' > '.join(ans_list)}")

    # Accuracy vs depth chart
    df = pd.DataFrame(rows)
    df["mapping_disp"] = df["mapping"].map(_disp_mapping)
    df_plot = df[df["gap_ideal"].notna()].copy()
    if not df_plot.empty:
        st.subheader("Cost vs accuracy")
        fig = px.scatter(
            df_plot,
            x="depth",
            y="gap_ideal",
            color="mapping_disp",
            symbol="ansatz_type",
            hover_data=["molecule", "mapping", "ansatz_type"],
            labels={"gap_ideal": "Error (|VQE − exact|)", "depth": "Depth", "mapping_disp": "Mapping"},
        )
        fig.update_traces(marker=dict(size=12))
        st.plotly_chart(fig, use_container_width=True)

    # Certified table
    st.subheader("Certified results table")
    table_cols = ["molecule", "mapping_disp", "ansatz_type", "gap_ideal", "depth", "num_2q_gates"]
    table_cols = [c for c in table_cols if c in df.columns]
    df_display = df[table_cols].rename(columns={
        "mapping_disp": "mapping",
        "gap_ideal": "error",
        "num_2q_gates": "2q",
    })
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    csv_bytes = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv_bytes,
        file_name=f"certified_{mol_sel}.csv",
        mime="text/csv",
        key="cert_csv",
    )
