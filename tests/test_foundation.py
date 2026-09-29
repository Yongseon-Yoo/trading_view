import pytest

from src.config import Settings, credential_mode
from src.domain.models import ProviderError
from src.providers.factory import providers
from src.repositories.database import Database


def test_credential_modes_and_no_secret_repr():
    assert credential_mode("", "") == "missing"
    assert credential_mode("key", "") == "invalid"
    assert credential_mode("key", "secret") == "api"
    assert "private-secret" not in repr(Settings(naver_secret="private-secret"))


def test_missing_credentials_never_select_generated_data():
    news, market = providers(Settings())
    assert "인증정보 없음" in news.label
    assert "인증정보 없음" in market.label
    with pytest.raises(ProviderError, match="인증정보가 없습니다"):
        news.search("삼성전자", None, None)
    with pytest.raises(ProviderError, match="인증정보가 없습니다"):
        market.quote("005930", "삼성전자", None)


def test_empty_database_does_not_add_example_watchlist(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    assert db.stocks() == db.themes() == []


def test_legacy_sample_report_is_hidden_not_deleted(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    old_id = db.save_report(
        {
            "kind": "morning",
            "report_date": "2026-09-29",
            "generated_at": "2026-09-29T09:00:00+09:00",
            "news_source": "샘플 뉴스 · 가상 기사",
        }
    )
    new_id = db.save_report(
        {
            "kind": "morning",
            "report_date": "2026-09-30",
            "generated_at": "2026-09-30T09:00:00+09:00",
            "news_source": "네이버 뉴스 검색 결과 기준",
        }
    )
    assert [row["id"] for row in db.reports()] == [new_id]
    assert db.report(old_id)["news_source"].startswith("샘플")


def test_watchlist_and_snapshot_are_independent(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.save_stock("005930", "삼성전자")
    db.save_stock("005930", "삼성전자 수정")
    assert len(db.stocks()) == 1
    with pytest.raises(ValueError):
        db.save_stock("bad", "회사")
    db.save_theme("반도체", ["HBM", "HBM"], ["005930"])
    assert db.themes()[0]["keywords"] == ["HBM"]
    report = dict(
        kind="morning", report_date="2026-09-29", generated_at="2026-09-29T09:00:00+09:00", stocks=db.stocks()
    )
    first = db.save_report(report)
    report["stocks"] = []
    second = db.save_report(report)
    db.delete_stock("005930")
    assert db.report(first)["stocks"]
    assert not db.report(second)["stocks"]
    assert db.themes()[0]["codes"] == []
