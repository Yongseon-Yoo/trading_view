import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.domain.models import now_kst
from src.services.morning_brief import build_morning
from src.ui.common import TEAL, chart_style, date_label, latest, statuses, title


def render(db, news, market, config):
    title("하루의 시작, 시장의 단서", "관심 종목과 테마의 밤사이 소식. 의미와 판단은 직접 살펴보세요.")
    if config.news_mode != "api":
        st.warning("네이버 뉴스 API 인증정보가 없습니다. .env 설정을 확인하세요.")
    if config.market_mode != "api":
        st.info("키움 인증정보가 없어 가격 카드는 표시되지 않습니다.")
    col, action = st.columns([3, 1])
    col.caption("MORNING BRIEF  /  직전 거래일 장 마감 이후")
    if action.button(
        "아침 브리핑 생성",
        type="primary",
        use_container_width=True,
        disabled=config.news_mode != "api" or not (db.stocks() or db.themes()),
    ):
        with st.spinner("뉴스와 가격을 모아 리포트를 저장하고 있어요…"):
            report = build_morning(db.stocks(), db.themes(), news, market, now_kst())
            db.save_report(report)
        st.success("브리핑을 날짜별 기록에 저장했어요.")
    report = latest(db, "morning")
    if report:
        show(report)
    else:
        a, b, c = st.columns(3)
        a.metric("관심 종목", f"{len(db.stocks())}개")
        b.metric("관심 테마", f"{len(db.themes())}개")
        c.metric("저장된 브리핑", "0개")
        with st.container(border=True):
            st.subheader("첫 브리핑을 만들어보세요")
            st.write("위의 생성 버튼을 누르면 가격 카드, 시간대별 기사량과 원문 목록이 함께 나타납니다.")
            st.caption("관심 종목·설정에서 종목과 테마를 자유롭게 바꿀 수 있어요.")
            st.write(" · ".join(s["name"] for s in db.stocks()) or "등록한 관심 종목이 없습니다.")


def show(report: dict):
    statuses(report)
    st.caption(
        f"{report['news_source']}  |  {date_label(report['window_start'])} → {date_label(report['window_end'])}"
    )
    for offset in range(0, len(report["quotes"]), 3):
        columns = st.columns(3)
        for col, q in zip(columns, report["quotes"][offset : offset + 3], strict=False):
            with col:
                delta = None if q["rate"] is None else f"{q['rate']:+.2f}% · {q['change']:+,}원"
                st.metric(q["name"], f"{q['price']:,}원", delta)
                st.caption(
                    f"{q['code']} · {q['label']} · 기준일 {q['price_date']}\n\n조회 {date_label(q['fetched_at'])}"
                )
    st.divider()
    tabs = st.tabs(["관심 종목 뉴스", "관심 테마 뉴스"])
    for tab, kind in zip(tabs, ["종목", "테마"], strict=True):
        with tab:
            sections = [s for s in report["sections"] if s["kind"] == kind]
            if not sections:
                st.info(f"등록된 {kind}가 없습니다.")
                continue
            chosen = st.selectbox(
                f"{kind} 선택",
                range(len(sections)),
                format_func=lambda i, items=sections: items[i]["name"],
                key=f"news-{kind}-{report['generated_at']}",
            )
            show_section(sections[chosen], key=f"morning-chart-{kind}-{report['generated_at']}-{chosen}")


def show_section(section: dict, key: str):
    st.subheader(section["name"])
    if section["failed"]:
        st.error("뉴스 수집 실패 · 아래 수집 상태를 확인하세요.")
    if section["warnings"]:
        with st.expander("수집 범위 및 오류", expanded=section["failed"]):
            for warning in section["warnings"]:
                st.warning(warning)
    if not section["complete"]:
        st.caption("일부 수집 결과입니다. 0건인 구간도 실제 기사가 없다는 뜻은 아닙니다.")
    a, b, c = st.columns(3)
    a.metric("장 마감 이후 수집 기사", f"{section['total']}건")
    b.metric("최근 6시간", f"{section['last_six_hours']}건")
    c.metric("최근 1시간", f"{section['last_hour']}건")
    frame = pd.DataFrame(section["buckets"])
    fig = go.Figure(
        go.Bar(
            x=frame["time"],
            y=frame["count"],
            marker_color=TEAL,
            customdata=frame[["issues", "partial"]],
            hovertemplate="%{x}<br>기사 %{y}건<br>유사 기사 묶음 %{customdata[0]}개<extra></extra>",
        )
    )
    st.plotly_chart(
        chart_style(fig, 250, "발행 시각 · KST", "수집 기사 수"),
        use_container_width=True,
        key=key,
    )
    st.caption("동일 URL은 1건으로 계산 · 양 끝 시간대는 조회 범위 내 기사만 포함 · 유사 제목 묶음은 추정치")
    if not section["groups"] and not section["failed"]:
        st.info("새로운 뉴스 없음")
    for group in section["groups"]:
        article = group[0]
        with st.container(border=True):
            st.write(article["title"])
            st.caption(
                f"{article['source']}  ·  {date_label(article['published_at'])}  ·  관련 기사 {len(group)}건"
            )
            st.link_button("원문 보기 ↗", article["url"])
            if len(group) > 1:
                with st.expander("묶인 기사 보기"):
                    for item in group[1:]:
                        st.write(item["title"])
                        st.caption(f"{item['source']} · {date_label(item['published_at'])}")
                        st.link_button("기사 열기 ↗", item["url"])
