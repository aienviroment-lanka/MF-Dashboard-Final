"""
app.py  —  Mutual Fund Live Dashboard
======================================
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from modules.data_ingestion import (
    load_all_schemes,
    compute_overlap,
    DEFAULT_SCHEME_CODES,
    fetch_nav_history,
)
from modules.data_cleaning import clean_records, build_summary

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title    = "Mutual Fund Dashboard",
    page_icon     = "📊",
    layout        = "wide",
    initial_sidebar_state = "expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Styling
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── App background ── */
.main .block-container {
    padding: 1.5rem 2.5rem 3rem;
    max-width: 1600px;
}

/* ── Page header ── */
.dash-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0e4f8b 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem 1.8rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.dash-header h1 {
    color: #f0f9ff;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.dash-header .sub {
    color: #93c5fd;
    font-size: 0.82rem;
    margin-top: 4px;
}
.timestamp-badge {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 6px 14px;
    color: #bfdbfe;
    font-size: 0.76rem;
    text-align: right;
}

/* ── KPI cards ── */
.kpi-row { display: flex; gap: 14px; margin-bottom: 1.5rem; flex-wrap: wrap; }
.kpi-card {
    flex: 1;
    min-width: 140px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #3b82f6);
    border-radius: 12px 12px 0 0;
}
.kpi-label { color: #94a3b8; font-size: 0.72rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.kpi-value { color: #f1f5f9; font-size: 1.6rem; font-weight: 700; }
.kpi-sub   { color: #64748b; font-size: 0.72rem; margin-top: 2px; }

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.8rem 0 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e293b;
}
.section-header h2 {
    color: #e2e8f0;
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
}
.section-tag {
    background: #1e3a5f;
    color: #60a5fa;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Dataframe styling ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #1e293b; }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #64748b;
    border-radius: 8px 8px 0 0;
    padding: 8px 18px;
    font-size: 0.83rem;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #1e293b !important;
    color: #60a5fa !important;
    border-bottom: 2px solid #3b82f6 !important;
}

/* ── Positive / negative ── */
.pos { color: #22c55e !important; }
.neg { color: #f87171 !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] p {
    color: #94a3b8 !important;
    font-size: 0.82rem;
}

/* ── Alert boxes ── */
.info-box {
    background: #0c2340;
    border: 1px solid #1d4ed8;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 16px;
    color: #bfdbfe;
    font-size: 0.8rem;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Plotly dark template shared across all charts
# ──────────────────────────────────────────────────────────────────────────────
PLOTLY_THEME = {
    "template"       : "plotly_dark",
    "paper_bgcolor"  : "#0f172a",
    "plot_bgcolor"   : "#0f172a",
    "font"           : dict(family="Inter", color="#94a3b8", size=11),
}
PALETTE = px.colors.qualitative.Bold

def apply_theme(fig, height=380):
    fig.update_layout(
        height          = height,
        paper_bgcolor   = "#0f172a",
        plot_bgcolor    = "#131f35",
        font            = dict(family="Inter", color="#94a3b8", size=11),
        legend          = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin          = dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(gridcolor="#1e293b", zeroline=False)
    fig.update_yaxes(gridcolor="#1e293b", zeroline=False)
    return fig

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Settings")
    st.markdown("---")

    raw_codes = st.text_area(
        "AMFI Scheme Codes (one per line)",
        value="\n".join(DEFAULT_SCHEME_CODES),
        height=250,
        help="Enter numeric AMFI scheme codes. Find them at mfapi.in",
    )
    scheme_codes = [c.strip() for c in raw_codes.splitlines() if c.strip()]

    refresh_interval = st.selectbox(
        "Auto-refresh interval",
        ["Off", "15 min", "30 min", "1 hour", "6 hours"],
        index=2,
    )
    st.markdown("---")
    st.markdown("""
