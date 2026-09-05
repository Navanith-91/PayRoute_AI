"""
Explainability Section Component for Streamlit Dashboard.
Clean, modern card-based design without graph dependencies.
"""

from typing import Any, Dict
import streamlit as st
from dashboard.components.charts import render_feature_attribution_chart


def render_explanation_card(explanation: Dict[str, Any]) -> None:
    """Renders explainability card with positive and negative drivers in clean UI."""
    if not explanation:
        st.info("No explainability metadata returned.")
        return

    top_risk = explanation.get("top_risk_contributors", [])
    top_protective = explanation.get("top_protective_factors", [])

    with st.container(border=True):
        st.markdown("#### 🧠 AI Explainability & Local Attribution (SHAP Signals)")
        st.caption("Detailed breakdown of features driving the model's failure probability assessment for this transaction.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🔴 Top Risk Drivers (+ Failure Risk)")
            if top_risk:
                for r in top_risk:
                    f_name = r.get("name", "").replace("_", " ").title()
                    impact = float(r.get("impact", 0.0))
                    st.markdown(f"- **{f_name}**: `+{impact:.4f}` (elevates risk)")
            else:
                st.write("No major risk multipliers detected.")

        with col2:
            st.markdown("##### 🟢 Top Protective Factors (- Failure Risk)")
            if top_protective:
                for p in top_protective:
                    f_name = p.get("name", "").replace("_", " ").title()
                    impact = float(p.get("impact", 0.0))
                    st.markdown(f"- **{f_name}**: `{impact:.4f}` (improves reliability)")
            else:
                st.write("No major protective factors detected.")

        st.markdown("##### 📋 Complete Feature Attribution Table")
        render_feature_attribution_chart(top_risk, top_protective)

