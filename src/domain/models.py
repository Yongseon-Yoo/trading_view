from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)


def serializable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return serializable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


class ProviderError(Exception):
    """Only sanitized user-facing messages belong here."""


@dataclass(frozen=True)
class Article:
    title: str
    source: str
    published_at: datetime
    url: str


@dataclass
class SearchResult:
    articles: list[Article]
    warnings: list[str]


@dataclass(frozen=True)
class Quote:
    code: str
    name: str
    price: int
    change: int | None
    rate: float | None
    label: str
    price_date: str
    fetched_at: datetime


@dataclass(frozen=True)
class FlowRow:
    code: str
    name: str
    sector: str
    amount: int
    raw_value: str
    raw_unit: str
    price: int | None = None
    rate: float | None = None
    volume: int | None = None
    trading_value: int | None = None


@dataclass(frozen=True)
class TradeTick:
    code: str
    price: int
    rate: float
    volume: int
    cumulative_volume: int
    executed_at: datetime
    received_at: datetime