**Data Sources**
- 📡 [MFAPI](https://api.mfapi.in) — NAV history
- 📋 [AMFI India](https://www.amfiindia.com) — Official NAV
- 📈 Yahoo Finance — Nifty 50 benchmark
    """)
    st.markdown("---")

    if st.button("🔄 Force Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Auto-refresh via st.rerun meta tag
# ──────────────────────────────────────────────────────────────────────────────
interval_map = {
    "Off"   : 0,
    "15 min": 900,
    "30 min": 1800,
    "1 hour": 3600,
    "6 hours": 21600,
}
ref_secs = interval_map.get(refresh_interval, 0)
if ref_secs:
    st.markdown(
        f'<meta http-equiv="refresh" content="{ref_secs}">',
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Load data
# ──────────────────────────────────────────────────────────────────────────────
with st.spinner("📡 Fetching live data from AMFI & MFAPI …"):
    records, fetched_at = load_all_schemes(tuple(scheme_codes))

df_clean  = clean_records(records)
summary   = build_summary(df_clean)
overlap_df = compute_overlap(records)

# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dash-header">
  <div>
    <h1>📊 Mutual Fund Intelligence Dashboard</h1>
    <div class="sub">14 Schemes · Live NAV · AMFI + MFAPI · Nifty 50 Benchmark</div>
  </div>
  <div class="timestamp-badge">
    🟢 Live<br>
    Updated: {fetched_at.strftime('%d %b %Y, %I:%M %p')}<br>
    Next refresh: {refresh_interval}
  </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# A. Summary KPIs
# ──────────────────────────────────────────────────────────────────────────────

def _fmt(v, suffix="", fallback="N/A"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return fallback
    return f"{v:.2f}{suffix}"

st.markdown("""<div class="section-header"><h2>Summary</h2><span class="section-tag">Overview</span></div>""", unsafe_allow_html=True)

cols = st.columns(6)
kpis = [
    ("Total Schemes", str(summary["total_schemes"]), "Loaded live", "#3b82f6"),
    ("Avg 1Y Return", _fmt(summary["avg_1y"], "%"), "Across all schemes", "#22c55e"),
    ("Avg 3Y CAGR",   _fmt(summary["avg_3y"], "%"), "Annualised", "#a78bfa"),
    ("Avg 5Y CAGR",   _fmt(summary["avg_5y"], "%"), "Annualised", "#f59e0b"),
    ("Avg Std Dev",   _fmt(summary["avg_std"], "%"), "3-year annualised", "#f87171"),
    ("Avg Alpha 1Y",  _fmt(summary["avg_alpha_1y"], "%"), "vs Nifty 50", "#38bdf8"),
]
for col, (label, val, sub, accent) in zip(cols, kpis):
    col.markdown(f"""
    <div class="kpi-card" style="--accent:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📋 Scheme Table",
    "📂 Portfolio",
    "🔄 Stock Movements",
    "📐 Overlap",
    "🎯 Benchmark",
    "⚡ Risk Analysis",
    "📈 Charts",
])

# ─────────────────────────────────────────────
# B. Scheme Comparison Table
# ─────────────────────────────────────────────
with tabs[0]:
    st.markdown("""<div class="section-header"><h2>Scheme Comparison Table</h2><span class="section-tag">B</span></div>""", unsafe_allow_html=True)

    display_cols = [
        "Scheme Name", "Category", "Latest NAV (₹)",
        "Inception Return (%)", "1M Return (%)", "3M Return (%)",
        "6M Return (%)", "1Y Return (%)", "3Y CAGR (%)", "5Y CAGR (%)",
        "Std Dev (%)", "Num Stocks", "Cash (%)",
    ]
    disp_df = df_clean[display_cols].copy()

    # Colour-map return columns
    ret_cols = [c for c in display_cols if "Return" in c or "CAGR" in c or "Alpha" in c]

    def color_returns(val):
        if pd.isna(val) or val is None:
            return "color: #64748b"
        return "color: #22c55e; font-weight:600" if val >= 0 else "color: #f87171; font-weight:600"

    styled = (
        disp_df.style
        .format({c: "{:.2f}" for c in ret_cols if c in disp_df.columns}, na_rep="—")
        .format({"Latest NAV (₹)": "{:.4f}", "Num Stocks": "{:.0f}"}, na_rep="—")
        .map(color_returns, subset=ret_cols)
        .set_properties(**{"font-size": "0.8rem"})
    )

    sort_col = st.selectbox("Sort by", ret_cols, index=ret_cols.index("1Y Return (%)") if "1Y Return (%)" in ret_cols else 0)
    asc = st.checkbox("Ascending", value=False)
    disp_df_sorted = disp_df.sort_values(sort_col, ascending=asc)

    st.dataframe(
        disp_df_sorted.style
        .format({c: "{:.2f}" for c in ret_cols if c in disp_df_sorted.columns}, na_rep="—")
        .format({"Latest NAV (₹)": "{:.4f}", "Num Stocks": "{:.0f}"}, na_rep="—")
        .applymap(color_returns, subset=[c for c in ret_cols if c in disp_df_sorted.columns]),
        use_container_width=True,
        height=480,
    )

