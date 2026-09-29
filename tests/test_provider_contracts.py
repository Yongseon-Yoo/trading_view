import asyncio
import json
from datetime import datetime

import httpx
import pytest

from src.domain.models import KST, ProviderError
from src.providers.kiwoom import KiwoomClient
from src.providers.kiwoom_realtime import KiwoomRealtimeProvider
from src.providers.naver_news import NaverNewsProvider


def test_kiwoom_pagination_and_token_reuse(monkeypatch):
    monkeypatch.setattr("src.providers.kiwoom.time.sleep", lambda _: None)
    auth_calls = []

    def handler(request):
        if request.url.path == "/oauth2/token":
            auth_calls.append(1)
            return httpx.Response(200, json={"token": "fixture"})
        if request.headers["cont-yn"] == "N":
            return httpx.Response(
                200, json={"list": [{"code": "first"}]}, headers={"cont-yn": "Y", "next-key": "next"}
            )
        assert request.headers["next-key"] == "next"
        return httpx.Response(200, json={"list": [{"code": "second"}]}, headers={"cont-yn": "N"})

    client = KiwoomClient("key", "secret", "mock", httpx.Client(transport=httpx.MockTransport(handler)))
    rows = client.pages("ka10099", "/api/dostk/stkinfo", {}, "list")
    assert len(rows) == 2 and len(auth_calls) == 1


def test_naver_partial_page_failure_is_explicit(monkeypatch):
    monkeypatch.setattr("src.providers.http.time.sleep", lambda _: None)

    def handler(request):
        if request.url.params["start"] == "1":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "title": "기사",
                            "link": f"https://example.com/{i}",
                            "pubDate": "Tue, 29 Sep 2026 08:00:00 +0900",
                        }
                        for i in range(100)
                    ]
                },
            )
        return httpx.Response(429)

    provider = NaverNewsProvider("id", "secret", httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.search("query", datetime(2026, 9, 28, tzinfo=KST), datetime(2026, 9, 29, 9, tzinfo=KST))
    assert len(result.articles) == 100 and result.warnings


def test_websocket_login_ping_register_and_unsubscribe(monkeypatch):
    class Client:
        ws_url = "wss://fixture.example"

        def token(self):
            return "fixture-token"

    class Socket:
        sent = []
        messages = iter([{"trnm": "PING"}, {"trnm": "LOGIN", "return_code": 0}])
        events = iter(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "PING"},
                {
                    "trnm": "REAL",
                    "data": [
                        {
                            "type": "0B",
                            "item": "005930",
                            "values": {"20": "091500", "10": "70000", "12": "0.2", "15": "10", "13": "100"},
                        }
                    ],
                },
            ]
        )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send(self, body):
            self.sent.append(json.loads(body))

        async def recv(self):
            return json.dumps(next(self.messages))

        def __aiter__(self):
            return self

        async def __anext__(self):
            event = next(self.events, None)
            if event is None:
                raise StopAsyncIteration
            return json.dumps(event)

    socket = Socket()
    monkeypatch.setattr("src.providers.kiwoom_realtime.connect", lambda *args, **kwargs: socket)

    async def collect():
        return [tick async for tick in KiwoomRealtimeProvider(Client()).stream(["005930"])]

    ticks = asyncio.run(collect())
    assert ticks[0] is None and ticks[1].price == 70000
    assert [p["trnm"] for p in socket.sent] == ["LOGIN", "PING", "REG", "PING", "REMOVE"]


def test_http_error_does_not_leak_response_secrets():
    client = KiwoomClient(
        "PRIVATE_KEY",
        "PRIVATE_SECRET",
        "mock",
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(401, text="PRIVATE_SECRET"))
        ),
    )
    with pytest.raises(ProviderError) as exc:
        client.token()
    assert "PRIVATE" not in str(exc.value)
