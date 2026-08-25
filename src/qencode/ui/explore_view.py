"""Phase 16: Explore view — tables, charts, advanced filters."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from qencode.comparison_engine import (
    MAPPING_DISPLAY,
    full_comparison,
    list_molecules,
    sync_from_dir,
)


@st.cache_data(ttl=60)
def _load_data(
    sqlite_path: Path,
    db_dir: Path,
    molecule: Optional[str],
) -> Tuple[List[dict], Dict]:
    """Load and sync data; return (rows, ranking). Cached 60s."""
    sync_from_dir(db_dir, sqlite_path)
    molecules = list_molecules(sqlite_path)
    rows_all: List[dict] = []
    ranking: Dict = {}
    for mol in molecules:
        if molecule and mol != molecule:
            continue
        try:
            r = full_comparison(sqlite_path, mol, variant="default", basis="sto3g")
            rows_all.extend(r["rows"])
            ranking[mol] = {
                "mapping_by_ansatz": r["mapping_ranking_by_ansatz"],
                "ansatz_by_mapping": r["ansatz_ranking_by_mapping"],
            }
        except Exception:
            pass
    return rows_all, ranking


def _disp_mapping(m: str) -> str:
    return MAPPING_DISPLAY.get(m, m)


def render_explore(db_dir: Path, sqlite_path: Path) -> None:
    """Render Explore page: full table, charts, advanced filters."""
    st.header("Explore")
    st.caption("Inspect benchmark tables, charts, and tradeoffs.")

    rows, ranking = _load_data(sqlite_path, db_dir, None)
    molecules = ["All"] + sorted({r["molecule"] for r in rows if r.get("molecule")})

    # Filters
    with st.sidebar:
        st.subheader("Filters")
        mol_sel = st.selectbox("Molecule", molecules, index=0, key="explore_mol")
        trust_sel = st.selectbox(
            "Trust",
            ["All", "Validated", "Certified"],
            index=0,
            help="Filter by result trust level",
            key="explore_trust",
        )
        mapping_filter = st.selectbox(
            "Mapping",
            ["All"] + list(MAPPING_DISPLAY.values()),
            index=0,
            key="explore_mapping",
        )
        ansatz_filter = st.selectbox(
            "Ansatz",
            ["All", "uccsd", "hardware_efficient"],
            index=0,
            key="explore_ansatz",
        )

    if mol_sel != "All":
        rows = [r for r in rows if r.get("molecule") == mol_sel]
        ranking = {k: v for k, v in ranking.items() if k == mol_sel}
    if trust_sel == "Validated":
        rows = [r for r in rows if (r.get("trust_level") or "experimental") in ("validated", "certified")]
    elif trust_sel == "Certified":
        rows = [r for r in rows if (r.get("trust_level") or "experimental") == "certified"]
    if mapping_filter != "All":
        rev_disp = {v: k for k, v in MAPPING_DISPLAY.items()}
        m = rev_disp.get(mapping_filter, mapping_filter)
        rows = [r for r in rows if r.get("mapping") == m]
    if ansatz_filter != "All":
        rows = [r for r in rows if r.get("ansatz_type") == ansatz_filter]

    if not rows:
        st.warning("No benchmark data for these filters.")
        return

    df = pd.DataFrame(rows)
    df["mapping_disp"] = df["mapping"].map(_disp_mapping)
    df_plot = df[df["gap_ideal"].notna()].copy()

    # Table
    st.subheader("Benchmark table")
    table_cols = ["molecule", "mapping_disp", "ansatz_type", "vqe_energy", "exact_energy", "gap_ideal", "depth", "num_2q_gates", "trust_level"]
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
        file_name="benchmark_table.csv",
        mime="text/csv",
        key="explore_csv",
    )

    # Ranking
    st.subheader("Ranking")
    for mol, rk in ranking.items():
        if mol_sel != "All" and mol != mol_sel:
            continue
        st.markdown(f"**Best mapping for {mol}**")
        for ans, mapping_list in rk["mapping_by_ansatz"].items():
            st.markdown(f"  {ans}: {' > '.join(mapping_list)}")
        st.markdown(f"**Best ansatz for {mol}**")
        for m, ans_list in rk["ansatz_by_mapping"].items():
            st.markdown(f"  {_disp_mapping(m)}: {' > '.join(ans_list)}")

    # Charts
    st.subheader("Charts")
    if df_plot.empty:
        st.info("No rows with error data for charts.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Cost vs accuracy**")
            fig1 = px.scatter(
                df_plot,
                x="depth",
                y="gap_ideal",
                color="mapping_disp",
                symbol="ansatz_type",
                hover_data=["molecule", "mapping", "ansatz_type"],
                labels={"gap_ideal": "Error", "depth": "Depth", "mapping_disp": "Mapping"},
            )
            fig1.update_traces(marker=dict(size=12))
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.markdown("**Mapping comparison**")
            fig2 = px.bar(
                df_plot,
                x="mapping_disp",
                y="gap_ideal",
                color="ansatz_type",
                barmode="group",
                labels={"gap_ideal": "Error", "mapping_disp": "Mapping"},
            )
            st.plotly_chart(fig2, use_container_width=True)

        df_noise = df_plot[df_plot["noise_sensitivity"].notna()]
        if not df_noise.empty:
            st.markdown("**Noise impact**")
            fig3 = px.bar(
                df_noise,
                x="mapping_disp",
                y="noise_sensitivity",
                color="ansatz_type",
                barmode="group",
                labels={"noise_sensitivity": "Noise sensitivity", "mapping_disp": "Mapping"},
            )
            st.plotly_chart(fig3, use_container_width=True)
