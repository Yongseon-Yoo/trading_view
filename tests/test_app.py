from datetime import datetime
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from src.domain.models import KST, Article
from src.repositories.database import Database
from src.services.evening_flow import build_evening
from src.services.morning_brief import build_morning
from tests.fakes import FakeMarketProvider, FakeNewsProvider


def test_dashboard_journey(tmp_path, monkeypatch):
    st.cache_resource.clear()
    path = str(tmp_path / "ui.db")
    monkeypatch.setenv("DASHBOARD_DB_PATH", path)
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KIWOOM_APP_KEY", "KIWOOM_APP_SECRET"):
        monkeypatch.setenv(key, "test-credential")
    db = Database(path)
    db.save_stock("005930", "삼성전자")
    db.save_theme("반도체", ["반도체"], ["005930"])
    # Both sections have identical zero-count charts, reproducing the former duplicate-ID crash.
    at = datetime(2026, 9, 29, 8, tzinfo=KST)
    db.save_report(build_morning(db.stocks(), db.themes(), FakeNewsProvider(), FakeMarketProvider(), at))
    db.save_report(build_evening(FakeMarketProvider(), datetime(2026, 9, 29, 19, tzinfo=KST)))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "아침 브리핑"
    assert len(app.metric) >= 3
    app.sidebar.radio[0].set_value("장 마감 리포트").run()
    assert not app.exception
    assert len(app.dataframe) == 2
    app.sidebar.radio[0].set_value("리포트 기록").run()
    assert not app.exception
    assert len(app.selectbox) >= 3
    app.sidebar.radio[0].set_value("관심 종목·설정").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("장중 관심종목").run()
    assert not app.exception


def test_missing_credentials_show_empty_state(tmp_path, monkeypatch):
    st.cache_resource.clear()
    path = str(tmp_path / "empty.db")
    monkeypatch.setenv("DASHBOARD_DB_PATH", path)
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KIWOOM_APP_KEY", "KIWOOM_APP_SECRET"):
        monkeypatch.setenv(key, "")
    db = Database(path)
    assert db.stocks() == db.themes() == []
    db.save_stock("005930", "삼성전자")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    assert db.reports() == []
    assert app.button[0].disabled
    app.sidebar.radio[0].set_value("장중 관심종목").run()
    assert not app.exception
    assert app.button[0].disabled


def test_long_news_list_keeps_remaining_issues_accessible(tmp_path, monkeypatch):
    st.cache_resource.clear()
    path = str(tmp_path / "news.db")
    monkeypatch.setenv("DASHBOARD_DB_PATH", path)
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KIWOOM_APP_KEY", "KIWOOM_APP_SECRET"):
        monkeypatch.setenv(key, "test-credential")
    db = Database(path)
    db.save_stock("005930", "삼성전자")
    at = datetime(2026, 9, 29, 19, tzinfo=KST)
    titles = [
        "반도체 생산 증설",
        "배터리 수출 증가",
        "조선업 신규 수주",
        "바이오 신약 승인",
        "항공 여객 회복",
        "게임업 신작 공개",
        "은행 예금 금리",
        "유통 매장 확장",
        "건설 주택 착공",
    ]
    articles = [
        Article(title, "example.com", at, f"https://example.com/{index}")
        for index, title in enumerate(titles)
    ]
    db.save_report(build_morning(db.stocks(), [], FakeNewsProvider(articles), FakeMarketProvider(), at))

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    assert any("나머지 1개 이슈 보기" in expander.label for expander in app.expander)
