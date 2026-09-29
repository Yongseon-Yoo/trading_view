from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_journey(tmp_path, monkeypatch):
    monkeypatch.setenv("YS_DB_PATH", str(tmp_path / "ui.db"))
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KIWOOM_APP_KEY", "KIWOOM_APP_SECRET"):
        monkeypatch.setenv(key, "")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "하루의 시작, 시장의 단서"
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric) >= 3
    app.sidebar.radio[0].set_value("장 마감 리포트").run()
    app.button[0].click().run()
    assert not app.exception
    assert len(app.dataframe) == 2
    app.sidebar.radio[0].set_value("리포트 기록").run()
    assert not app.exception
    assert len(app.selectbox) >= 3
    app.sidebar.radio[0].set_value("관심 종목·설정").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("장중 관심종목").run()
    assert not app.exception
