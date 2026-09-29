from datetime import datetime

from src.domain.models import ProviderError, serializable
from src.providers.protocols import MarketProvider, NewsProvider
from src.services.market_calendar import last_close
from src.services.news_dedup import organize


def build_morning(
    stocks: list[dict], themes: list[dict], news: NewsProvider, market: MarketProvider, at: datetime
) -> dict:
    start = last_close(at)
    sections, quotes, errors = [], [], []
    searches = [("종목", s["name"], [s["name"]]) for s in stocks]
    searches += [("테마", t["name"], t["keywords"]) for t in themes]
    cache = {}
    for kind, name, queries in searches:
        articles, warnings = [], []
        succeeded = 0
        for query in queries:
            try:
                if query not in cache:
                    cache[query] = news.search(query, start, at)
                result = cache[query]
                articles.extend(result.articles)
                warnings.extend(result.warnings)
                succeeded += 1
            except ProviderError as exc:
                warnings.append(f"{query}: {exc}")
        sections.append(
            {
                "kind": kind,
                "name": name,
                **organize(articles, start, at),
                "warnings": warnings,
                "complete": succeeded == len(queries) and not warnings,
                "failed": succeeded == 0,
            }
        )
    for stock in stocks:
        try:
            quotes.append(market.quote(stock["code"], stock["name"], at))
        except ProviderError as exc:
            errors.append(f"{stock['name']} 가격 조회: {exc}")
    return serializable(
        {
            "kind": "morning",
            "report_date": at.date().isoformat(),
            "generated_at": at,
            "window_start": start,
            "window_end": at,
            "sections": sections,
            "quotes": quotes,
            "errors": errors,
            "news_source": news.label,
            "market_source": market.label,
        }
    )
