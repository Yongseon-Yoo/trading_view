import plotly.graph_objects as go
import streamlit as st

from src.providers.kiwoom_realtime import KiwoomRealtimeProvider
from src.services.live import LiveSession
from src.ui.common import ACCENT, chart_style, date_label, title


def render(db, config, market):
    title("실시간 관심종목", "연결 이후의 체결 흐름 · 최근 5분 · 종목당 최대 300건")
    stocks = db.stocks()
    active = "live_session" in st.session_state
    if config.market_mode != "api":
        st.warning("키움 API 인증정보가 없습니다. .env 설정 후 앱을 재시작하세요.")
    st.caption("키움 KRX 체결을 구독합니다. 장이 닫혔거나 거래가 없으면 수신 대기합니다.")
    a, b, _ = st.columns([1, 1, 3])
    if a.button(
        "실시간 시작",
        type="primary",
        disabled=active or not stocks or config.market_mode != "api",
        use_container_width=True,
    ):
        provider = KiwoomRealtimeProvider(market.client)
        session = LiveSession(provider, [s["code"] for s in stocks])
        st.session_state.live_session = session
        session.start()
        st.rerun()
    if b.button("실시간 중지", disabled=not active, use_container_width=True):
        st.session_state.live_session.stop()
        del st.session_state.live_session
        st.rerun()
    if not stocks:
        st.info("관심 종목을 먼저 등록하세요.")
    if "live_session" not in st.session_state:
        st.info("실시간 시작을 누르면 종목 카드와 가격 그래프가 갱신됩니다.")
        return
    live_panel(stocks)


@st.fragment(run_every=1)
def live_panel(stocks):
    session = st.session_state.get("live_session")
    if not session:
        return
    session.touch()
    status, error, buffers = session.snapshot()
    st.caption(f"● {status}  |  체결 데이터는 메모리에서만 사용됩니다.")
    if error:
        st.warning(error)
    for offset in range(0, len(stocks), 3):
        columns = st.columns(3)
        for col, stock in zip(columns, stocks[offset : offset + 3], strict=False):
            with col:
                rows = buffers.get(stock["code"], [])
                if not rows:
                    st.metric(stock["name"], "수신 대기")
                    continue
                tick = rows[-1]
                st.metric(stock["name"], f"{tick.price:,}원", f"{tick.rate:+.2f}%")
                st.caption(
                    f"체결 {tick.volume:+,}주 · 누적 {tick.cumulative_volume:,}주\n\n마지막 체결 {date_label(tick.executed_at.isoformat())}"
                )
                fig = go.Figure(
                    go.Scatter(
                        x=[r.executed_at for r in rows],
                        y=[r.price for r in rows],
                        mode="lines+markers",
                        line=dict(color=ACCENT, width=2),
                        marker=dict(size=3),
                        fill="tozeroy",
                        fillcolor="rgba(36,196,229,.10)",
                    )
                )
                fig.update_yaxes(
                    rangemode="normal",
                    range=[min(r.price for r in rows) * 0.998, max(r.price for r in rows) * 1.002],
                )
                st.plotly_chart(
                    chart_style(fig, 230, "체결 시각", "원"),
                    use_container_width=True,
                    key=f"live-chart-{stock['code']}",
                )
