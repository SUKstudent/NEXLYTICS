import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🏠 NEXLYTICS — Executive Overview")
st.markdown("**From Business Data to Confident Decisions**")

# Load data (Kadambini's cleaned CSVs)
@st.cache_data
def load_data():
    # Adjust paths if your folder structure is slightly different
    assignments = pd.read_csv('Data-Preparation/Processed/campaign_table_cleaned.csv')
    redemptions = pd.read_csv('Data-Preparation/Processed/coupon_redempt_cleaned.csv')
    return assignments, redemptions

try:
    assignments, redemptions = load_data()

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assignments", f"{len(assignments):,}")
    col2.metric("Total Redemptions", f"{len(redemptions):,}")
    col3.metric("Descriptive Matched Incidence", "12.33%")
    col4.metric("Demographic Target Coverage", "47.98%")

    st.markdown("---")
    
    # Bar Chart
    st.subheader("Total Redemptions by Campaign")
    camp_counts = redemptions['campaign'].value_counts().reset_index()
    camp_counts.columns = ['Campaign', 'Redemptions']
    camp_counts = camp_counts.sort_values('Redemptions', ascending=True).tail(15) # Top 15
    
    fig = px.bar(camp_counts, x='Redemptions', y='Campaign', orientation='h', 
                 title="Top 15 Campaigns by Redemptions",
                 color='Redemptions', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)

except FileNotFoundError:
    st.error("Data files not found. Please ensure Kadambini's CSVs are in Data-Preparation/Processed/")