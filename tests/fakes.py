import asyncio
from datetime import datetime

from src.domain.models import Article, FlowRow, Quote, SearchResult, TradeTick, now_kst


class FakeNewsProvider:
    label = "테스트 뉴스 공급자"

    def __init__(self, articles: list[Article] | None = None) -> None:
        self.articles = articles or []

    def search(self, query: str, start: datetime, end: datetime) -> SearchResult:
        return SearchResult(self.articles, [])


class FakeMarketProvider:
    label = "테스트 시장 공급자"

    def quote(self, code: str, name: str, at: datetime) -> Quote:
        return Quote(code, name, 70000, 1000, 1.45, "전일 종가", at.date().isoformat(), at)

    def ranks(self, market: str, investor: str, side: str) -> list[FlowRow]:
        sign = -1 if side == "sell" else 1
        base = 0 if market == "KOSPI" else 100
        return [
            FlowRow(
                f"{base + i:06d}",
                f"테스트 종목 {i}",
                "테스트 업종",
                sign * (10 - i) * 1_000_000,
                str(sign * (10 - i)),
                "백만원",
            )
            for i in range(10)
        ]


class FakeRealtimeProvider:
    def __init__(self, interval: float = 0.01) -> None:
        self.interval = interval

    async def stream(self, codes: list[str]):
        yield None
        count = 0
        while True:
            for code in codes:
                at = now_kst()
                yield TradeTick(code, 70000 + count, 0.0, 10, 1000 + count * 10, at, at)
            count += 1
            await asyncio.sleep(self.interval)
