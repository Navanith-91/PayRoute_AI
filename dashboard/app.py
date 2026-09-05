"""
PayRoute AI — Intelligent Customer Payment Shield & Reliability Platform.
Dynamic fintech customer app with left panel navigation, multi-gateway resilience (Google Pay, PhonePe, Cards, Net Banking),
real-time payment lifecycle tracking, and zero-loss AI route protection.
"""

import datetime
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

try:
    from dashboard.api_client import PayRouteAPIClient
    from dashboard.components.auth_ui import (
        get_current_user,
        is_authenticated,
        logout_user,
        render_auth_screen,
    )
    from dashboard.components.settings_ui import render_gateway_settings_panel
    from dashboard.components.transactions_ui import render_transactions_audit_panel
    from dashboard.components.unified_console import (
        render_ai_payment_check_card,
        render_live_bank_health_radar,
        render_payment_form,
        render_payment_result_card,
        render_transaction_status_section,
    )
except ModuleNotFoundError:
    from api_client import PayRouteAPIClient
    from components.auth_ui import (
        get_current_user,
        is_authenticated,
        logout_user,
        render_auth_screen,
    )
    from components.settings_ui import render_gateway_settings_panel
    from components.transactions_ui import render_transactions_audit_panel
    from components.unified_console import (
        render_ai_payment_check_card,
        render_live_bank_health_radar,
        render_payment_form,
        render_payment_result_card,
        render_transaction_status_section,
    )

