import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

st.title("🤖 Predictive Analytics & Forecasting")

# Check if Tauz pushed a real dataset. If not, generate mock data for demo.
try:
    # Replace with Tauz's actual file path if he pushed one
    df = pd.read_csv('Predictive Analytics & ML/forecast_output.csv') 
    st.success("Loaded ML predictions successfully.")
except FileNotFoundError:
    st.warning("Actual ML model output not found. Displaying simulated projection for demonstration.")
    # Mock data
    dates = pd.date_range(start='1/1/2023', periods=30, freq='D')
    df = pd.DataFrame({'Date': dates, 'Predicted_Redemptions': np.random.randint(50, 150, 30)})

fig = px.line(df, x='Date', y='Predicted_Redemptions', title='30-Day Redemption Forecast')
st.plotly_chart(fig, use_container_width=True)