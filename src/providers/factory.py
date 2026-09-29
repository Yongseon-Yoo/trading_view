from typing import NoReturn

from src.config import Settings
from src.domain.models import ProviderError
from src.providers.kiwoom import KiwoomClient, KiwoomMarketProvider
from src.providers.naver_news import NaverNewsProvider


class UnavailableProvider:
    def __init__(self, source: str, mode: str) -> None:
        self.label = f"{source} · {'인증정보 없음' if mode == 'missing' else '설정 불완전'}"
        self.message = (
            f"{source} 인증정보가 없습니다. .env의 키 두 개를 입력하고 앱을 재시작하세요."
            if mode == "missing"
            else f"{source} 인증정보가 일부만 입력되었습니다. .env의 키 쌍을 확인하세요."
        )

    def search(self, *args: object) -> NoReturn:
        raise ProviderError(self.message)

    quote = search
    ranks = search


def providers(settings: Settings):
    news = (
        NaverNewsProvider(settings.naver_id, settings.naver_secret)
        if settings.news_mode == "api"
        else UnavailableProvider("네이버 뉴스", settings.news_mode)
    )
    market = (
        KiwoomMarketProvider(KiwoomClient(settings.kiwoom_key, settings.kiwoom_secret, settings.kiwoom_env))
        if settings.market_mode == "api"
        else UnavailableProvider("키움 시장 데이터", settings.market_mode)
    )
    return news, market
