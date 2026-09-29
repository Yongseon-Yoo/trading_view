import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.domain.models import ProviderError, now_kst
from src.services.evening_flow import RANKINGS, build_evening
from src.ui.common import BLUE, RED, chart_style, latest, statuses, title


def render(db, market):
    title("오늘, 거래가 모인 곳", "외국인과 기관의 매매를 시장별로 정리해 확인하세요.")
    col, action = st.columns([3, 1])
    col.caption("CLOSING REPORT  /  순매수금액 · 거래대금 TOP 10")
    if action.button("장 마감 수급 리포트 생성", type="primary", use_container_width=True):
        try:
            with st.spinner("시장별 수급과 업종을 조회하고 있어요…"):
                report = build_evening(market, now_kst())
                db.save_report(report)
            st.success("수급 리포트를 저장했어요.")
        except ProviderError as exc:
            st.error(str(exc))
    report = latest(db, "evening")
    if report:
        show(report)
    else:
        with st.container(border=True):
            st.subheader("시장의 하루를 한 화면에")
            st.write("리포트를 생성하면 코스피·코스닥의 투자자별 순매수·순매도와 업종 분포를 볼 수 있습니다.")
            st.caption("과거 자료는 리포트 기록에서 열람 · 조회 시점의 잠정 데이터")


def show(report):
    statuses(report)
    st.caption(f"기준 거래일 {report['report_date']} · {report['market_state']} · {report['notice']}")
    for tab, market in zip(st.tabs(["KOSPI · 코스피", "KOSDAQ · 코스닥"]), ("KOSPI", "KOSDAQ"), strict=True):
        with tab:
            for investor, label in (("foreign", "외국인"), ("institution", "기관")):
                st.subheader(f"{label} · Top 10 종목 내 업종 분포")
                groups = report["sectors"][market].get(investor, [])
                if not groups:
                    st.info("표시할 업종 집계가 없습니다.")
                    continue
                fig = go.Figure()
                for side, name, color in (("buy", "순매수 +", RED), ("sell", "순매도 −", BLUE)):
                    subset = [g for g in groups if g["side"] == side]
                    fig.add_trace(
                        go.Bar(
                            y=[g["sector"] for g in subset],
                            x=[g["amount"] / 1e8 for g in subset],
                            orientation="h",
                            name=name,
                            marker_color=color,
                            text=[f"{g['amount'] / 1e8:+,.1f}억" for g in subset],
                            customdata=[[g["amount"], g["count"], ", ".join(g["names"])] for g in subset],
                            hovertemplate="%{y}<br>%{customdata[0]:,}원<br>%{customdata[1]}종목 · %{customdata[2]}<extra></extra>",
                        )
                    )
                fig.update_layout(barmode="relative")
                st.plotly_chart(chart_style(fig, 320, "순매수금액 · 억원"), use_container_width=True)
                st.caption("전체 업종 수급이 아닌 순매수·순매도 Top 10 포함 종목 기준 · 매수/매도 각각 집계")
            st.subheader("종목별 원자료")
            rank = st.selectbox(
                "순위 선택",
                RANKINGS,
                format_func=lambda r: r[2],
                key=f"rank-{market}-{report['generated_at']}",
            )
            key = f"{rank[0]}_{rank[1]}"
            rows = report["tables"][market].get(key, [])
            if not rows:
                st.info("수집된 순위가 없습니다. 상단 수집 상태를 확인하세요.")
            else:
                table = pd.DataFrame(
                    [
                        {
                            "순위": i + 1,
                            "종목": r["name"],
                            "코드": r["code"],
                            "업종": r["sector"],
                            "금액(억원)": r["amount"] / 1e8,
                            "정확한 금액(원)": r["amount"],
                            "현재가(원)": r["price"],
                            "등락률(%)": r["rate"],
                            "거래량(주)": r["volume"],
                        }
                        for i, r in enumerate(rows)
                    ]
                )
                st.dataframe(
                    table,
                    hide_index=True,
                    use_container_width=True,
                    column_config={"금액(억원)": st.column_config.NumberColumn(format="%.2f")},
                )
                st.caption(
                    "미제공 값은 빈칸으로 표시합니다. 수급 순위 API에는 현재가·거래량이 포함되지 않을 수 있습니다."
                )
