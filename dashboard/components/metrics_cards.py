"""
Reusable KPI Metrics and Status Badge Components for Streamlit Dashboard.
Clean, modern fintech styling without graph dependencies.
"""

from typing import Optional
import streamlit as st


def render_risk_badge(risk_level: str, p_fail: float) -> None:
    """Renders visual risk level pill banner with progress indicator."""
    pct = p_fail * 100.0
    level = str(risk_level).upper()

    if level == "LOW":
        st.success(f"🟢 **LOW RISK ASSESSMENT** — Failure Probability: **{pct:.1f}%** (Safe to Route)")
    elif level == "MEDIUM":
        st.warning(f"🟡 **MEDIUM RISK ASSESSMENT** — Failure Probability: **{pct:.1f}%** (Monitor Route Latency)")
    else:
        st.error(f"🔴 **HIGH RISK ASSESSMENT** — Failure Probability: **{pct:.1f}%** (Requires Resilient Gateway)")

    # Clean progress bar indicating failure probability
    st.progress(min(1.0, max(0.0, p_fail)), text=f"Failure Risk Score: {pct:.1f}%")


def render_circuit_badge(circuit_state: str) -> str:
    """Returns formatted circuit state badge with emoji and description."""
    state = str(circuit_state).upper()
    if state == "CLOSED":
        return "🟢 CLOSED (Healthy / Normal Traffic)"
    elif state == "HALF_OPEN":
        return "🟡 HALF-OPEN (Testing Probe Traffic)"
    elif state == "OPEN":
        return "🔴 OPEN (Tripped / Traffic Diverted)"
    return f"⚪ {state}"