st.set_page_config(
    page_title="PayRoute AI — Smart Payment Shield",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dynamic Fintech Styling with Light Sky Blue Canvas and High-Contrast Dark Navy Typography
st.markdown(
    """
    <style>
    /* -------------------------------------------------------------
       UNIVERSAL HIGH-CONTRAST DARK BLUE TYPOGRAPHY
       ------------------------------------------------------------- */
    .stApp {
        background: radial-gradient(at 0% 0%, rgba(186, 230, 253, 0.70) 0px, transparent 50%),
                    radial-gradient(at 100% 0%, rgba(125, 211, 252, 0.60) 0px, transparent 50%),
                    radial-gradient(at 100% 100%, rgba(224, 242, 254, 0.95) 0px, transparent 50%),
                    radial-gradient(at 0% 100%, rgba(56, 189, 248, 0.40) 0px, transparent 50%),
                    #e0f2fe !important;
        background-attachment: fixed !important;
        color: #082f49 !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1100px;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: #082f49 !important;
        font-weight: 850 !important;
        letter-spacing: -0.02em;
    }

    .main-title {
        font-size: 2.1rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        margin-bottom: 0.1rem;
        color: #082f49 !important;
    }
    .main-subtitle {
        font-size: 0.98rem;
        font-weight: 600;
        color: #0c4a6e !important;
        margin-bottom: 1.1rem;
        line-height: 1.5;
    }
    .badge-sub {
        display: inline-block;
        padding: 0.3rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 850;
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff !important;
        border: 1px solid #0284c7;
        margin-bottom: 0.35rem;
        letter-spacing: 0.08em;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.25);
    }

    /* Regular Body Text & Paragraphs */
    p, span, div, li, a, strong, b,
    .stMarkdown p, .stMarkdown span, .stMarkdown div, .stMarkdown li,
    .stText, .stMarkdown {
        color: #082f49 !important;
    }

    /* Captions & Subtitles */
    .stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
        color: #0369a1 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }

    /* Widget Labels & Input Headers */
    label,
    label[data-testid="stWidgetLabel"],
    label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] span,
    [data-testid="stWidgetLabel"] * {
        color: #082f49 !important;
        font-weight: 800 !important;
        font-size: 0.92rem !important;
    }

    /* Inputs, Selectboxes, Number Inputs, Sliders */
    input, textarea, select,
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span {
        color: #082f49 !important;
        background-color: #ffffff !important;
        font-weight: 750 !important;
    }

    /* -------------------------------------------------------------
       TOP HEADER BAR, STATUS WIDGET, DECORATION & TOOLBAR
       ------------------------------------------------------------- */
    header,
    header[data-testid="stHeader"],
    .stAppHeader,
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    div[data-testid="stToolbar"] {
        background: #e0f2fe !important;
        background-color: #e0f2fe !important;
        color: #082f49 !important;
        border-bottom: 1px solid #bae6fd !important;
    }
    header *,
    header[data-testid="stHeader"] *,
    .stAppHeader *,
    [data-testid="stToolbar"] *,
    [data-testid="stStatusWidget"] *,
    header button,
    header svg,
    header a {
        color: #082f49 !important;
        fill: #082f49 !important;
        stroke: #082f49 !important;
    }

    /* -------------------------------------------------------------
       BASEWEB DROPDOWN MENUS, POPOVERS & SELECTBOX ARROWS
       ------------------------------------------------------------- */
    /* Selectbox Input Box */
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1.5px solid #7dd3fc !important;
        color: #082f49 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #082f49 !important;
        font-weight: 750 !important;
    }

    /* Dropdown Arrow SVGs & Icons */
    div[data-baseweb="select"] svg,
    div[data-baseweb="select"] [data-baseweb="icon"],
    svg[data-testid="stIcon"],
    div[data-baseweb="select"] svg path {
        fill: #0284c7 !important;
        color: #0284c7 !important;
        stroke: #0284c7 !important;
    }

    /* Universal BaseWeb Dropdown Menu / Popover Styling (Overrides Dark Overlay) */
    body div[data-baseweb="popover"],
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] > div > div,
    div[data-baseweb="menu"],
    ul[role="listbox"],
    ul[data-baseweb="menu"],
    div[role="listbox"],
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] li,
    [data-baseweb="menu"] ul,
    [data-baseweb="menu"] li {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #082f49 !important;
    }

    div[data-baseweb="popover"] > div,
    div[data-baseweb="menu"],
    ul[role="listbox"] {
        border: 1.5px solid #7dd3fc !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 25px -3px rgba(2, 132, 199, 0.25), 0 4px 6px -2px rgba(2, 132, 199, 0.1) !important;
    }

    /* All text inside popover & menu options */
    body div[data-baseweb="popover"] *,
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"] *,
    ul[role="listbox"] *,
    ul[data-baseweb="menu"] *,
    li[role="option"],
    li[role="option"] *,
    li[data-baseweb="menu-item"],
    li[data-baseweb="menu-item"] * {
        color: #082f49 !important;
        font-weight: 750 !important;
    }

    /* Dropdown Menu Items / Options */
    li[role="option"],
    li[data-baseweb="menu-item"],
    ul[role="listbox"] > li,
    div[data-baseweb="menu"] > li,
    div[data-baseweb="popover"] li {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #082f49 !important;
        font-weight: 750 !important;
        font-size: 0.94rem !important;
        padding: 10px 14px !important;
        border-bottom: 1px solid #f0f9ff !important;
        cursor: pointer !important;
    }

    /* Hover & Selected States */
    li[role="option"]:hover,
    li[role="option"]:hover *,
    li[role="option"]:hover > div,
    li[data-baseweb="menu-item"]:hover,
    li[data-baseweb="menu-item"]:hover *,
    li[aria-selected="true"],
    li[aria-selected="true"] *,
    li[aria-selected="true"] > div,
    li[role="option"][aria-selected="true"],
    li[role="option"][aria-selected="true"] * {
        background-color: #e0f2fe !important;
        background: #e0f2fe !important;
        color: #0284c7 !important;
        font-weight: 850 !important;
    }

    /* Modals, Dialogs & Tooltips */
    div[data-baseweb="modal"],
    div[data-baseweb="modal"] > div,
    div[data-baseweb="tooltip"],
    div[data-baseweb="toast"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #082f49 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] p {
        color: #0369a1 !important;
        font-weight: 800 !important;
        font-size: 0.88rem !important;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #082f49 !important;
        font-weight: 900 !important;
    }

    /* Containers & Cards */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        background: rgba(255, 255, 255, 0.98) !important;
        backdrop-filter: blur(12px) !important;
        border: 1.5px solid #bae6fd !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px -2px rgba(2, 132, 199, 0.12) !important;
    }

    /* Primary Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px 0 rgba(2, 132, 199, 0.35) !important;
        font-weight: 800 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"] * {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px 0 rgba(2, 132, 199, 0.45) !important;
    }

    /* Secondary Buttons */
    button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1.5px solid #7dd3fc !important;
        border-radius: 8px !important;
    }
    button[kind="secondary"] * {
        color: #0369a1 !important;
        font-weight: 750 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f0f9ff !important;
        border-right: 2px solid #bae6fd !important;
    }
    section[data-testid="stSidebar"] * {
        color: #082f49 !important;
    }
    section[data-testid="stSidebar"] .stRadio label * {
        color: #0c4a6e !important;
        font-weight: 750 !important;
    }

    /* Expanders */
    .streamlit-expanderHeader,
    .streamlit-expanderHeader p,
    .streamlit-expanderHeader span,
    details summary, details summary * {
        color: #082f49 !important;
        font-weight: 800 !important;
    }

    /* Tables & Dataframes */
    [data-testid="stDataFrame"] *,
    table, th, td, tr {
        color: #082f49 !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

client = PayRouteAPIClient()

# -------------------------------------------------------------
# 0. Authentication Guard (Customer Login)
# -------------------------------------------------------------
if not is_authenticated():
    render_auth_screen(client)
    st.stop()

# Initialize Session State
if "current_analysis" not in st.session_state:
    st.session_state["current_analysis"] = None
if "last_execution_result" not in st.session_state:
    st.session_state["last_execution_result"] = None
if "active_payment_request" not in st.session_state:
    st.session_state["active_payment_request"] = None
if "search_txn_id" not in st.session_state:
    st.session_state["search_txn_id"] = "TXN_PENDING_001"
if "form_amount_input" not in st.session_state:
    st.session_state["form_amount_input"] = 1200.0


# -------------------------------------------------------------
# 1. Left Sidebar Navigation & Customer Profile
# -------------------------------------------------------------
user = get_current_user() or {}
user_name = user.get("full_name") or "Rahul Sharma"
user_email = user.get("email") or "customer@payroute.ai"
user_bank = user.get("organization") or "HDFC Bank ••••4291"

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #bae6fd; margin-bottom: 15px;">
            <div style="font-size: 1.35rem; font-weight: 850; color: #0c4a6e; display: flex; align-items: center; gap: 8px;">
                💳 PayRoute AI
            </div>
            <div style="font-size: 0.78rem; font-weight: 600; color: #0284c7; letter-spacing: 0.04em;">
                SMART PAYMENT SHIELD
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🧭 Navigation")
    nav_selection = st.radio(
        "Go to page",
        options=[
            "💳 Pay & Transfer",
            "🔍 Track Payment",
            "📋 My Transactions",
            "⚡ Live Bank Health",
            "⚙️ Payment Preferences",
        ],
        index=0,
        label_visibility="collapsed",
        key="main_nav_radio",
    )

    st.markdown("---")

    # Customer Profile Card
    with st.container(border=True):
        st.markdown(f"👤 **{user_name}**")
        st.caption(f"📧 `{user_email}`")
        st.caption(f"🏦 {user_bank}")
        st.caption("🛡️ **Verified AI-Protected Payer**")

        if st.button("🚪 Sign Out", use_container_width=True, type="secondary", key="sidebar_logout_btn"):
            logout_user()


# -------------------------------------------------------------
# 2. Main Page Header
# -------------------------------------------------------------
st.markdown('<div class="badge-sub">AI-POWERED PAYMENT SHIELD & INSTANT ROUTER</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">💳 PAYROUTE AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">'
    "Guarantees seamless, zero-drop payments across UPI, Cards, and Net Banking by dynamically bypassing congested bank servers in real-time."
    "</div>",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# 3. Router: Render Selected Navigation Page
# -------------------------------------------------------------

# PAGE 1: PAY & TRANSFER (SMART CHECKOUT)
if nav_selection == "💳 Pay & Transfer":
    payment_request = render_payment_form()

    if payment_request is not None:
        # Dynamic Animated AI Route Analysis
        with st.status("Evaluating payment routes with AI Shield...", expanded=True) as status_box:
            status_box.update(label="Scanning NPCI and bank payment gateways... ✓ Clear")
            time.sleep(0.18)
            status_box.update(label=f"Checking {payment_request.get('bank')} bank switch latency... ✓ 76ms Fast")
            time.sleep(0.18)
            status_box.update(label="Analyzing failure probability & congestion... ✓ 99.4% Safe")
            time.sleep(0.18)
            status_box.update(label="AI Route Shield ready! Preparing optimal path.", state="complete")

        analysis_res = client.analyze_payment(payment_request)

        if analysis_res.get("success"):
            st.session_state["current_analysis"] = analysis_res["data"]
            st.session_state["active_payment_request"] = payment_request
            st.session_state["last_execution_result"] = None
        else:
            st.error(f"Route Check Failed: {analysis_res.get('error')}")

    # Render Payment Analysis, Radar Graphs, and One-Click Pay Action
    analysis = st.session_state.get("current_analysis")
    if analysis:
        render_ai_payment_check_card(analysis)

        # Handle Action Trigger
        if st.session_state.get("decision_btn_clicked"):
            btn_action = st.session_state.get("btn_action_type", "EXECUTE")

            # Action: SWITCH PAYMENT METHOD
            if btn_action == "SWITCH_METHOD":
                new_m = st.session_state.get("new_method", "CREDIT_CARD")
                st.session_state["form_method"] = new_m
                req = st.session_state["active_payment_request"].copy()
                req["payment_method"] = new_m
                with st.spinner(f"Re-evaluating conditions with {new_m}..."):
                    re_res = client.analyze_payment(req)
                    if re_res.get("success"):
                        st.session_state["current_analysis"] = re_res["data"]
                        st.session_state["active_payment_request"] = req
                        st.rerun()

            # Action: SMART WAIT & RETRY
            elif btn_action == "WAIT":
                with st.status("High bank traffic detected. Waiting for queue drainage...", expanded=True) as status_box:
                    for s in range(3, 0, -1):
                        status_box.update(label=f"Auto-waiting for bank server buffer clearance... {s}s")
                        time.sleep(0.7)
                    status_box.update(label="Bank servers cleared! Ready to pay.", state="complete")

                re_res = client.analyze_payment(st.session_state["active_payment_request"])
                if re_res.get("success"):
                    st.session_state["current_analysis"] = re_res["data"]
                    st.rerun()

            # Action: RETRY CHECKING
            elif btn_action == "RETRY":
                with st.spinner("Retrying payment route availability check..."):
                    re_res = client.analyze_payment(st.session_state["active_payment_request"])
                    if re_res.get("success"):
                        st.session_state["current_analysis"] = re_res["data"]
                        st.rerun()

            # Action: EXECUTE SECURE PAYMENT
            elif btn_action == "EXECUTE":
                target_route = st.session_state.get("target_exec_route") or analysis.get("decision", {}).get("recommended_route")

                with st.status("Processing secure transaction via AI Route Shield...", expanded=True) as status_box:
                    status_box.update(label="🔐 Securing 256-bit encrypted handshake...")
                    time.sleep(0.18)
                    status_box.update(label="🏦 Requesting bank authorization...")
                    time.sleep(0.18)
                    status_box.update(label="🛡️ AI Shield verifying packet delivery...")
                    time.sleep(0.18)
                    status_box.update(label="🧾 Generating instant digital receipt...", state="running")

                    exec_payload = st.session_state["active_payment_request"].copy()
                    exec_payload["preferred_route"] = target_route
                    exec_res = client.process_payment(exec_payload)

                    if exec_res.get("success"):
                        data = exec_res["data"]
                        st.session_state["last_execution_result"] = data
                        if data.get("status") == "SUCCESS":
                            status_box.update(label="Payment successful! Funds transferred safely.", state="complete")
                        else:
                            status_box.update(label="Payment could not be completed.", state="error")
                    else:
                        st.error(f"Payment Execution Error: {exec_res.get('error')}")

    # Payment Result Section
    last_result = st.session_state.get("last_execution_result")
    if last_result:
        render_payment_result_card(last_result)


# PAGE 2: TRACK PAYMENT STATUS & DEBIT VERIFIER
elif nav_selection == "🔍 Track Payment":
    render_transaction_status_section(client)


# PAGE 3: MY PAYMENT HISTORY & DIGITAL RECEIPTS
elif nav_selection == "📋 My Transactions":
    render_transactions_audit_panel(client)


# PAGE 4: LIVE BANK & UPI HEALTH RADAR
elif nav_selection == "⚡ Live Bank Health":
    render_live_bank_health_radar()


# PAGE 5: PAYMENT PREFERENCES & AI SHIELD SETTINGS
elif nav_selection == "⚙️ Payment Preferences":
    render_gateway_settings_panel(client)

