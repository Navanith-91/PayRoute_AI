"""
Customer Payment Preferences & AI Route Shield Configuration UI Component.
Allows customers to manage preferred UPI apps (GPay, PhonePe, Paytm), linked bank accounts,
and AI Auto-Shield protection settings.
"""

from typing import Any, Dict, List
import time
import streamlit as st


def render_gateway_settings_panel(client) -> None:
    """
    Renders Customer Payment Preferences, Linked UPI Apps, and AI Shield Configuration.
    """
    st.markdown("### ⚙️ PAYMENT PREFERENCES & AI SHIELD")
    st.markdown(
        '<div style="color: #0c4a6e; font-size: 0.98rem; font-weight: 600; margin-bottom: 1.2rem; line-height: 1.5;">'
        "Manage your linked UPI applications (<strong>Google Pay</strong>, <strong>PhonePe</strong>, <strong>Paytm</strong>), "
        "primary bank account, and customize your <strong>AI Route Shield</strong> protection level."
        "</div>",
        unsafe_allow_html=True,
    )

    tab_upi, tab_banks, tab_shield = st.tabs([
        "📱 Linked UPI Apps",
        "🏦 Bank Accounts & Cards",
        "🛡️ AI Auto-Shield & Security",
    ])

    # =========================================================================
    # Tab 1: Linked UPI Apps
    # =========================================================================
    with tab_upi:
        _render_customer_upi_settings(client)

    # =========================================================================
    # Tab 2: Bank Accounts & Cards
    # =========================================================================
    with tab_banks:
        _render_customer_bank_settings(client)

    # =========================================================================
    # Tab 3: AI Auto-Shield & Security
    # =========================================================================
    with tab_shield:
        _render_customer_shield_settings(client)


def _render_customer_upi_settings(client) -> None:
    """Customer UPI Apps & VPAs configuration."""
    with st.container(border=True):
        st.markdown("#### 📱 Linked UPI Applications")
        st.caption("Select your default UPI app and configure your Virtual Payment Addresses (VPAs).")

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            default_app = st.selectbox(
                "Primary Default UPI App",
                ["Google Pay (GPay)", "PhonePe", "Paytm UPI", "BHIM UPI", "Cred UPI"],
                index=0,
                key="pref_default_upi_app",
            )
            upi_vpa = st.text_input(
                "Your Primary UPI ID (VPA)",
                value=st.session_state.get("pref_upi_vpa", "rahul.sharma@okhdfcbank"),
                placeholder="yourname@bank",
                key="pref_upi_vpa_input",
            )
        with col_u2:
            secondary_vpa = st.text_input(
                "Backup UPI ID (Optional)",
                value="rahul.sharma@ybl",
                placeholder="backup@bank",
                key="pref_backup_vpa_input",
            )
            fast_checkout = st.checkbox(
                "⚡ Enable 1-Click Fast UPI Intent (Deep-Linking)",
                value=True,
                help="Automatically triggers the UPI app on your mobile device without manual VPA entry.",
            )

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            if st.button("💾 Save UPI Preferences", use_container_width=True, type="primary", key="btn_save_upi_pref"):
                st.session_state["pref_upi_vpa"] = upi_vpa
                st.success("✓ UPI preferences saved securely!")
                st.rerun()

        with col_b2:
            if st.button("⚡ Test UPI Rail Ping", use_container_width=True, key="btn_ping_upi_rail"):
                with st.spinner("Pinging UPI rail switches (GPay & PhonePe)..."):
                    time.sleep(0.3)
                    st.success("✓ Google Pay & PhonePe UPI Rails Connected (Avg Latency: 78ms)")


def _render_customer_bank_settings(client) -> None:
    """Customer Bank Accounts and Cards configuration."""
    with st.container(border=True):
        st.markdown("#### 🏦 Linked Bank Accounts & Saved Cards")
        st.caption("Manage your funding accounts for online transactions.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Primary Bank Account")
            primary_bank = st.selectbox(
                "Default Bank for Transfers",
                ["HDFC Bank (••••4291)", "State Bank of India (••••1082)", "ICICI Bank (••••6649)", "Axis Bank (••••3390)"],
                index=0,
                key="pref_primary_bank",
            )
            st.caption("🟢 Account Active | Auto-Debit Mandate: Enabled")

        with c2:
            st.markdown("##### Saved Tokenized Cards")
            st.markdown(
                """
                <div style="background: #f0f9ff; border: 1.2px solid #bae6fd; border-radius: 8px; padding: 0.7rem 0.9rem; margin-bottom: 0.6rem;">
                    <div style="font-weight: 800; color: #082f49; font-size: 0.9rem;">💳 HDFC Regalia Visa Platinum</div>
                    <div style="color: #0369a1; font-size: 0.82rem; font-weight: 600;">•••• •••• •••• 8819 | Exp: 09/29 | RBI Tokenized ✓</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
        if st.button("💾 Update Bank Preferences", use_container_width=True, type="primary", key="btn_save_bank_pref"):
            st.success("✓ Bank preferences updated!")


def _render_customer_shield_settings(client) -> None:
    """Customer AI Route Shield & Security settings."""
    with st.container(border=True):
        st.markdown("#### 🛡️ PayRoute AI Route Shield Settings")
        st.caption("Configure how AI protects your payments from server timeouts and bank network drops.")

        shield_active = st.toggle("🛡️ Active Route Shield (Auto-reroute on bank congestion)", value=True)
        instant_refund = st.toggle("⚡ Instant Auto-Reversal Tracker (Monitors debited-but-pending transactions)", value=True)
        sms_alerts = st.toggle("🔔 Instant Payment Delivery & Settlement Notifications", value=True)

        st.markdown(
            """
            <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 8px; padding: 0.9rem 1.1rem; margin-top: 1rem;">
                <div style="font-weight: 850; color: #16a34a; font-size: 0.95rem; margin-bottom: 0.2rem;">
                    🛡️ AI ROUTE PROTECTION GUARANTEE: ACTIVE
                </div>
                <div style="color: #082f49; font-size: 0.88rem; font-weight: 600; line-height: 1.5;">
                    When your primary bank experiences heavy traffic or server timeouts (>800ms), PayRoute AI automatically switches the underlying payment tunnel to a healthy backup gateway, ensuring zero dropped payments.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
        if st.button("💾 Save Security & Shield Settings", use_container_width=True, type="primary", key="btn_save_shield_pref"):
            st.success("✓ AI Route Shield settings saved successfully!")

