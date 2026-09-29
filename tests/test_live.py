import asyncio
import time
from datetime import timedelta

from src.domain.models import TradeTick, now_kst
from src.providers.kiwoom_realtime import parse_ticks, registration
from src.providers.sample_realtime import SampleRealtimeProvider
from src.services.live import LiveSession


def test_subscription_and_signed_fields():
    assert registration(["005930", "005930", "000660"])["data"][0]["item"] == ["005930", "000660"]
    ticks = parse_ticks(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0B",
                    "item": "005930",
                    "values": {"20": "091500", "10": "-70000", "12": "-1.25", "15": "-30", "13": "456"},
                }
            ],
        },
        now_kst(),
    )
    assert ticks[0].price == 70000 and ticks[0].volume == -30


def test_bounded_buffer_and_legitimate_same_second_ticks():
    live = LiveSession(None, ["005930"])
    at = now_kst()
    for i in range(400):
        live.ingest(TradeTick("005930", 70000, 0, 10, i * 10, at, at))
    assert len(live.snapshot()[2]["005930"]) == 300
    live.ingest(TradeTick("005930", 70000, 0, 10, 3990, at, at))
    assert len(live.snapshot()[2]["005930"]) == 300
    live._prune(at + timedelta(minutes=6))
    assert not live.snapshot()[2]["005930"]


def test_stream_start_stop_cleanup():
    live = LiveSession(SampleRealtimeProvider(0.01), ["005930", "000660"])
    live.start()
    deadline = time.monotonic() + 2
    while live.snapshot()[0] != "연결됨" and time.monotonic() < deadline:
        time.sleep(0.01)
    assert all(live.snapshot()[2].values())
    live.stop()
    assert live.snapshot()[0] == "종료"
    assert not any(live.snapshot()[2].values())
    assert not live._thread.is_alive()


def test_heartbeat_ends_idle_session():
    live = LiveSession(SampleRealtimeProvider(0.01), ["005930"])
    live._heartbeat = time.monotonic() - 31
    live.start()
    live._thread.join(timeout=2)
    assert live.snapshot()[0] == "종료"


def test_retry_is_bounded():
    class Broken:
        attempts = 0

        async def stream(self, codes):
            self.attempts += 1
            raise RuntimeError("secret-containing error must not be exposed")
            yield

    provider = Broken()
    live = LiveSession(provider, ["005930"])
    asyncio.run(live._supervise())
    assert provider.attempts == 3
    assert "secret" not in live.snapshot()[1]
