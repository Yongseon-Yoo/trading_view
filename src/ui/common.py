import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ACCENT = "#24C4E5"
POSITIVE = "#42D3A4"
NEGATIVE = "#FF7885"


def apply_style():
    st.markdown(
        """<style>
    :root {color-scheme: dark;}
    .block-container {padding-top:2.3rem;padding-bottom:3rem;max-width:1360px;}
    h1 {font-size:1.9rem!important;letter-spacing:-.045rem;font-weight:720!important;}
    h2 {font-size:1.24rem!important;letter-spacing:-.025rem;}
    h3 {font-size:1.05rem!important;letter-spacing:-.015rem;}
    p, li {line-height:1.55;}
    [data-testid="stCaptionContainer"] {color:#A5BAC6;}
    [data-testid="stSidebar"] {border-right:1px solid #20313E;}
    [data-testid="stSidebar"] .block-container {padding-top:2rem;}
    .sidebar-brand {font-size:1.45rem;font-weight:750;letter-spacing:-.045rem;color:#ECF5F8;padding:4px 0 2px;}
    [data-testid="stSidebar"] [role="radiogroup"] label {padding:8px 10px;border-radius:8px;transition:background .15s ease;}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#1B2B38;}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#183440;color:#24C4E5;}
    [data-testid="stMetric"] {background:#15232E;border:1px solid #2B4050;border-radius:12px;padding:15px 17px;}
    [data-testid="stMetricValue"] {font-size:1.42rem;letter-spacing:-.025rem;font-weight:700;}
    [data-testid="stMetricLabel"] {color:#A5BAC6;font-size:.83rem;}
    [data-testid="stMetricDelta"] {font-size:.78rem;}
    div[data-testid="stVerticalBlockBorderWrapper"] {background:#15232E;border-radius:12px;}
    [data-testid="stExpander"] {border:1px solid #2B4050;border-radius:10px;background:#15232E;}
    [data-testid="stDataFrame"] {border:1px solid #2B4050;border-radius:10px;overflow:hidden;}
    .stButton button {border-radius:8px;font-weight:650;min-height:38px;}
    .stButton button[kind="primary"] {background:#24C4E5;color:#08141C;border:1px solid #24C4E5;}
    .stButton button[kind="primary"]:hover {background:#61DCF2;color:#08141C;border-color:#61DCF2;}
    [data-testid="stTabs"] button[aria-selected="true"] {color:#24C4E5;}
    hr {border-color:#2B4050!important;}
    @media (max-width: 760px) {
        .block-container {padding-top:1.4rem;padding-left:1rem;padding-right:1rem;}
        h1 {font-size:1.55rem!important;}
        [data-testid="stMetricValue"] {font-size:1.15rem;}
    }
    </style>""",
        unsafe_allow_html=True,
    )


def title(heading: str, description: str):
    st.title(heading)
    st.write(description)


def date_label(iso: str) -> str:
    return pd.Timestamp(iso).strftime("%m.%d %H:%M:%S")


def chart_style(fig: go.Figure, height: int = 300, x_title: str = "", y_title: str = "") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=20, t=28, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", color="#A5BAC6", size=12),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=1.15, x=0),
        hoverlabel=dict(bgcolor="#1B2B38", font_color="#ECF5F8"),
    )
    fig.update_xaxes(showgrid=False, zerolinecolor="#2B4050", linecolor="#2B4050")
    fig.update_yaxes(gridcolor="#253847", zerolinecolor="#2B4050", linecolor="#2B4050")
    return fig


def statuses(report: dict):
    st.caption(f"저장 기준 · {date_label(report['generated_at'])} KST  |  {report.get('market_source', '')}")
    if report.get("errors"):
        with st.expander(f"수집 상태 · {len(report['errors'])}건 확인 필요"):
            for error in report["errors"]:
                st.warning(error)


def latest(db, kind: str):
    for row in db.reports():
        if row["kind"] == kind:
            return db.report(row["id"])
    return None
