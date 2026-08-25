"""Phase 16: Home screen — three primary paths."""
from __future__ import annotations

import streamlit as st


def _go_page(page: str) -> None:
    st.session_state["page"] = page


def render_home() -> None:
    """Render the landing screen with three cards."""
    st.markdown("## Welcome to qencode-db")
    st.caption("Benchmark quantum algorithms. Compare encodings and ansätze. Make data-driven decisions.")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.subheader("Standard Suite")
            st.markdown(
                "Browse **certified benchmark results** from the official benchmark suite."
            )
            st.button(
                "Open Standard Suite →",
                key="nav_standard",
                use_container_width=True,
                on_click=_go_page,
                args=("standard_suite",),
            )

    with col2:
        with st.container(border=True):
            st.subheader("Workflows")
            st.markdown(
                "Compare named VQE workflow strategies across molecules."
            )
            st.button(
                "Open Workflows →",
                key="nav_workflows",
                use_container_width=True,
                on_click=_go_page,
                args=("workflows",),
            )

    with col3:
        with st.container(border=True):
            st.subheader("Explore")
            st.markdown(
                "Inspect benchmark tables, charts, and tradeoffs."
            )
            st.button(
                "Open Explore →",
                key="nav_explore",
                use_container_width=True,
                on_click=_go_page,
                args=("explore",),
            )
