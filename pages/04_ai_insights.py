import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.title("🧠 AI Decision Intelligence & Simulations")
st.markdown("Gen-AI Logic** (Decision Readiness & What-If Analysis)")

# 1. Decision Confidence Passport
st.markdown("### 🛂 Decision Confidence Passport")
col1, col2, col3 = st.columns(3)
col1.metric(label="AI Confidence Score", value="87%", delta="High Certainty")
col2.metric(label="Data Quality Readiness", value="92%", delta="Passed Audits")
col3.metric(label="Fan-Out Risk Level", value="High", delta="-14k Rows", delta_color="inverse")

st.info("**AI Recommendation:** Reallocate promotional resources to audit mid-tier campaigns. Top 3 campaigns dominate 71.35% of redemptions, creating operational dependency risk.")

st.markdown("---")

# 2. What-If Simulation (Simulating Naveen's what_if_simulation.py)
st.subheader("🔮 What-If Scenario Simulator")
st.write("Adjust the budget reallocation to see predicted impacts on demographic coverage and campaign reach.")

reallocation_pct = st.slider("Reallocate Budget from Top 3 to Mid-Tier Campaigns (%)", 0, 100, 20)

# Simulated AI math for the demo
current_coverage = 47.98
predicted_coverage = current_coverage + (reallocation_pct * 0.15) # AI logic simulation
predicted_reach = 7208 - (reallocation_pct * 10)

col_sim1, col_sim2 = st.columns(2)
col_sim1.metric(label="Predicted Demographic Coverage", value=f"{predicted_coverage:.2f}%", delta=f"+{predicted_coverage - current_coverage:.2f}%")
col_sim2.metric(label="Projected Reach (Assignments)", value=f"{predicted_reach:,.0f}")

# Chart for the simulation
sim_data = pd.DataFrame({
    'Scenario': ['Current State', 'Simulated State'],
    'Coverage %': [current_coverage, predicted_coverage]
})
fig = px.bar(sim_data, x='Scenario', y='Coverage %', color='Scenario', 
             title="Impact of Budget Reallocation on Demographic Coverage",
             color_discrete_sequence=['#1f77b4', '#2ca02c'])
st.plotly_chart(fig, use_container_width=True)