# ─────────────────────────────────────────────
# C. Portfolio Analysis
# ─────────────────────────────────────────────
with tabs[1]:
    st.markdown("""<div class="section-header"><h2>Portfolio Analysis</h2><span class="section-tag">C</span></div>""", unsafe_allow_html=True)

    scheme_names = [r["scheme_name"][:50] for r in records]
    sel_scheme   = st.selectbox("Select Scheme", scheme_names, key="port_sel")
    sel_rec      = records[scheme_names.index(sel_scheme)]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Number of Stocks", sel_rec.get("num_stocks") or "N/A")
    with col2:
        st.metric("Cash Allocation", f"{sel_rec.get('cash_pct') or 'N/A'}%")
    with col3:
        st.metric("Portfolio Date", sel_rec.get("portfolio_date", "N/A"))

    st.markdown(f"""<div class="info-box">📡 Source: {sel_rec.get('portfolio_source','MFAPI / AMFI')}</div>""", unsafe_allow_html=True)

    pc1, pc2 = st.columns(2)

    # Sector allocation
    with pc1:
        sec = sel_rec.get("sector_alloc", {})
        if sec:
            fig_sec = px.pie(
                names  = list(sec.keys()),
                values = list(sec.values()),
                title  = "Sector Allocation",
                color_discrete_sequence = PALETTE,
                hole   = 0.4,
            )
            apply_theme(fig_sec, height=360)
            st.plotly_chart(fig_sec, use_container_width=True)
        else:
            st.info("Sector data not available from MFAPI for this scheme.")

    # Market cap
    with pc2:
        mc = sel_rec.get("market_cap_alloc", {})
        if mc:
            fig_mc = px.bar(
                x      = list(mc.values()),
                y      = list(mc.keys()),
                title  = "Market Cap Allocation",
                orientation = "h",
                color  = list(mc.keys()),
                color_discrete_sequence = PALETTE,
            )
            apply_theme(fig_mc, height=360)
            st.plotly_chart(fig_mc, use_container_width=True)
        else:
            st.info("Market cap data not available.")

    # Top 10 holdings
    holdings = sel_rec.get("top_holdings", [])
    if holdings:
        st.markdown("#### Top 10 Holdings")
        h_df = pd.DataFrame(holdings)
        fig_h = px.bar(
            h_df, x="pct", y="name",
            orientation = "h",
            text        = "pct",
            color       = "pct",
            color_continuous_scale = "Blues",
            title       = "Top Holdings (% of NAV)",
        )
        fig_h.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        apply_theme(fig_h, height=400)
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("Holdings data not available. MFAPI provides portfolio data for many schemes — check again after AMFI monthly disclosure.")

