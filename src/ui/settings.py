import streamlit as st

from src.ui.common import title


def render(db, config):
    title("나의 관심 목록", "궁금한 종목과 뉴스 키워드를 직접 관리하세요.")
    stock_tab, theme_tab, config_tab = st.tabs(["관심 종목", "관심 테마", "연결 설정"])
    with stock_tab:
        with st.form("stock_form", clear_on_submit=True):
            a, b = st.columns(2)
            code = a.text_input("종목코드", placeholder="005930", max_chars=6)
            name = b.text_input("종목명", placeholder="삼성전자", max_chars=60)
            if st.form_submit_button("종목 저장", type="primary"):
                try:
                    db.save_stock(code, name)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        st.caption("이미 있는 종목코드로 저장하면 이름을 수정합니다.")
        for stock in db.stocks():
            with st.container(border=True):
                a, b = st.columns([5, 1])
                a.write(f"{stock['name']} · {stock['code']}")
                if b.button("삭제", key=f"stock-delete-{stock['code']}"):
                    db.delete_stock(stock["code"])
                    st.rerun()
    with theme_tab:
        stocks = db.stocks()
        names = {s["code"]: s["name"] for s in stocks}
        themes = db.themes()
        editing = st.selectbox("편집할 테마", ["새 테마"] + [t["name"] for t in themes])
        existing = next(
            (t for t in themes if t["name"] == editing), {"name": "", "keywords": [], "codes": []}
        )
        with st.form(f"theme-form-{editing}"):
            name = st.text_input("테마명", existing["name"], disabled=editing != "새 테마")
            keywords = st.text_area("검색 키워드 · 한 줄에 하나", "\n".join(existing["keywords"]))
            codes = st.multiselect(
                "연결할 관심 종목", list(names), default=existing["codes"], format_func=lambda c: names[c]
            )
            if st.form_submit_button("테마 저장", type="primary"):
                try:
                    db.save_theme(name, keywords.splitlines(), codes)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        for theme in themes:
            with st.container(border=True):
                a, b = st.columns([5, 1])
                a.write(theme["name"])
                a.caption(" · ".join(theme["keywords"]))
                a.caption("연결 종목: " + (", ".join(names.get(c, c) for c in theme["codes"]) or "없음"))
                if b.button("삭제", key=f"theme-delete-{theme['name']}"):
                    db.delete_theme(theme["name"])
                    st.rerun()
    with config_tab:
        modes = {
            "sample": "샘플 데이터",
            "api": "API 키 설정됨 · 연결은 조회 시 확인",
            "invalid": "설정 불완전",
        }
        st.write("뉴스: " + modes[config.news_mode])
        st.write("시장: " + modes[config.market_mode])
        st.write("키움 환경: " + config.kiwoom_env)
        st.info(
            "프로젝트의 .env.example을 .env로 복사해 발급받은 키를 채우고 앱을 재시작하세요. 네이버는 NAVER API HUB 뉴스 검색 Application의 키를 사용합니다."
        )
        st.code(
            "NAVER_CLIENT_ID=\nNAVER_CLIENT_SECRET=\nKIWOOM_APP_KEY=\nKIWOOM_APP_SECRET=\nKIWOOM_ENV=mock",
            language="ini",
        )
        st.caption("키가 모두 비어 있으면 샘플 모드입니다. 일부만 입력하면 실제 호출을 차단합니다.")
