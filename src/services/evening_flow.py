from datetime import datetime

from src.domain.models import FlowRow, ProviderError, serializable
from src.providers.protocols import MarketProvider
from src.services.market_calendar import market_state, session_day

RANKINGS = [
    ("foreign", "buy", "외국인 순매수"),
    ("foreign", "sell", "외국인 순매도"),
    ("institution", "buy", "기관 순매수"),
    ("institution", "sell", "기관 순매도"),
    ("value", "buy", "거래대금"),
]


def group_sectors(rows: list[FlowRow], side: str) -> list[dict]:
    grouped = {}
    for row in {row.code: row for row in rows}.values():
        entry = grouped.setdefault(
            row.sector, {"sector": row.sector, "side": side, "amount": 0, "names": [], "count": 0}
        )
        entry["amount"] += row.amount
        entry["names"].append(row.name)
        entry["count"] += 1
    return list(grouped.values())


def build_evening(provider: MarketProvider, at: datetime) -> dict:
    state = market_state(at)
    if "키움" in provider.label and state in {"휴장", "장전"}:
        raise ProviderError(
            "최신 순위 API는 기준일을 지정할 수 없습니다. 거래일 장 시작 이후 생성하거나 저장 리포트를 열어주세요."
        )
    tables, errors, sectors = {}, [], {}
    for market in ("KOSPI", "KOSDAQ"):
        tables[market], sectors[market] = {}, {}
        for investor, side, title in RANKINGS:
            key = f"{investor}_{side}"
            try:
                rows = provider.ranks(market, investor, side)
                rows = sorted(rows, key=lambda r: abs(r.amount), reverse=True)[:10]
                tables[market][key] = rows
                if investor != "value":
                    sectors[market].setdefault(investor, []).extend(group_sectors(rows, side))
                if any(r.sector == "미분류" for r in rows):
                    errors.append(f"{market} {title}: 업종 매핑이 없는 종목을 미분류로 표시했습니다.")
            except ProviderError as exc:
                tables[market][key] = []
                errors.append(f"{market} {title}: {exc}")
    return serializable(
        {
            "kind": "evening",
            "report_date": session_day(at),
            "generated_at": at,
            "market_source": provider.label,
            "market_state": state,
            "notice": "최신 조회 잠정 자료 · KRX 기준 · 확정 수급 아님",
            "tables": tables,
            "sectors": sectors,
            "errors": errors,
        }
    )
