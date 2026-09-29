from datetime import datetime, timedelta

import httpx

from src.domain.models import KST, Article, ProviderError
from src.providers.naver_news import NaverNewsProvider
from src.providers.sample import SampleNewsProvider
from src.services.market_calendar import last_close, market_state
from src.services.morning_brief import build_morning
from src.services.news_dedup import organize


def test_monday_and_holiday_window():
    assert last_close(datetime(2026, 9, 21, 8, tzinfo=KST)) == datetime(2026, 9, 18, 15, 30, tzinfo=KST)
    assert last_close(datetime(2026, 9, 28, 8, tzinfo=KST)) == datetime(2026, 9, 23, 15, 30, tzinfo=KST)
    assert market_state(datetime(2026, 9, 26, 12, tzinfo=KST)) == "휴장"


def test_dedup_buckets_and_zero_intervals():
    start = datetime(2026, 9, 28, 15, 30, tzinfo=KST)
    end = start + timedelta(hours=4)
    a = Article("[속보] 반도체 생산 계획 발표", "source", start, "https://example.com/a")
    b = Article("반도체 생산 계획 발표", "source", end - timedelta(minutes=1), "https://example.com/b")
    result = organize([a, a, b], start, end)
    assert result["total"] == 2 and len(result["groups"]) == 1
    assert sum(b["count"] for b in result["buckets"]) == 2
    assert any(b["count"] == 0 for b in result["buckets"])
    assert result["last_hour"] == 1


def test_naver_parses_metadata_and_skips_bad_date():
    def handler(request):
        assert request.url.params["sort"] == "date"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "title": "<b>기사</b> &amp; 제목",
                        "originallink": "https://news.example.com/1",
                        "pubDate": "Tue, 29 Sep 2026 08:00:00 +0900",
                    },
                    {"pubDate": "wrong"},
                ]
            },
        )

    provider = NaverNewsProvider("id", "secret", httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.search(
        "반도체", datetime(2026, 9, 28, tzinfo=KST), datetime(2026, 9, 29, 9, tzinfo=KST)
    )
    assert result.articles[0].title == "기사 & 제목"
    assert result.articles[0].source == "news.example.com"
    assert len(result.warnings) == 1


def test_quote_failure_preserves_news():
    class BrokenMarket:
        label = "오류 공급자"

        def quote(self, *args):
            raise ProviderError("인증 실패")

    result = build_morning(
        [{"code": "005930", "name": "삼성전자"}],
        [],
        SampleNewsProvider(),
        BrokenMarket(),
        datetime(2026, 9, 29, 8, tzinfo=KST),
    )
    assert result["sections"][0]["total"] == 12
    assert result["errors"] and not result["quotes"]
