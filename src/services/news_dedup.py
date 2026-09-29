import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from src.domain.models import Article


def normalize(title: str) -> str:
    return re.sub(r"[^\w가-힣]", "", re.sub(r"\[[^]]*\]", "", title)).lower()


def organize(articles: list[Article], start: datetime, end: datetime) -> dict:
    unique = {a.url: a for a in articles if start <= a.published_at <= end}
    ordered = sorted(unique.values(), key=lambda a: a.published_at, reverse=True)
    groups: list[list[Article]] = []
    for article in ordered:
        title = normalize(article.title)
        for group in groups:
            if SequenceMatcher(None, title, normalize(group[0].title)).ratio() >= 0.88:
                group.append(article)
                break
        else:
            groups.append([article])
    buckets = []
    hour = start.replace(minute=0, second=0, microsecond=0)
    while hour <= end:
        limit = hour + timedelta(hours=1)
        in_bucket = [a for a in ordered if hour <= a.published_at < limit]
        issues = sum(any(hour <= a.published_at < limit for a in group) for group in groups)
        buckets.append(
            {"time": hour, "count": len(in_bucket), "issues": issues, "partial": hour < start or limit > end}
        )
        hour = limit
    return {
        "articles": ordered,
        "groups": groups,
        "buckets": buckets,
        "total": len(ordered),
        "last_hour": sum(a.published_at >= end - timedelta(hours=1) for a in ordered),
        "last_six_hours": sum(a.published_at >= end - timedelta(hours=6) for a in ordered),
        "duplicates": len(articles) - len(unique),
    }