# ─────────────────────────────────────────────
# D. Fund Flow — simulated from AUM proxy
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# E. Stock Movements
# ─────────────────────────────────────────────
with tabs[2]:
    st.markdown("""<div class="section-header"><h2>Stock Movement Analysis</h2><span class="section-tag">E</span></div>""", unsafe_allow_html=True)

    sel2     = st.selectbox("Select Scheme", scheme_names, key="mov_sel")
    sel_rec2 = records[scheme_names.index(sel2)]

    holdings2 = sel_rec2.get("top_holdings", [])
    if holdings2:
        h_df2 = pd.DataFrame(holdings2).sort_values("pct", ascending=False)
        top5   = h_df2.head(5)
        bot5   = h_df2.tail(5)

        mv1, mv2 = st.columns(2)
        with mv1:
            st.markdown("#### 🔼 Highest Conviction Holdings")
            st.dataframe(
                top5[["name","pct","sector"]].rename(columns={"name":"Stock","pct":"% NAV","sector":"Sector"}),
                use_container_width=True, hide_index=True,
            )
        with mv2:
            st.markdown("#### 🔽 Smallest Holdings (of top 10)")
            st.dataframe(
                bot5[["name","pct","sector"]].rename(columns={"name":"Stock","pct":"% NAV","sector":"Sector"}),
                use_container_width=True, hide_index=True,
            )
        st.info("ℹ️ Month-over-month change data requires two consecutive AMFI portfolio disclosures. Data will appear after the next monthly disclosure is published.")
    else:
        st.info("Portfolio holdings not available for this scheme from MFAPI. This data is published monthly by AMFI.")

    # NAV trend for the selected scheme
    nav_df_sel = fetch_nav_history(sel_rec2["scheme_code"])
    if not nav_df_sel.empty:
        nav_30 = nav_df_sel[nav_df_sel["date"] >= nav_df_sel["date"].max() - pd.Timedelta(days=365)]
        fig_nav = px.line(
            nav_30, x="date", y="nav",
            title  = f"1-Year NAV Trend — {sel2[:40]}",
            labels = {"date": "", "nav": "NAV (₹)"},
            color_discrete_sequence = ["#3b82f6"],
        )
        fig_nav.update_traces(line_width=2)
        apply_theme(fig_nav)
        st.plotly_chart(fig_nav, use_container_width=True)

# ─────────────────────────────────────────────
# F. Overlap Analysis
# ─────────────────────────────────────────────
with tabs[3]:
    st.markdown("""<div class="section-header"><h2>Portfolio Overlap Matrix</h2><span class="section-tag">F</span></div>""", unsafe_allow_html=True)

    st.markdown("""<div class="info-box">
    Overlap is computed via Jaccard similarity of top-10 holdings names across each pair of schemes.
    100% = identical top-10 holdings. N/A = holdings data unavailable.
    </div>""", unsafe_allow_html=True)

    if not overlap_df.empty and not overlap_df.isnull().all().all():
        fig_ov = px.imshow(
            overlap_df,
            text_auto   = ".0f",
            color_continuous_scale = "Blues",
            title       = "Overlap % (Top-10 Holdings Jaccard Similarity)",
            aspect      = "auto",
        )
        fig_ov.update_layout(
            height        = 600,
            paper_bgcolor = "#0f172a",
            font          = dict(family="Inter", color="#94a3b8", size=9),
        )
        st.plotly_chart(fig_ov, use_container_width=True)

        # Most / least similar
        ov_flat = overlap_df.copy()
        np.fill_diagonal(ov_flat.values, np.nan)
        ov_stack = ov_flat.stack().dropna()
        if not ov_stack.empty:
            most_sim  = ov_stack.idxmax()
            least_sim = ov_stack.idxmin()
            oc1, oc2 = st.columns(2)
            oc1.success(f"🤝 Most similar: **{most_sim[0]}** & **{most_sim[1]}** ({ov_stack.max():.0f}%)")
            oc2.warning(f"🔀 Least similar: **{least_sim[0]}** & **{least_sim[1]}** ({ov_stack.min():.0f}%)")
    else:
        st.info("Overlap matrix will populate once MFAPI returns portfolio holdings for the selected schemes.")

