
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.title("🏠 NEXLYTICS — Executive Overview")
st.caption("From Business Data to Confident Decisions")

# =====================================================
# CUSTOM STYLING
# =====================================================

st.markdown("""
<style>
/* Page headings */
h1 {
    color: #f8fafc !important;
    font-weight: 800 !important;
    letter-spacing: -1px;
}

h2, h3 {
    color: #e2e8f0 !important;
    font-weight: 700 !important;
}

/* KPI cards */
div[data-testid="stMetric"] {
    background: linear-gradient(
        145deg,
        rgba(30, 41, 70, 0.95),
        rgba(15, 23, 42, 0.98)
    );
    border: 1px solid rgba(129, 140, 248, 0.20);
    padding: 22px 20px;
    border-radius: 15px;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

div[data-testid="stMetricValue"] {
    color: #60a5fa !important;
    font-size: 29px !important;
    font-weight: 800 !important;
}

/* Chart container */
div[data-testid="stPlotlyChart"] {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 15px;
    padding: 12px;
}

/* Caption */
.stCaption {
    color: #94a3b8 !important;
}

/* Divider */
hr {
    border-color: rgba(148, 163, 184, 0.15);
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HERO SECTION
# =====================================================

st.html("""
<div style="
    background:
        radial-gradient(circle at top right, rgba(99,102,241,0.22), transparent 40%),
        linear-gradient(120deg, #1e293b, #111827);
    border: 1px solid rgba(129,140,248,0.25);
    border-radius: 18px;
    padding: 28px 32px;
    margin: 12px 0 28px 0;
">
    <div style="
        color: #93c5fd;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 12px;
    ">
        EXECUTIVE BUSINESS INTELLIGENCE
    </div>

    <div style="
        color: #f8fafc;
        font-size: 27px;
        font-weight: 800;
        margin-bottom: 10px;
    ">
        Business Performance at a Glance
    </div>

    <div style="
        color: #a5b4cc;
        font-size: 14px;
        line-height: 1.8;
        max-width: 800px;
    ">
        Monitor campaign assignments, coupon redemptions and
        business performance indicators through a unified
        executive analytics dashboard.
    </div>
</div>
""")

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data
def load_data():

    base_path = Path(__file__).resolve().parent.parent

    assignments_path = (
        base_path /
        "Data-Preparation" /
        "Processed" /
        "campaign_table_cleaned.csv"
    )

    redemptions_path = (
        base_path /
        "Data-Preparation" /
        "Processed" /
        "coupon_redempt_cleaned.csv"
    )

    assignments = pd.read_csv(assignments_path)
    redemptions = pd.read_csv(redemptions_path)

    return assignments, redemptions


# =====================================================
# DASHBOARD DATA AND VISUALS
# =====================================================

try:

    assignments, redemptions = load_data()

    if "campaign" not in redemptions.columns:
        st.error(
            "The redemptions CSV does not contain a 'campaign' column."
        )
        st.stop()

    # -------------------------------------------------
    # KPI SECTION
    # -------------------------------------------------

    st.markdown("### 📊 Executive Performance Metrics")

    col1, col2, col3, col4 = st.columns(4, gap="medium")

    with col1:
        st.metric(
            label="Total Assignments",
            value=f"{len(assignments):,}"
        )

    with col2:
        st.metric(
            label="Total Redemptions",
            value=f"{len(redemptions):,}"
        )

    with col3:
        st.metric(
            label="Descriptive Matched Incidence",
            value="12.33%"
        )

    with col4:
        st.metric(
            label="Demographic Target Coverage",
            value="47.98%"
        )

    st.markdown("---")

    # -------------------------------------------------
    # CAMPAIGN REDEMPTION ANALYSIS
    # -------------------------------------------------

    st.markdown("### 📈 Campaign Redemption Analysis")

    st.caption(
        "Explore the 15 campaigns with the highest number of redemptions."
    )

    camp_counts = (
        redemptions["campaign"]
        .value_counts()
        .reset_index()
    )

    camp_counts.columns = ["Campaign", "Redemptions"]

    camp_counts = (
        camp_counts
        .sort_values("Redemptions", ascending=True)
        .tail(15)
    )

    if camp_counts.empty:
        st.warning("No campaign redemption records are available.")

    else:

        fig = px.bar(
            camp_counts,
            x="Redemptions",
            y="Campaign",
            orientation="h",
            color="Redemptions",
            color_continuous_scale=[
                "#1e3a8a",
                "#2563eb",
                "#60a5fa",
                "#a78bfa"
            ],
            text="Redemptions",
            title="Top 15 Campaigns by Redemptions"
        )

        fig.update_traces(
            textposition="outside",
            marker_line_width=0,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Redemptions: %{x:,}"
                "<extra></extra>"
            )
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Inter, sans-serif",
                color="#cbd5e1",
                size=12
            ),
            title=dict(
                font=dict(
                    size=18,
                    color="#f1f5f9"
                )
            ),
            xaxis_title="Number of Redemptions",
            yaxis_title="Campaign",
            coloraxis_showscale=False,
            margin=dict(l=20, r=50, t=65, b=35),
            height=520,
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(148,163,184,0.12)",
                zeroline=False
            ),
            yaxis=dict(
                showgrid=False,
                categoryorder="total ascending"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # -------------------------------------------------
    # DATA SUMMARY
    # -------------------------------------------------

    st.markdown("---")
    st.markdown("### 📁 Dataset Summary")

    summary1, summary2 = st.columns(2)

    with summary1:
        st.markdown("**Campaign Assignments Dataset**")
        st.caption(f"Total records: {len(assignments):,}")
        st.caption(f"Total columns: {len(assignments.columns)}")

    with summary2:
        st.markdown("**Coupon Redemptions Dataset**")
        st.caption(f"Total records: {len(redemptions):,}")
        st.caption(f"Total columns: {len(redemptions.columns)}")

    # Optional data preview
    with st.expander("View redemption data sample"):
        st.dataframe(
            redemptions.head(10),
            use_container_width=True
        )

    # -------------------------------------------------
    # FOOTER
    # -------------------------------------------------

    st.markdown("---")

    st.html("""
    <div style="
        text-align:center;
        color:#64748b;
        font-size:12px;
        padding:15px 0;
    ">
        NEXLYTICS · Executive Business Overview
        <br>
        Business Intelligence • Analytics • Data-Driven Decisions
    </div>
    """)

except FileNotFoundError:
    st.error(
        "Data files not found. Please check that both CSV files "
        "exist inside Data-Preparation/Processed/."
    )

except Exception as e:
    st.error(f"Unable to load the overview dashboard: {e}")
