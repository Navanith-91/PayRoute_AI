"""
Page 3: Gateway Health Monitor — Real-Time Circuit Breakers & Outage Degradation Simulator.
Clean, modern fintech UI without graph dependencies.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

try:
    from dashboard.api_client import PayRouteAPIClient
    from dashboard.components import render_gateway_health_table, require_auth
except ModuleNotFoundError:
    from api_client import PayRouteAPIClient
    from components import render_gateway_health_table, require_auth

st.set_page_config(page_title="Gateway Health Monitor", page_icon="🩺", layout="wide")

st.markdown(
    """
    <style>
    .page-title { font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; }
    .badge-sub {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #fce7f3;
        color: #9d174d;
        margin-bottom: 0.5rem;
    }
    .health-card {
        border-radius: 8px;
        padding: 0.8rem;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

client = PayRouteAPIClient()
require_auth(client)

st.markdown('<div class="badge-sub">INFRASTRUCTURE TELEMETRY & RESILIENCE</div>', unsafe_allow_html=True)

st.markdown('<div class="page-title">🩺 Gateway Health Monitor</div>', unsafe_allow_html=True)
st.caption(
    "Monitor live rolling provider telemetry, detect degraded routes, and observe automatic "
    "3-state circuit breaker state transitions (CLOSED ➔ OPEN ➔ HALF_OPEN)."
)

st.markdown("---")

# Refresh Control Bar
rc1, rc2 = st.columns([6, 1])
with rc1:
    st.markdown("### 📡 Live Route Health Telemetry")
with rc2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# -------------------------------------------------------------
# 1. Real-Time Telemetry Grid
# -------------------------------------------------------------
with st.spinner("Fetching real-time gateway health and circuit states..."):
    res = client.get_gateway_health()

if res.get("success"):
    routes_data = res["data"].get("routes", [])

    # Overview Metrics Row
    if routes_data:
        total_routes = len(routes_data)
        healthy_routes = sum(1 for r in routes_data if r.get("circuit_state") == "CLOSED")
        tripped_routes = sum(1 for r in routes_data if r.get("circuit_state") == "OPEN")
        testing_routes = sum(1 for r in routes_data if r.get("circuit_state") == "HALF_OPEN")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monitored Routes", f"{total_routes}")
        m2.metric("🟢 Healthy (CLOSED)", f"{healthy_routes}")
        m3.metric("🔴 Tripped (OPEN)", f"{tripped_routes}")
        m4.metric("🟡 Testing (HALF_OPEN)", f"{testing_routes}")

    # Render Clean Table
    render_gateway_health_table(routes_data)

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. Route Health Telemetry Cards (Clean Card Grid)
    # -------------------------------------------------------------
    st.markdown("### 📊 Route-by-Route Reliability Breakdown")

    if routes_data:
        for i in range(0, len(routes_data), 2):
            c_left, c_right = st.columns(2)
            
            # Left Card
            r_left = routes_data[i]
            with c_left:
                with st.container(border=True):
                    st_icon = "🟢" if r_left.get("circuit_state") == "CLOSED" else ("🟡" if r_left.get("circuit_state") == "HALF_OPEN" else "🔴")
                    st.markdown(f"**{st_icon} {r_left.get('route_id')}**")
                    sr = float(r_left.get("rolling_success_rate", 0.0))
                    st.progress(sr, text=f"Success Rate: {sr*100:.1f}%")
                    
                    sub1, sub2, sub3 = st.columns(3)
                    sub1.metric("Latency", f"{r_left.get('median_latency_ms', 0):.0f} ms")
                    sub2.metric("Circuit", f"{r_left.get('circuit_state', 'CLOSED')}")
                    sub3.metric("Failures", f"{r_left.get('total_failures', 0)}")

            # Right Card (if available)
            if i + 1 < len(routes_data):
                r_right = routes_data[i + 1]
                with c_right:
                    with st.container(border=True):
                        st_icon2 = "🟢" if r_right.get("circuit_state") == "CLOSED" else ("🟡" if r_right.get("circuit_state") == "HALF_OPEN" else "🔴")
                        st.markdown(f"**{st_icon2} {r_right.get('route_id')}**")
                        sr2 = float(r_right.get("rolling_success_rate", 0.0))
                        st.progress(sr2, text=f"Success Rate: {sr2*100:.1f}%")
                        
                        sub1, sub2, sub3 = st.columns(3)
                        sub1.metric("Latency", f"{r_right.get('median_latency_ms', 0):.0f} ms")
                        sub2.metric("Circuit", f"{r_right.get('circuit_state', 'CLOSED')}")
                        sub3.metric("Failures", f"{r_right.get('total_failures', 0)}")

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. Interactive Outage & Degradation Simulator
    # -------------------------------------------------------------
    st.markdown("### 💥 Interactive Outage & Circuit Breaker Simulator")
    st.caption(
        "Inject consecutive synthetic failures into a specific payment route to trip its circuit breaker from "
        "**CLOSED (🟢)** to **OPEN (🔴)**, and observe how traffic is safely diverted in real-time."
    )

    with st.container(border=True):
        outage_col1, outage_col2 = st.columns(2)

        with outage_col1:
            target_route = st.selectbox(
                "Select Route to Degrade",
                [r["route_id"] for r in routes_data],
                index=0,
            )
            failures_to_inject = st.slider("Consecutive Failures to Inject", min_value=5, max_value=30, value=22)

        with outage_col2:
            st.markdown("**Simulation Trigger Actions**")
            btn_trip = st.button("🔴 1. Inject Outage & Trip Circuit", type="primary", use_container_width=True)
            btn_recover = st.button("🟢 2. Send Successful Recovery Probe", use_container_width=True)

        if btn_trip:
            with st.spinner(f"Injecting {failures_to_inject} severe failures on {target_route}..."):
                sample_bank = target_route.split("_")[1] if len(target_route.split("_")) > 1 else "HDFC"
                for _ in range(failures_to_inject):
                    client.execute_transaction(
                        payment_request={
                            "amount": 1000.0,
                            "payment_method": "UPI",
                            "bank": sample_bank,
                            "merchant_category": "ECOMMERCE",
                        },
                        preferred_route=target_route,
                        simulate_outage=True,
                    )
            st.error(f"🚨 Outage Injected! Ingested {failures_to_inject} failures on `{target_route}`. Circuit is now **OPEN**.")
            st.rerun()

        if btn_recover:
            with st.spinner(f"Sending recovery probe to {target_route}..."):
                sample_bank = target_route.split("_")[1] if len(target_route.split("_")) > 1 else "HDFC"
                client.execute_transaction(
                    payment_request={
                        "amount": 500.0,
                        "payment_method": "UPI",
                        "bank": sample_bank,
                        "merchant_category": "FOOD",
                    },
                    preferred_route=target_route,
                    simulate_outage=False,
                )
            st.success(f"✅ Recovery Probe Sent to `{target_route}`.")
            st.rerun()

else:
    st.error(f"Failed to fetch health telemetry: {res.get('error')}")

