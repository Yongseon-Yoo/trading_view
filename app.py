import streamlit as st

from src.config import Settings
from src.domain.models import now_kst
from src.providers.factory import providers
from src.repositories.database import Database
from src.ui import evening, history, live, morning
from src.ui import settings as settings_ui
from src.ui.common import apply_style

st.set_page_config(page_title="주식대시보드YS", page_icon="◈", layout="wide")
apply_style()


@st.cache_resource
def resources():
    config = Settings.load()
    database = Database(config.db_path)
    news, market = providers(config)
    return config, database, news, market


config, db, news, market = resources()
with st.sidebar:
    st.markdown('<div class="brand-mark">YS<span>MARKET DESK</span></div>', unsafe_allow_html=True)
    st.title("주식대시보드YS")
    st.caption("뉴스와 수급, 나의 시선으로.")
    st.divider()
    page = st.radio(
        "워크스페이스",
        ["아침 브리핑", "장중 관심종목", "장 마감 리포트", "리포트 기록", "관심 종목·설정"],
        label_visibility="collapsed",
        key="page",
    )
    st.divider()
    st.caption("데이터 연결")
    st.markdown(f"**뉴스** · {news.label}")
    st.markdown(f"**시장** · {market.label}")
    st.caption("로컬 저장 · Asia/Seoul\n\n리포트는 생성 당시 내용을 보관합니다.")

if page != "장중 관심종목" and "live_session" in st.session_state:
    st.session_state.live_session.stop()
    del st.session_state.live_session

st.caption(f"MY MARKET WORKSPACE  /  {now_kst():%Y.%m.%d}  /  KRX")
if page == "아침 브리핑":
    morning.render(db, news, market, config)
elif page == "장중 관심종목":
    live.render(db, config, market)
elif page == "장 마감 리포트":
    evening.render(db, market, config)
elif page == "리포트 기록":
    history.render(db)
else:
    settings_ui.render(db, config)
