import pytest

from src.config import Settings, credential_mode
from src.repositories.database import Database


def test_credential_modes_and_no_secret_repr():
    assert credential_mode("", "") == "sample"
    assert credential_mode("key", "") == "invalid"
    assert credential_mode("key", "secret") == "api"
    assert "private-secret" not in repr(Settings(naver_secret="private-secret"))


def test_seed_only_once_and_delete_persists(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.seed_once(True)
    assert len(db.stocks()) == len(db.themes()) == 3
    for stock in db.stocks():
        db.delete_stock(stock["code"])
    for theme in db.themes():
        db.delete_theme(theme["name"])
    db.seed_once(True)
    assert db.stocks() == db.themes() == []


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