# ─────────────────────────────────────────────
# G. Benchmark Comparison
# ─────────────────────────────────────────────
with tabs[4]:
    st.markdown("""<div class="section-header"><h2>Benchmark Comparison — Nifty 50</h2><span class="section-tag">G</span></div>""", unsafe_allow_html=True)

    bench_data = []
    for r in records:
        bench_data.append({
            "Scheme"       : r["scheme_name"][:35],
            "Fund 1Y (%)"  : r.get("ret_1y"),
            "Nifty 1Y (%)" : r.get("nifty_1y"),
            "Alpha 1Y (%)" : r.get("alpha_1y"),
            "Fund 3Y (%)"  : r.get("cagr_3y"),
            "Nifty 3Y (%)" : r.get("nifty_3y"),
            "Alpha 3Y (%)" : r.get("alpha_3y"),
            "Fund 5Y (%)"  : r.get("cagr_5y"),
            "Nifty 5Y (%)" : r.get("nifty_5y"),
            "Alpha 5Y (%)" : r.get("alpha_5y"),
        })
    bench_df = pd.DataFrame(bench_data)

    # 1Y chart
    b1_melt = bench_df[["Scheme","Fund 1Y (%)","Nifty 1Y (%)"]].dropna(subset=["Fund 1Y (%)"])
    b1_melt = b1_melt.melt(id_vars="Scheme", var_name="Source", value_name="Return (%)")
    fig_b1  = px.bar(
        b1_melt, x="Scheme", y="Return (%)", color="Source",
        barmode="group", title="1-Year Return vs Nifty 50",
        color_discrete_map={"Fund 1Y (%)":"#3b82f6","Nifty 1Y (%)":"#f59e0b"},
    )
    fig_b1.update_xaxes(tickangle=-30)
    apply_theme(fig_b1)
    st.plotly_chart(fig_b1, use_container_width=True)

    # Alpha bars
    alpha_df = bench_df[["Scheme","Alpha 1Y (%)","Alpha 3Y (%)","Alpha 5Y (%)"]].dropna(subset=["Alpha 1Y (%)"])
    if not alpha_df.empty:
        alpha_melt = alpha_df.melt(id_vars="Scheme", var_name="Period", value_name="Alpha (%)")
        colors = alpha_melt["Alpha (%)"].apply(lambda x: "#22c55e" if x >= 0 else "#f87171")
        fig_alpha = px.bar(
            alpha_melt, x="Scheme", y="Alpha (%)", color="Period",
            barmode="group", title="Alpha Generated over Nifty 50",
            color_discrete_sequence=["#3b82f6","#a78bfa","#22c55e"],
        )
        fig_alpha.add_hline(y=0, line_dash="dash", line_color="#475569")
        fig_alpha.update_xaxes(tickangle=-30)
        apply_theme(fig_alpha)
        st.plotly_chart(fig_alpha, use_container_width=True)

    # Table
    def _style_alpha(v):
        if pd.isna(v): return ""
        return "color:#22c55e;font-weight:600" if v >= 0 else "color:#f87171;font-weight:600"

    alpha_cols = [c for c in bench_df.columns if "Alpha" in c]
    st.dataframe(
        bench_df.style
        .format({c: "{:.2f}" for c in bench_df.columns if "(" in c}, na_rep="—")
        .map(_style_alpha, subset=alpha_cols)
        use_container_width=True, height=400
    )

