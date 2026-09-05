"""
Page 1: Live Payment Simulator — Real-time Payment Risk Prediction, Routing, and Execution.
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
        render_explanation_card,
        render_risk_badge,
        require_auth,
    )
except ModuleNotFoundError:
    from api_client import PayRouteAPIClient
    from components import (
        render_candidate_comparison_table,
        render_explanation_card,
        render_risk_badge,
        require_auth,
    )

st.set_page_config(page_title="Live Payment Simulator", page_icon="⚡", layout="wide")

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
        background-color: #fef3c7;
        color: #92400e;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

client = PayRouteAPIClient()
require_auth(client)

st.markdown('<div class="badge-sub">INTERACTIVE SIMULATION ENVIRONMENT</div>', unsafe_allow_html=True)

st.markdown('<div class="page-title">⚡ Live Payment Simulator</div>', unsafe_allow_html=True)
st.caption(
    "Simulate an incoming transaction, run calibrated ML failure prediction, evaluate candidate route utilities, "
    "and execute payments through simulated gateways with automated telemetry."
)

st.markdown("---")

# -------------------------------------------------------------
# Demo Scenario Presets
# -------------------------------------------------------------
st.markdown("#### 🎯 Quick Simulation Presets")
preset_col1, preset_col2, preset_col3 = st.columns(3)

if "payment_data" not in st.session_state:
    st.session_state.payment_data = {
        "amount": 1500.0,
        "payment_method": "UPI",
        "bank": "HDFC",
        "merchant_category": "FOOD",
        "hour": 14,
        "device_type": "MOBILE",
        "network_type": "5G",
        "customer_age_days": 300,
        "previous_transactions": 25,
        "previous_failed_transactions": 1,
        "previous_attempts": 0,
        "transaction_velocity": 1,
        "is_new_device": 0,
    }

with preset_col1:
    with st.container(border=True):
        st.markdown("**🟢 Healthy Retail UPI**")
        st.caption("Standard low-risk mobile payment on healthy HDFC network.")
        if st.button("Load Preset 1", use_container_width=True):
            st.session_state.payment_data = {
                "amount": 350.0,
                "payment_method": "UPI",
                "bank": "HDFC",
                "merchant_category": "FOOD",
                "hour": 14,
                "device_type": "MOBILE",
                "network_type": "5G",
                "customer_age_days": 450,
                "previous_transactions": 50,
                "previous_failed_transactions": 0,
                "previous_attempts": 0,
                "transaction_velocity": 1,
                "is_new_device": 0,
            }
            st.rerun()

with preset_col2:
    with st.container(border=True):
        st.markdown("**🔴 Degraded Session / Retries**")
        st.caption("High retry count on degraded network with prior failed attempts.")
        if st.button("Load Preset 2", use_container_width=True):
            st.session_state.payment_data = {
                "amount": 18500.0,
                "payment_method": "NET_BANKING",
                "bank": "SBI",
                "merchant_category": "TRAVEL",
                "hour": 3,
                "device_type": "MOBILE",
                "network_type": "2G",
                "customer_age_days": 20,
                "previous_transactions": 2,
                "previous_failed_transactions": 2,
                "previous_attempts": 3,
                "transaction_velocity": 5,
                "is_new_device": 1,
            }
            st.rerun()

with preset_col3:
    with st.container(border=True):
        st.markdown("**🟡 High-Value Card Order**")
        st.caption("High-ticket e-commerce purchase via desktop browser.")
        if st.button("Load Preset 3", use_container_width=True):
            st.session_state.payment_data = {
                "amount": 45000.0,
                "payment_method": "CREDIT_CARD",
                "bank": "ICICI",
                "merchant_category": "ECOMMERCE",
                "hour": 20,
                "device_type": "DESKTOP",
                "network_type": "WIFI",
                "customer_age_days": 600,
                "previous_transactions": 40,
                "previous_failed_transactions": 3,
                "previous_attempts": 1,
                "transaction_velocity": 2,
                "is_new_device": 0,
            }
            st.rerun()

# -------------------------------------------------------------
# Payment Context Input Form
# -------------------------------------------------------------
p = st.session_state.payment_data

with st.container(border=True):
    st.markdown("#### 📝 Transaction Parameters")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        amount = st.number_input("Amount (INR)", min_value=1.0, value=float(p.get("amount", 1500.0)), step=100.0)
        payment_method = st.selectbox(
            "Payment Method",
            ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
            index=["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"].index(p.get("payment_method", "UPI")),
        )
        bank = st.selectbox(
            "Issuing Bank",
            ["HDFC", "SBI", "ICICI", "AXIS"],
            index=["HDFC", "SBI", "ICICI", "AXIS"].index(p.get("bank", "HDFC")),
        )

    with col_b:
        merchant_category = st.selectbox(
            "Merchant Category",
            ["ECOMMERCE", "FOOD", "TRAVEL", "UTILITIES", "ENTERTAINMENT", "HEALTHCARE", "EDUCATION"],
            index=["ECOMMERCE", "FOOD", "TRAVEL", "UTILITIES", "ENTERTAINMENT", "HEALTHCARE", "EDUCATION"].index(p.get("merchant_category", "FOOD")),
        )
        network_type = st.selectbox(
            "Network Connection",
            ["5G", "4G", "WIFI", "3G", "2G"],
            index=["5G", "4G", "WIFI", "3G", "2G"].index(p.get("network_type", "4G")),
        )
        device_type = st.selectbox(
            "Device Type",
            ["MOBILE", "DESKTOP", "TABLET"],
            index=["MOBILE", "DESKTOP", "TABLET"].index(p.get("device_type", "MOBILE")),
        )

    with col_c:
        previous_attempts = st.slider("Immediate Retries in Session", 0, 4, int(p.get("previous_attempts", 0)))
        previous_failed = st.number_input("Past Failed Transactions", 0, 50, int(p.get("previous_failed_transactions", 0)))
        is_new_device = st.checkbox("Unrecognized / New Device Fingerprint", value=bool(p.get("is_new_device", 0)))

# Prepare current payment request dictionary
current_request = {
    "amount": amount,
    "currency": "INR",
    "payment_method": payment_method,
    "bank": bank,
    "merchant_category": merchant_category,
    "device_type": device_type,
    "network_type": network_type,
    "hour": 14,
    "day_of_week": 2,
    "customer_age_days": int(p.get("customer_age_days", 180)),
    "previous_transactions": int(p.get("previous_transactions", 10)),
    "previous_failed_transactions": int(previous_failed),
    "previous_attempts": int(previous_attempts),
    "transaction_velocity": int(p.get("transaction_velocity", 1)),
    "is_new_device": 1 if is_new_device else 0,
}

st.markdown("---")

# -------------------------------------------------------------
# Action Buttons (Predict, Route, Execute)
# -------------------------------------------------------------
st.markdown("#### 🚀 Execution Pipeline")
btn_col1, btn_col2, btn_col3 = st.columns(3)

with btn_col1:
    btn_predict = st.button("🔍 1. Predict Failure Risk", use_container_width=True, type="secondary")

with btn_col2:
    btn_route = st.button("🧠 2. Find Best Route", use_container_width=True, type="primary")

with btn_col3:
    btn_execute = st.button("💳 3. Execute Simulated Payment", use_container_width=True, type="secondary")

# -------------------------------------------------------------
# 1. Failure Prediction Results
# -------------------------------------------------------------
if btn_predict:
    with st.spinner("Evaluating Stage-1 ML Failure Predictor & Diagnoser..."):
        res = client.predict_failure(current_request)

    if res.get("success"):
        data = res["data"]
        p_fail = data["failure_probability"]
        p_succ = data["success_probability"]
        risk_level = data["risk_level"]
        reason = data.get("predicted_failure_reason", "N/A")

        with st.container(border=True):
            st.markdown("### 📊 ML Failure Risk Assessment")
            render_risk_badge(risk_level, p_fail)

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Predicted Failure Risk", f"{p_fail*100:.1f}%")
            kpi2.metric("Expected Success Prob", f"{p_succ*100:.1f}%")
            kpi3.metric("Decision Threshold (T*)", f"{data['decision_threshold']:.2f}")
            kpi4.metric("Diagnosis Reason", reason)

        # Render Explanation Cards (no matplotlib plots)
        explanation_payload = {
            "top_risk_contributors": data.get("top_risk_factors", []),
            "top_protective_factors": data.get("top_protective_factors", []),
        }
        render_explanation_card(explanation_payload)
    else:
        st.error(f"Prediction Error: {res.get('error')}")

# -------------------------------------------------------------
# 2. Route Recommendation Results
# -------------------------------------------------------------
if btn_route:
    with st.spinner("Calculating multi-objective utility scores across candidate routes..."):
        res = client.recommend_route(current_request)

    if res.get("success"):
        data = res["data"]
        primary = data.get("primary_route")
        fallback = data.get("fallback_route")
        strategy = data.get("routing_strategy")
        util = data.get("primary_utility_score", 0.0)

        with st.container(border=True):
            st.markdown("### 🥇 Recommended Payment Route Assignment")

            rec_col1, rec_col2, rec_col3 = st.columns(3)
            with rec_col1:
                st.success(f"**Primary Route**: `{primary}`\n\n**Utility Score**: `{util:.4f}`")
            with rec_col2:
                st.info(f"**Fallback Route**: `{fallback or 'None'}`\n\n**Strategy**: `{strategy}`")
            with rec_col3:
                st.metric("Expected Primary Success", f"{data.get('primary_predicted_success_prob', 0.0)*100:.1f}%")

        with st.container(border=True):
            st.markdown("#### 📋 Candidate Routes Comparison Matrix")
            render_candidate_comparison_table(data.get("candidates", []), selected_route_id=primary)

        if data.get("explanation"):
            render_explanation_card(data["explanation"])
    else:
        st.error(f"Routing Error: {res.get('error')}")

# -------------------------------------------------------------
# 3. Simulated Transaction Execution Results
# -------------------------------------------------------------
if btn_execute:
    with st.spinner("Executing transaction through PayRoute AI & recording telemetry..."):
        res = client.execute_transaction(payment_request=current_request, simulate_outage=False)

    if res.get("success"):
        data = res["data"]
        status_label = data["status"]
        route = data.get("selected_route")
        latency = data.get("latency_ms")
        reason = data.get("failure_reason")

        with st.container(border=True):
            st.markdown("### 💳 Simulated Transaction Receipt")
            if status_label == "SUCCESS":
                st.success(
                    f"✅ **PAYMENT COMPLETED SUCCESSFULLY**\n\n"
                    f"- **Routed Through**: `{route}`\n"
                    f"- **Observed Latency**: `{latency} ms`\n"
                    f"- **Transaction ID**: `{data['transaction_id']}` (Audited to SQLite)"
                )
            else:
                st.error(
                    f"❌ **PAYMENT ATTEMPT FAILED**\n\n"
                    f"- **Routed Through**: `{route}`\n"
                    f"- **Failure Reason**: `{reason}`\n"
                    f"- **Observed Latency**: `{latency} ms`\n"
                    f"- **Circuit State**: `{data.get('circuit_state', 'CLOSED')}`"
                )
    else:
        st.error(f"Execution Error: {res.get('error')}")

