import streamlit as st

st.set_page_config(page_title="NEXLYTICS", page_icon="📊", layout="wide")

page_overview = st.Page("pages/01_overview.py", title="Business Overview", icon="🏠")
page_powerbi = st.Page("pages/02_powerbi.py", title="Interactive Dashboard", icon="📊")
page_ml = st.Page("pages/03_ml_forecast.py", title="ML Forecasts", icon="🤖")
page_ai = st.Page("pages/04_ai_insights.py", title="AI Insights", icon="🧠")

pg = st.navigation([page_overview, page_powerbi, page_ml, page_ai])
pg.run()