import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from src.domain.models import KST, Article, ProviderError, SearchResult
from src.providers.http import request_json


def clean_title(title: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", title)).split())


def safe_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme in {"https", "http"} and bool(parts.hostname) and not parts.username


class NaverNewsProvider:
    label = "네이버 뉴스 검색 결과 기준"

    def __init__(self, client_id: str, secret: str, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=12)
        self.headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": secret}

    def search(self, query: str, start: datetime, end: datetime) -> SearchResult:
        articles, warnings = [], []
        for offset in range(1, 1000, 100):
            try:
                data, _ = request_json(
                    self.client,
                    "GET",
                    "https://openapi.naver.com/v1/search/news.json",
                    headers=self.headers,
                    params={"query": query, "display": 100, "start": offset, "sort": "date"},
                )
            except ProviderError:
                if not articles:
                    raise
                warnings.append("후속 페이지 수집 실패: 일부 검색 결과만 표시합니다.")
                break
            items = data.get("items")
            if not isinstance(items, list):
                raise ProviderError("뉴스 목록 필드가 누락되었습니다.")
            reached_start = False
            for item in items:
                try:
                    stamp = parsedate_to_datetime(item["pubDate"])
                    if stamp.tzinfo is None:
                        raise ValueError
                    stamp = stamp.astimezone(KST)
                    if stamp < start:
                        reached_start = True
                        continue
                    url = item.get("originallink") or item["link"]
                    if not safe_url(url):
                        raise ValueError
                    if start <= stamp <= end:
                        articles.append(
                            Article(
                                clean_title(item["title"]), urlsplit(url).hostname or "출처 미상", stamp, url
                            )
                        )
                except (KeyError, ValueError, TypeError, OverflowError):
                    warnings.append("시각·링크 형식이 잘못된 기사 1건을 제외했습니다.")
            if reached_start or len(items) < 100:
                break
        else:
            warnings.append("검색 상한 1,000건에 도달했습니다. 기사 수는 수집된 범위 기준입니다.")
        return SearchResult(articles, warnings)