# ─────────────────────────────────────────────
# H. Risk Analysis
# ─────────────────────────────────────────────
with tabs[5]:
    st.markdown("""<div class="section-header"><h2>Risk Analysis</h2><span class="section-tag">H</span></div>""", unsafe_allow_html=True)

    risk_data = []
    for r in records:
        std = r.get("std_dev")
        r1y = r.get("ret_1y")
        risk_data.append({
            "Scheme"     : r["scheme_name"][:35],
            "Std Dev (%)" : std,
            "1Y Return (%)" : r1y,
            "Category"   : r.get("category",""),
        })
    risk_df = pd.DataFrame(risk_data).dropna(subset=["Std Dev (%)","1Y Return (%)"])

    if not risk_df.empty:
        # Risk-Return scatter
        fig_rr = px.scatter(
            risk_df,
            x     = "Std Dev (%)",
            y     = "1Y Return (%)",
            text  = "Scheme",
            color = "Category",
            size  = [14] * len(risk_df),
            title = "Risk vs Return (1Y Return vs 3Y Std Dev)",
            color_discrete_sequence = PALETTE,
        )
        fig_rr.update_traces(textposition="top center", textfont_size=9, marker=dict(line=dict(width=1.5, color="white")))
        fig_rr.add_hline(y=0,               line_dash="dot", line_color="#475569", annotation_text="0%")
        fig_rr.add_vline(x=risk_df["Std Dev (%)"].mean(), line_dash="dot", line_color="#475569", annotation_text="Avg risk")
        apply_theme(fig_rr, height=460)
        st.plotly_chart(fig_rr, use_container_width=True)

        # Standard deviation bars
        std_sorted = risk_df.sort_values("Std Dev (%)", ascending=True)
        fig_std = px.bar(
            std_sorted, x="Std Dev (%)", y="Scheme",
            orientation="h",
            color="Std Dev (%)",
            color_continuous_scale="RdYlGn_r",
            title="Volatility Ranking (lower is less volatile)",
        )
        apply_theme(fig_std, height=420)
        st.plotly_chart(fig_std, use_container_width=True)
    else:
        st.info("Risk data computing — requires at least 20 NAV data points.")

    # Risk table
    st.markdown("#### Risk Metrics Summary")
    rt_df = df_clean[["Scheme Name","Category","Std Dev (%)","1Y Return (%)","Alpha 1Y (%)"]].copy()
    def risk_label(v):
        if pd.isna(v): return "N/A"
        if v < 12: return "🟢 Low"
        if v < 18: return "🟡 Moderate"
        return "🔴 High"
    rt_df["Risk Rating"] = rt_df["Std Dev (%)"].apply(risk_label)
    st.dataframe(rt_df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# I. Charts
# ─────────────────────────────────────────────
with tabs[6]:
    st.markdown("""<div class="section-header"><h2>Analytics Charts</h2><span class="section-tag">I</span></div>""", unsafe_allow_html=True)

    # ── CAGR Comparison
    cagr_df = df_clean[["Scheme Name","1Y Return (%)","3Y CAGR (%)","5Y CAGR (%)"]].copy()
    cagr_df["Scheme"] = cagr_df["Scheme Name"].str[:32]
    cagr_melt = cagr_df.drop(columns="Scheme Name").melt(id_vars="Scheme", var_name="Period", value_name="CAGR (%)")

    fig_cagr = px.bar(
        cagr_melt, x="Scheme", y="CAGR (%)", color="Period",
        barmode="group",
        title="Return Comparison — 1Y / 3Y CAGR / 5Y CAGR",
        color_discrete_sequence=["#3b82f6","#a78bfa","#22c55e"],
    )
    fig_cagr.update_xaxes(tickangle=-35)
    fig_cagr.add_hline(y=0, line_dash="dash", line_color="#475569")
    apply_theme(fig_cagr, height=420)
    st.plotly_chart(fig_cagr, use_container_width=True)

    # ── NAV Trends (multi-scheme selector)
    st.markdown("#### Multi-Scheme NAV Trend")
    trend_sel = st.multiselect(
        "Select schemes to compare",
        scheme_names,
        default=scheme_names[:4],
        key="nav_trend_sel",
    )
    if trend_sel:
        fig_nav2 = go.Figure()
        for sname in trend_sel:
            idx = scheme_names.index(sname)
            nav_df_t = fetch_nav_history(records[idx]["scheme_code"])
            if not nav_df_t.empty:
                # normalise to 100
                nav_df_t = nav_df_t[nav_df_t["date"] >= nav_df_t["date"].max() - pd.Timedelta(days=5*365)].copy()
                nav_df_t["nav_norm"] = nav_df_t["nav"] / nav_df_t["nav"].iloc[0] * 100
                fig_nav2.add_trace(go.Scatter(
                    x=nav_df_t["date"], y=nav_df_t["nav_norm"],
                    name=sname[:30], mode="lines", line=dict(width=2),
                ))
        fig_nav2.update_layout(
            title="5-Year NAV Trend (Rebased to 100)",
            yaxis_title="Indexed NAV",
        )
        apply_theme(fig_nav2, height=420)
        st.plotly_chart(fig_nav2, use_container_width=True)

    # ── Category distribution
    cat_dist = df_clean["Category"].value_counts().reset_index()
    cat_dist.columns = ["Category","Count"]
    fig_cat = px.pie(
        cat_dist, names="Category", values="Count",
        title="Scheme Category Distribution",
        color_discrete_sequence=PALETTE,
        hole=0.45,
    )
    apply_theme(fig_cat, height=380)
    st.plotly_chart(fig_cat, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.75rem;padding:12px 0;">
  Data sourced from <strong>AMFI India</strong>, <strong>MFAPI.in</strong>, and <strong>Yahoo Finance</strong> (Nifty 50).
  All returns are calculated from official NAV data. Past performance is not indicative of future results.
  Last fetched: {fetched_at.strftime('%d %b %Y %I:%M %p IST')} | Auto-refresh: {refresh_interval}
</div>
""", unsafe_allow_html=True)
