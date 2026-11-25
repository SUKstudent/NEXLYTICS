import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🤖 Predictive Analytics & Anomaly Detection")
st.markdown("Advanced Machine Learning • Forecasting & Anomaly Detection")

# File paths based on your directory structure
forecast_path = 'Predictive Analytics & ML/outputs/forecast_results.csv'
anomaly_path = 'Predictive Analytics & ML/outputs/anomaly_results.csv'

try:
    # Load Tauz's data
    df_forecast = pd.read_csv(forecast_path)
    df_anomaly = pd.read_csv(anomaly_path)
    
    st.success("✅ Successfully loaded Tauz's ML output data.")
    
    # Tabs for the two models
    tab1, tab2 = st.tabs(["📈 Redemption Forecast", "🚨 Anomaly Detection"])
    
    with tab1:
        st.subheader("Predicted Campaign Redemptions")
        # Assuming the first column is Date/Index and second is the Forecast
        x_col = df_forecast.columns[0]
        y_col = df_forecast.columns[1]
        
        fig_forecast = px.line(df_forecast, x=x_col, y=y_col, 
                               title="ML Forecasted Redemptions",
                               markers=True)
        fig_forecast.update_layout(xaxis_title="Timeline", yaxis_title="Predicted Redemptions")
        st.plotly_chart(fig_forecast, use_container_width=True)
        
    with tab2:
        st.subheader("Detected Anomalies in Campaign Activity")
        # Display the anomaly dataframe
        st.dataframe(df_anomaly, use_container_width=True)
        
        # If there's a score/flag column, try to plot it
        if len(df_anomaly.columns) >= 2:
            fig_anomaly = px.scatter(df_anomaly, x=df_anomaly.columns[0], y=df_anomaly.columns[1], 
                                     color=df_anomaly.columns[1], 
                                     title="Anomaly Scatter Plot")
            st.plotly_chart(fig_anomaly, use_container_width=True)

except FileNotFoundError:
    st.error(f"Could not find Tauz's output files. Checked paths:\n- {forecast_path}\n- {anomaly_path}")
except Exception as e:
    st.error(f"An error occurred reading the data: {e}")
