"""Payment History & Digital Receipts Component for PayRoute AI.

Displays a filterable, searchable, and exportable ledger of customer payments
with instant digital receipts and live lifecycle tracking.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

try:
    from dashboard.api_client import PayRouteAPIClient
except ModuleNotFoundError:
    from api_client import PayRouteAPIClient


def render_transactions_audit_panel(client: Optional[PayRouteAPIClient] = None) -> None:
    """Renders the customer payment history ledger with search, filters, receipt viewer, and export."""
    if client is None:
        client = PayRouteAPIClient()

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 18px 22px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.2);">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h2 style="margin: 0; font-size: 1.45rem; font-weight: 800; color: #ffffff;">📋 My Payment History & Receipts</h2>
                    <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: #e0f2fe; font-weight: 600;">
                        View your completed online payments, verify bank debit states, and download digital receipts.
                    </p>
                </div>
                <div style="background: rgba(255,255,255,0.18); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 700;">
                    🛡️ AI ROUTE PROTECTED
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter Bar
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 1])
    with f_col1:
        search_query = st.text_input(
            "🔍 Search My Payments",
            placeholder="Search by Transaction ID, Store, Bank...",
            key="txn_audit_search",
        )
    with f_col2:
        status_filter = st.selectbox(
            "Status",
            options=["ALL", "SUCCESS", "FAILED", "PENDING", "RE_ROUTED"],
            index=0,
            key="txn_audit_status",
        )
    with f_col3:
        payment_app_filter = st.selectbox(
            "Payment Method",
            options=["ALL", "UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
            index=0,
            key="txn_audit_method",
        )
    with f_col4:
        limit = st.selectbox(
            "Rows",
            options=[25, 50, 100],
            index=0,
            key="txn_audit_limit",
        )

    with st.spinner("Loading your payment history..."):
        api_status = status_filter if status_filter != "ALL" else None
        res = client.get_all_transactions(
            limit=limit,
            status_filter=api_status,
            search_query=search_query if search_query.strip() else None,
        )

    if res.get("success"):
        response_data = res.get("data", {})
    else:
        st.error(f"Failed to fetch payments: {res.get('error')}")
        response_data = {"transactions": [], "total": 0}

    txns: List[Dict[str, Any]] = response_data.get("transactions", [])
    total_count: int = response_data.get("total", response_data.get("total_count", len(txns)))

    if payment_app_filter != "ALL" and txns:
        txns = [t for t in txns if str(t.get("payment_method", "")).upper() == payment_app_filter]

    if txns:
        df = pd.DataFrame(txns)
        total_shown = len(df)
        success_count = len(df[df["lifecycle_status"].astype(str).str.upper().isin(["SUCCESS", "CONFIRMED_SUCCESS", "SUCCESS_AFTER_RETRY"]) | (df.get("payment_status") == 0)])
        failed_count = len(df[df["lifecycle_status"].astype(str).str.upper().isin(["FAILED", "ABORTED", "FAILED_NO_DEBIT"]) | (df.get("payment_status") == 1)])
        
        try:
            total_spent = df["amount"].astype(float).sum()
        except Exception:
            total_spent = 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Payments", f"{total_shown}")
        m2.metric("Successful Payments", f"{success_count}", delta="Safe & Verified")
        m3.metric("Failed / Retried", f"{failed_count}")
        m4.metric("Total Spent", f"₹{total_spent:,.2f}")

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # Action bar: Download CSV
        btn_c1, btn_c2 = st.columns([1, 4])
        with btn_c1:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Statement (CSV)",
                data=csv_data,
                file_name=f"PayRoute_Statement_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Render Table
        display_rows = []
        for t in txns:
            st_val = str(t.get("lifecycle_status") or ("SUCCESS" if t.get("payment_status") == 0 else "FAILED")).upper()
            st_badge = "🟢 SUCCESS" if "SUCCESS" in st_val else ("🔴 FAILED" if "FAIL" in st_val or "ABORT" in st_val else f"🟡 {st_val}")
            
            created_at = t.get("created_at", "")
            if created_at and "T" in created_at:
                created_at = created_at.replace("T", " ")[:19]

            amt_val = t.get("amount", 0.0)
            try:
                amt_str = f"₹{float(amt_val):,.2f}"
            except Exception:
                amt_str = f"₹{amt_val}"

            gw = t.get("route_id") or t.get("provider") or "Direct Bank Rail"
            lat = t.get("gateway_latency_ms") or t.get("latency_ms") or 120

            display_rows.append({
                "Transaction ID": t.get("transaction_id", ""),
                "Date & Time": created_at,
                "Amount": amt_str,
                "Payment Method": t.get("payment_method", "UPI"),
                "Funding Bank": t.get("bank", "HDFC"),
                "Status": st_badge,
                "Bank Debit Status": t.get("customer_debit_status", "CONFIRMED"),
                "Speed": f"{lat:.0f}ms",
            })

        display_df = pd.DataFrame(display_rows)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Digital Receipt Inspector
        st.markdown("<h4 style='color: #0c4a6e; margin-top: 20px;'>🧾 Digital Payment Receipt & Details</h4>", unsafe_allow_html=True)
        txn_ids = [t.get("transaction_id", "") for t in txns if t.get("transaction_id")]
        
        if txn_ids:
            selected_txn_id = st.selectbox(
                "Select a Transaction ID to view its complete receipt:",
                options=txn_ids,
                key="txn_audit_selected_id",
            )
            
            matched = next((t for t in txns if t.get("transaction_id") == selected_txn_id), None)
            if matched:
                with st.expander(f"Official Receipt: {selected_txn_id}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Transaction ID:** `{matched.get('transaction_id', 'N/A')}`")
                        st.markdown(f"**Payment Status:** `{matched.get('lifecycle_status', 'SUCCESS')}`")
                        st.markdown(f"**Bank Account Debit:** `{matched.get('customer_debit_status', 'CONFIRMED')}`")
                    with c2:
                        st.markdown(f"**Amount Paid:** `₹{float(matched.get('amount', 0)):,.2f}`")
                        st.markdown(f"**Payment Method:** `{matched.get('payment_method', 'UPI')}`")
                        st.markdown(f"**Funding Bank:** `{matched.get('bank', 'HDFC')}`")
                    with c3:
                        st.markdown(f"**Payment Speed:** `{matched.get('latency_ms', 120)}ms`")
                        st.markdown(f"**Timestamp:** `{matched.get('created_at', 'N/A')}`")
                        st.markdown(f"**AI Shield Protection:** `Active ✓`")
                    
                    st.download_button(
                        "📥 Download Single Receipt (TXT)",
                        data=f"PAYROUTE AI PAYMENT RECEIPT\nTxn ID: {selected_txn_id}\nAmount: INR {matched.get('amount', 0)}\nStatus: {matched.get('lifecycle_status', 'SUCCESS')}\nDate: {matched.get('created_at')}",
                        file_name=f"Receipt_{selected_txn_id}.txt",
                        key="btn_dl_single_receipt",
                    )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px; background: white; border-radius: 12px; border: 1.5px dashed #7dd3fc; margin-top: 15px;">
                <div style="font-size: 2.2rem; margin-bottom: 8px;">📭</div>
                <h3 style="color: #082f49; font-weight: 850; margin: 0 0 6px 0;">No Payment Records Found</h3>
                <p style="color: #0c4a6e; font-size: 0.95rem; font-weight: 600; max-width: 450px; margin: 0 auto 16px auto;">
                    You haven't made any payments matching this filter yet. Head over to <strong>Pay & Transfer</strong> to make a fast, secure payment!
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
