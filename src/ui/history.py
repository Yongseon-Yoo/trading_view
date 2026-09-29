import streamlit as st

from src.ui.common import date_label, title
from src.ui.evening import show as show_evening
from src.ui.morning import show as show_morning


def render(db):
    title("기록에서 다시 읽는 시장", "생성 당시의 데이터와 수집 상태를 그대로 보관합니다.")
    reports = db.reports()
    if not reports:
        st.info("아직 저장된 리포트가 없습니다. 아침 또는 장 마감 리포트를 생성해보세요.")
        return
    a, b, c = st.columns([1, 1, 2])
    selected_date = a.selectbox("날짜", sorted({r["report_date"] for r in reports}, reverse=True))
    kind = b.selectbox(
        "종류",
        ["morning", "evening"],
        format_func=lambda x: "아침 브리핑" if x == "morning" else "장 마감 리포트",
    )
    versions = [r for r in reports if r["report_date"] == selected_date and r["kind"] == kind]
    if not versions:
        st.info("선택한 날짜에 해당 종류의 리포트가 없습니다.")
        return
    chosen = c.selectbox(
        "생성 시각", versions, format_func=lambda r: f"{date_label(r['generated_at'])} · {r['id'][:6]}"
    )
    report = db.report(chosen["id"])
    (show_morning if kind == "morning" else show_evening)(report)
