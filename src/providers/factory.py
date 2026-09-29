from src.config import Settings
from src.domain.models import ProviderError
from src.providers.kiwoom import KiwoomClient, KiwoomMarketProvider
from src.providers.naver_news import NaverNewsProvider
from src.providers.sample import SampleMarketProvider, SampleNewsProvider


class InvalidProvider:
    label = "설정 오류"

    def search(self, *args):
        raise ProviderError("인증정보가 일부만 입력되었습니다. .env의 키 쌍을 확인하세요.")

    quote = search
    ranks = search


def providers(settings: Settings):
    news = (
        NaverNewsProvider(settings.naver_id, settings.naver_secret)
        if settings.news_mode == "api"
        else SampleNewsProvider()
        if settings.news_mode == "sample"
        else InvalidProvider()
    )
    market = (
        KiwoomMarketProvider(KiwoomClient(settings.kiwoom_key, settings.kiwoom_secret, settings.kiwoom_env))
        if settings.market_mode == "api"
        else SampleMarketProvider()
        if settings.market_mode == "sample"
        else InvalidProvider()
    )
    return news, market
