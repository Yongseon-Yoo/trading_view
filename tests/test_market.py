from datetime import datetime

import httpx
import pytest

from src.domain.models import KST, ProviderError
from src.providers.kiwoom import KiwoomClient, KiwoomMarketProvider, number
from src.providers.sample import SampleMarketProvider
from src.services.evening_flow import build_evening, group_sectors


def test_units_and_direction():
    assert number("+1,234", 1_000_000) == 1_234_000_000
    assert number("-12.5", 1_000_000) == -12_500_000
    with pytest.raises(ProviderError):
        number("")
    with pytest.raises(ProviderError):
        number("NaN")


def test_kiwoom_request_and_parsing(monkeypatch):
    monkeypatch.setattr("src.providers.kiwoom.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"token": "test-token", "return_code": 0})
        api = request.headers["api-id"]
        if api == "ka10099":
            return httpx.Response(
                200, json={"list": [{"code": "005930", "upName": "전기·전자", "lastPrice": "70000"}]}
            )
        return httpx.Response(
            200,
            json={"opmr_invsr_trde_upper": [{"stk_cd": "005930", "stk_nm": "삼성전자", "netslmt": "123"}]},
        )

    client = KiwoomClient("key", "secret", "mock", httpx.Client(transport=httpx.MockTransport(handler)))
    provider = KiwoomMarketProvider(client)
    rows = provider.ranks("KOSPI", "foreign", "sell")
    assert rows[0].amount == -123_000_000
    assert rows[0].raw_unit == "백만원"
    assert rows[0].sector == "전기·전자"
    assert b'"amt_qty_tp":"1"' in calls[1].content
    with pytest.raises(ProviderError):
        client.call("order", "/bad", {})


def test_all_markets_and_sector_buy_sell_separated():
    provider = SampleMarketProvider()
    result = build_evening(provider, datetime(2026, 9, 29, 19, tzinfo=KST))
    for market in ("KOSPI", "KOSDAQ"):
        assert len(result["tables"][market]) == 5
        assert all(len(table) == 10 for table in result["tables"][market].values())
        groups = result["sectors"][market]["foreign"]
        assert sum(g["amount"] for g in groups if g["side"] == "buy") > 0
        assert sum(g["amount"] for g in groups if g["side"] == "sell") < 0
    rows = provider.ranks("KOSPI", "foreign", "buy")
    assert sum(g["count"] for g in group_sectors(rows + rows, "buy")) == 10


def test_partial_rank_failure():
    class Partial(SampleMarketProvider):
        def ranks(self, market, investor, side):
            if investor == "institution":
                raise ProviderError("실패")
            return super().ranks(market, investor, side)

    result = build_evening(Partial(), datetime(2026, 9, 29, 19, tzinfo=KST))
    assert result["errors"]
    assert result["tables"]["KOSPI"]["foreign_buy"]
    assert not result["tables"]["KOSPI"]["institution_buy"]
