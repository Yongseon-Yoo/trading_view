import hashlib
from datetime import datetime, timedelta
from urllib.parse import quote

from src.domain.models import Article, FlowRow, Quote, SearchResult
from src.services.market_calendar import market_state, price_day

STOCKS = {
    "KOSPI": [
        ("005930", "삼성전자", "전기·전자"),
        ("000660", "SK하이닉스", "전기·전자"),
        ("012450", "한화에어로스페이스", "운송장비"),
        ("005380", "현대차", "운송장비"),
        ("035420", "NAVER", "서비스업"),
        ("035720", "카카오", "서비스업"),
        ("105560", "KB금융", "금융업"),
        ("055550", "신한지주", "금융업"),
        ("051910", "LG화학", "화학"),
        ("006400", "삼성SDI", "전기·전자"),
        ("028260", "삼성물산", "유통업"),
        ("003550", "LG", "금융업"),
        ("017670", "SK텔레콤", "통신업"),
        ("030200", "KT", "통신업"),
        ("086790", "하나금융지주", "금융업"),
        ("000270", "기아", "운송장비"),
        ("010950", "S-Oil", "화학"),
        ("096770", "SK이노베이션", "화학"),
        ("066570", "LG전자", "전기·전자"),
        ("032830", "삼성생명", "보험"),
    ],
    "KOSDAQ": [
        ("247540", "에코프로비엠", "전기·전자"),
        ("086520", "에코프로", "금융"),
        ("196170", "알테오젠", "연구·개발"),
        ("028300", "HLB", "제약"),
        ("058470", "리노공업", "전기·전자"),
        ("214150", "클래시스", "의료·정밀기기"),
        ("039030", "이오테크닉스", "기계·장비"),
        ("403870", "HPSP", "기계·장비"),
        ("140860", "파크시스템스", "의료·정밀기기"),
        ("067310", "하나마이크론", "전기·전자"),
        ("095340", "ISC", "전기·전자"),
        ("240810", "원익IPS", "기계·장비"),
        ("000250", "삼천당제약", "제약"),
        ("141080", "리가켐바이오", "연구·개발"),
        ("041510", "에스엠", "오락·문화"),
        ("035900", "JYP Ent.", "오락·문화"),
        ("263750", "펄어비스", "출판"),
        ("293490", "카카오게임즈", "출판"),
        ("078600", "대주전자재료", "전기·전자"),
        ("112040", "위메이드", "출판"),
    ],
}


def seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


class SampleNewsProvider:
    label = "샘플 뉴스 · 가상 기사"

    def search(self, query: str, start: datetime, end: datetime) -> SearchResult:
        span = (end - start).total_seconds()
        titles = [
            "설비 투자 계획 관련 업계 동향",
            "공급망 점검 및 생산 일정 발표",
            "산업 전시회 참가 소식",
            "연구개발 현황 공개",
            "기업 실적 발표 일정 안내",
        ]
        articles = []
        for i in range(12):
            fraction = (0.10, 0.30, 0.68, 0.84, 0.86, 0.87, 0.90, 0.92, 0.93, 0.95, 0.97, 0.99)[i]
            articles.append(
                Article(
                    f"[샘플] {query} {titles[i % 5]}",
                    "가상 뉴스",
                    start + timedelta(seconds=span * fraction),
                    f"https://example.com/news/{quote(query, safe='')}/{i}",
                )
            )
        return SearchResult(articles, [])


class SampleMarketProvider:
    label = "샘플 시세·수급 · 가상 금액"

    def quote(self, code: str, name: str, at: datetime) -> Quote:
        value = 50000 + seed(code) % 150000 // 100 * 100
        change = (seed(code) % 21 - 10) * 100
        label = "전일 종가" if market_state(at) in {"장전", "휴장"} else "조회 시점 현재가"
        return Quote(
            code, name, value, change, round(change / (value - change) * 100, 2), label, price_day(at), at
        )

    def ranks(self, market: str, investor: str, side: str) -> list[FlowRow]:
        stocks = STOCKS[market]
        selected = stocks[:10] if side != "sell" else stocks[10:]
        rows = []
        for i, (code, name, sector) in enumerate(selected):
            millions = (21000 - i * 1750) * (1 if investor == "foreign" else 2)
            if investor == "value":
                millions *= 9
            amount = millions * 1_000_000 * (-1 if side == "sell" else 1)
            price = 50000 + seed(code) % 150000 // 100 * 100
            rows.append(
                FlowRow(
                    code,
                    name,
                    sector,
                    amount,
                    str(amount // 1_000_000),
                    "백만원",
                    price,
                    round((seed(code) % 800 - 300) / 100, 2),
                    500000 + i * 24000,
                    abs(amount) * 9 if investor != "value" else amount,
                )
            )
        return rows
