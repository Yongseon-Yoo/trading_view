from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from src.domain.models import FlowRow, Quote, SearchResult, TradeTick


class NewsProvider(Protocol):
    label: str

    def search(self, query: str, start: datetime, end: datetime) -> SearchResult: ...


class MarketProvider(Protocol):
    label: str

    def quote(self, code: str, name: str, at: datetime) -> Quote: ...
    def ranks(self, market: str, investor: str, side: str) -> list[FlowRow]: ...


class RealtimeMarketProvider(Protocol):
    def stream(self, codes: list[str]) -> AsyncIterator[TradeTick | None]: ...
