import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE TITLE
# =====================================================

st.title("🧠 AI Decision Intelligence & Simulations")

st.markdown(
    "**Advanced Gen-AI Logic** — Decision Readiness & What-If Analysis"
)

# =====================================================
# CUSTOM STYLING
# =====================================================

st.markdown("""
<style>
div[data-testid="stMetric"] {
    background: linear-gradient(
        145deg,
        rgba(30, 41, 70, 0.95),
        rgba(15, 23, 42, 0.98)
    );
    border: 1px solid rgba(129, 140, 248, 0.20);
    padding: 20px;
    border-radius: 15px;
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8;
    font-weight: 600;
}

div[data-testid="stMetricValue"] {
    color: #60a5fa;
    font-weight: 800;
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# 1. DECISION CONFIDENCE PASSPORT
# =====================================================

st.markdown("### 🛂 Decision Confidence Passport")

col1, col2, col3 = st.columns(3, gap="large")

col1.metric(
    label="AI Confidence Score",
    value="87%",
    delta="High Certainty"
)

col2.metric(
    label="Data Quality Readiness",
    value="92%",
    delta="Passed Audits"
)

col3.metric(
    label="Fan-Out Risk Level",
    value="High",
    delta="-14k Rows",
    delta_color="inverse"
)

# =====================================================
# AI RECOMMENDATION
# =====================================================

st.info(
    "**AI Recommendation:** Reallocate promotional resources "
    "to audit mid-tier campaigns. Top 3 campaigns dominate "
    "71.35% of redemptions, creating operational dependency risk."
)

st.markdown("---")

# =====================================================
# 2. WHAT-IF SCENARIO SIMULATOR
# =====================================================

st.subheader("🔮 What-If Scenario Simulator")

st.write(
    "Adjust the budget reallocation to see predicted impacts "
    "on demographic coverage and campaign reach."
)

reallocation_pct = st.slider(
    "Reallocate Budget from Top 3 to Mid-Tier Campaigns (%)",
    min_value=0,
    max_value=100,
    value=20,
    step=1
)

# =====================================================
# SIMULATION CALCULATIONS
# =====================================================

current_coverage = 47.98

predicted_coverage = (
    current_coverage + (reallocation_pct * 0.15)
)

predicted_reach = (
    7208 - (reallocation_pct * 10)
)

# =====================================================
# SIMULATION METRICS
# =====================================================

st.markdown("### 📊 Predicted Business Impact")

col_sim1, col_sim2 = st.columns(2, gap="large")

col_sim1.metric(
    label="Predicted Demographic Coverage",
    value=f"{predicted_coverage:.2f}%",
    delta=f"+{predicted_coverage - current_coverage:.2f}%"
)

col_sim2.metric(
    label="Projected Reach (Assignments)",
    value=f"{predicted_reach:,.0f}",
    delta=f"{predicted_reach - 7208:,.0f}",
    delta_color="inverse"
)

# =====================================================
# SIMULATION CHART
# =====================================================

sim_data = pd.DataFrame({
    "Scenario": [
        "Current State",
        "Simulated State"
    ],
    "Coverage %": [
        current_coverage,
        predicted_coverage
    ]
})

fig = px.bar(
    sim_data,
    x="Scenario",
    y="Coverage %",
    color="Scenario",
    title="Impact of Budget Reallocation on Demographic Coverage",
    text="Coverage %",
    color_discrete_sequence=[
        "#3b82f6",
        "#8b5cf6"
    ]
)

fig.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="outside",
    marker_line_width=0
)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="Inter, sans-serif",
        color="#cbd5e1"
    ),
    title_font=dict(
        size=18,
        color="#f1f5f9"
    ),
    xaxis_title="Scenario",
    yaxis_title="Demographic Coverage (%)",
    showlegend=False,
    yaxis=dict(
        range=[
            0,
            max(60, predicted_coverage + 8)
        ],
        gridcolor="rgba(148,163,184,0.15)"
    ),
    xaxis=dict(
        showgrid=False
    ),
    height=420,
    margin=dict(
        l=30,
        r=30,
        t=70,
        b=40
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# SIMULATION SUMMARY
# =====================================================

st.markdown("---")

st.markdown("### 💡 Simulation Summary")

st.success(
    f"With {reallocation_pct}% budget reallocation, "
    f"predicted demographic coverage is "
    f"{predicted_coverage:.2f}% compared with the current "
    f"{current_coverage:.2f}%."
)

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.caption(
    "NEXLYTICS | AI Decision Intelligence & Business Simulations"
)
