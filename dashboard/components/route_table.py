"""
Formatted Tables for Candidate Routes and Gateway Telemetry.
Clean, modern fintech styling without graph dependencies.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st


def render_candidate_comparison_table(
    candidates: List[Dict[str, Any]],
    selected_route_id: Optional[str] = None,
) -> None:
    """Renders formatted candidate comparison dataframe."""
    if not candidates:
        st.info("No candidates to display.")
        return

    rows = []
    for c in candidates:
        r_id = c.get("route_id", "")
        is_sel = "⭐ " if r_id == selected_route_id else ""
        c_state = c.get("circuit_state", "CLOSED")
        state_icon = "🟢" if c_state == "CLOSED" else ("🟡" if c_state == "HALF_OPEN" else "🔴")

        rows.append({
            "Selection": f"{is_sel}{r_id}",
            "Gateway Provider": c.get("gateway", ""),
            "P(Fail)": f"{c.get('failure_probability', 0.0)*100:.1f}%",
            "P(Success)": f"{c.get('success_probability', 0.0)*100:.1f}%",
            "Expected Latency": f"{c.get('expected_latency_ms', 0)} ms",
            "5-Min Health": f"{c.get('rolling_health', 0.0)*100:.1f}%",
            "Fee %": f"{c.get('base_fee_pct', 0.0):.2f}%",
            "Utility Score": f"{c.get('utility_score', 0.0):.4f}",
            "Circuit": f"{state_icon} {c_state}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_gateway_health_table(routes: List[Dict[str, Any]]) -> None:
    """Renders real-time gateway health table."""
    if not routes:
        st.info("No gateway health records available.")
        return

    rows = []
    for r in routes:
        state = r.get("circuit_state", "CLOSED")
        status_icon = "🟢" if state == "CLOSED" else ("🟡" if state == "HALF_OPEN" else "🔴")
        rows.append({
            "Route ID": r.get("route_id", ""),
            "Circuit State": f"{status_icon} {state}",
            "Rolling Success": f"{r.get('rolling_success_rate', 0.0)*100:.1f}%",
            "Rolling Failure": f"{r.get('rolling_failure_rate', 0.0)*100:.1f}%",
            "Median Latency": f"{r.get('median_latency_ms', 0):.0f} ms",
            "Total Ingested": f"{r.get('total_transactions', 0):,}",
            "Total Failed": f"{r.get('total_failures', 0):,}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

