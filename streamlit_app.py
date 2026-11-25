import streamlit as st

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="NEXLYTICS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: linear-gradient(135deg, #080d1b, #0d1428 55%, #111a35);
    color: #f1f5f9;
    font-family: 'Inter', sans-serif;
}

#MainMenu, footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0a1020;
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

section[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif;
}

/* Navigation */
[data-testid="stSidebarNav"] {
    padding-top: 1rem;
}

[data-testid="stSidebarNav"] a {
    border-radius: 10px;
    margin: 5px 0;
    padding: 10px 12px;
    transition: all 0.2s ease;
}

[data-testid="stSidebarNav"] a:hover {
    background: rgba(59, 130, 246, 0.15);
    color: #93c5fd;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: linear-gradient(
        90deg,
        rgba(37, 99, 235, 0.25),
        rgba(124, 58, 237, 0.15)
    );
    border-left: 3px solid #6366f1;
}

/* Brand */
.brand {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 5px;
}

.brand-subtitle {
    color: #64748b;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 25px;
}

/* Hero */
.hero {
    background:
        radial-gradient(circle at top right, rgba(99,102,241,0.22), transparent 35%),
        linear-gradient(120deg, rgba(30,41,75,0.95), rgba(15,23,42,0.95));
    border: 1px solid rgba(129,140,248,0.22);
    border-radius: 20px;
    padding: 38px 40px;
    margin-bottom: 30px;
    box-shadow: 0 15px 45px rgba(0,0,0,0.2);
}

.hero-tag {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(96,165,250,0.25);
    color: #93c5fd;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    margin-bottom: 18px;
}

.hero h1 {
    font-size: 42px;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 12px 0;
    letter-spacing: -1.5px;
}

.hero p {
    color: #a5b4cc;
    font-size: 15px;
    line-height: 1.8;
    max-width: 720px;
    margin-bottom: 0;
}

/* Section headings */
.section-heading {
    color: #e2e8f0;
    font-size: 20px;
    font-weight: 700;
    margin: 28px 0 16px 0;
}

/* Feature cards */
.feature-card {
    background: linear-gradient(145deg, rgba(30,41,70,0.85), rgba(15,23,42,0.95));
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 16px;
    padding: 23px;
    min-height: 170px;
    transition: all 0.25s ease;
}

.feature-card:hover {
    border-color: rgba(99,102,241,0.5);
    transform: translateY(-3px);
}

.feature-icon {
    font-size: 27px;
    margin-bottom: 15px;
}

.feature-title {
    color: #f1f5f9;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 9px;
}

.feature-description {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.7;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    color: white;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}

.stButton > button:hover {
    color: white;
    border: none;
}

/* Footer */
.footer {
    color: #64748b;
    font-size: 12px;
    text-align: center;
    padding: 25px 0 5px 0;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR BRANDING
# =====================================================

with st.sidebar:
    st.markdown("""
    <div class="brand">NEXLYTICS</div>
    <div class="brand-subtitle">Business Intelligence Platform</div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div style="
        color:#64748b;
        font-size:11px;
        letter-spacing:1.5px;
        font-weight:700;
        margin:15px 0 8px 5px;
    ">
        WORKSPACE
    </div>

    <div style="
        color:#94a3b8;
        font-size:12px;
        line-height:1.8;
        padding:5px;
    ">
        Explore business performance, machine learning
        forecasts and AI-powered insights from one workspace.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div style="color:#64748b;font-size:11px;padding:5px;">
        ● SYSTEM ONLINE
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# MULTI-PAGE NAVIGATION
# =====================================================

page_overview = st.Page(
    "pages/01_overview.py",
    title="Business Overview",
    icon="🏠",
    default=True
)

page_ml = st.Page(
    "pages/03_ml_forecast.py",
    title="ML Forecasts",
    icon="🤖"
)

page_ai = st.Page(
    "pages/04_ai_insights.py",
    title="AI Insights",
    icon="🧠"
)

pg = st.navigation([
    page_overview,
    page_ml,
    page_ai
])

pg.run()
