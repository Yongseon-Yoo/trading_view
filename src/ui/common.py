import pandas as pd
import plotly.graph_objects as go
import streamlit as st

TEAL = "#137E73"
RED = "#D65C54"
BLUE = "#5279BA"


def apply_style():
    st.markdown(
        """<style>
    .block-container {padding-top:4rem;padding-bottom:3rem;max-width:1500px;}
    h1 {font-size:2.3rem!important;letter-spacing:-.07rem;font-weight:750!important;}
    h2 {letter-spacing:-.035rem;}
    [data-testid="stSidebar"] {border-right:1px solid #e0e7ec;}
    [data-testid="stMetric"] {background:white;border:1px solid #e0e7ec;border-radius:14px;padding:18px 20px;}
    [data-testid="stMetricValue"] {font-size:1.75rem;letter-spacing:-.03rem;}
    [data-testid="stMetricLabel"] {color:#687c88;}
    .brand-mark {font-size:2.3rem;font-weight:850;color:#137e73;letter-spacing:-2px;}
    .brand-mark span {font-size:.65rem;letter-spacing:2px;margin-left:12px;color:#607783;}
    [data-testid="stSidebar"] h1 {font-size:1.15rem!important;letter-spacing:-.03rem;}
    [data-testid="stSidebar"] [role="radiogroup"] label {padding:9px 8px;}
    .stButton button {border-radius:9px;font-weight:600;}
    [data-testid="stExpander"] {background:white;}
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
        margin=dict(l=12, r=24, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", color="#435967", size=12),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=1.15, x=0),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, zerolinecolor="#96AAB5")
    fig.update_yaxes(gridcolor="#E4EBF0", zerolinecolor="#96AAB5")
    return fig


def statuses(report: dict):
    st.caption(f"저장 기준 · {date_label(report['generated_at'])} KST  |  {report.get('market_source', '')}")
    if "샘플" in str(report.get("market_source", "")) or "샘플" in str(report.get("news_source", "")):
        st.warning("샘플 데이터가 포함된 시연용 리포트입니다. 실제 시세·보도가 아닙니다.")
    if report.get("errors"):
        with st.expander(f"수집 상태 · {len(report['errors'])}건 확인 필요"):
            for error in report["errors"]:
                st.warning(error)


def latest(db, kind: str):
    for row in db.reports():
        if row["kind"] == kind:
            return db.report(row["id"])
    return None
