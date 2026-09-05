"""
Page 2: Smart Routing Console — Multi-Criteria Scoring & Route Optimization.
Clean, modern fintech UI without graph dependencies.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

try:
    from dashboard.api_client import PayRouteAPIClient
    from dashboard.components import (
        render_candidate_comparison_table,
        render_candidate_scores_chart,
        render_explanation_card,
        require_auth,
    )
except ModuleNotFoundError:
    from api_client import PayRouteAPIClient
    from components import (
        render_candidate_comparison_table,
        render_candidate_scores_chart,
        render_explanation_card,
        require_auth,
    )

st.set_page_config(page_title="Smart Routing Console", page_icon="🧠", layout="wide")

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
        background-color: #dbeafe;
        color: #1e40af;
        margin-bottom: 0.5rem;
    }
    .flow-step {
        border-left: 4px solid #3b82f6;
        padding: 0.8rem 1rem;
        background: #f8fafc;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

client = PayRouteAPIClient()
require_auth(client)

st.markdown('<div class="badge-sub">MULTI-OBJECTIVE OPTIMIZATION ENGINE</div>', unsafe_allow_html=True)


st.markdown('<div class="badge-sub">MULTI-OBJECTIVE OPTIMIZATION ENGINE</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">🧠 Smart Routing Console</div>', unsafe_allow_html=True)
st.caption(
    "Deep dive into how PayRoute AI evaluates multi-gateway candidate routes, balances success probabilities "
    "against infrastructure latencies and fees, and assigns automated backup fallbacks."
)

st.markdown("---")

# -------------------------------------------------------------
# 1. Multi-Objective Scoring Weights
# -------------------------------------------------------------
st.markdown("### ⚖️ Multi-Objective Utility Formulation")

with st.container(border=True):
    st.latex(
        r"\text{Utility Score}_i = 0.60 \cdot P(\text{Success}_i) - 0.20 \cdot \widetilde{\text{Latency}}_i - 0.10 \cdot \widetilde{\text{Cost}}_i + 0.10 \cdot \text{Health}_i"
    )

    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_col1.metric("1. Predicted Success", "60% Weight", help="Calibrated Stage-1 GBDT success probability.")
    w_col2.metric("2. Latency Penalty", "20% Weight", help="Normalized candidate latency impact.")
    w_col3.metric("3. Cost / Fee Penalty", "10% Weight", help="Base transaction fee percentage.")
    w_col4.metric("4. Health Bonus", "10% Weight", help="Recent 5-minute rolling success rate telemetry.")

st.markdown("---")

# -------------------------------------------------------------
# 2. Interactive Route Evaluator
# -------------------------------------------------------------
st.markdown("### 🔍 Live Route Candidate Evaluator")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_bank = st.selectbox("Target Issuing Bank", ["SBI", "HDFC", "ICICI", "AXIS"])
    with c2:
        selected_method = st.selectbox("Payment Instrument", ["UPI", "NET_BANKING", "CREDIT_CARD", "DEBIT_CARD"])
    with c3:
        test_amount = st.number_input("Transaction Amount (INR)", min_value=10.0, value=3500.0, step=500.0)

sample_req = {
    "amount": test_amount,
    "currency": "INR",
    "payment_method": selected_method,
    "bank": selected_bank,
    "merchant_category": "ECOMMERCE",
    "hour": 15,
    "device_type": "MOBILE",
    "network_type": "4G",
}

with st.spinner("Evaluating candidate routes across providers..."):
    res = client.recommend_route(sample_req)

if res.get("success"):
    data = res["data"]
    primary = data.get("primary_route")
    fallback = data.get("fallback_route")
    candidates = data.get("candidates", [])

    with st.container(border=True):
        st.markdown("#### 🏆 Optimal Route Selection Summary")
        d1, d2, d3 = st.columns(3)
        d1.success(f"🥇 **Primary Selected**: `{primary}`\n\n**Utility Score**: `{data.get('primary_utility_score', 0.0):.4f}`")
        d2.info(f"🥈 **Backup Fallback**: `{fallback or 'None'}`\n\n**Circuit State**: `{data.get('primary_circuit_state', 'CLOSED')}`")
        d3.metric("Decision Strategy", data.get("routing_strategy", "AI_OPTIMAL"))

    with st.container(border=True):
        st.markdown("#### 📊 Candidate Ranking & Utility Leaderboard")
        render_candidate_scores_chart(candidates)

    with st.container(border=True):
        st.markdown("#### 📋 Candidate Routes Comparison Matrix")
        render_candidate_comparison_table(candidates, selected_route_id=primary)

    # -------------------------------------------------------------
    # 3. Fallback Route Cascading Visualizer (Clean Card Steps)
    # -------------------------------------------------------------
    with st.container(border=True):
        st.markdown("### 🔀 Automated Fallback Cascading Workflow")
        st.caption("How PayRoute AI handles failure resilience dynamically without exposing downtime to the merchant:")

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            with st.container(border=True):
                st.markdown("**Step 1: Primary Dispatch**")
                st.write(f"Payment routed to **`{primary}`** based on highest multi-objective utility score.")
                st.caption("🟢 Expected Latency: ~300ms")

        with fc2:
            with st.container(border=True):
                st.markdown("**Step 2: Circuit & Health Check**")
                st.write("If primary times out (>1500ms) or returns 5xx error, router catches failure instantly.")
                st.caption("⚡ Zero merchant re-entry needed")

        with fc3:
            with st.container(border=True):
                st.markdown("**Step 3: Fallback Cascade**")
                st.write(f"Traffic cascades automatically to **`{fallback or 'Alternate Provider'}`** to salvage payment.")
                st.caption("🛡️ Prevented 198+ failures in benchmark")

    if data.get("explanation"):
        render_explanation_card(data["explanation"])

else:
    st.error(f"Routing Error: {res.get('error')}")

