import asyncio
import math

from src.domain.models import TradeTick, now_kst
from src.providers.sample import seed


class SampleRealtimeProvider:
    def __init__(self, interval: float = 1.0):
        self.interval = interval

    async def stream(self, codes: list[str]):
        count = 0
        cumulative = {code: 100000 for code in codes}
        while True:
            for index, code in enumerate(codes):
                at = now_kst()
                base = 50000 + seed(code) % 150000 // 100 * 100
                price = base + round(math.sin(count / 7 + index) * 9) * 100
                volume = 20 + (count * 17 + index * 53) % 500
                cumulative[code] += volume
                yield TradeTick(
                    code,
                    price,
                    round((price / base - 1) * 100, 2),
                    volume if count % 3 else -volume,
                    cumulative[code],
                    at,
                    at,
                )
            count += 1
            await asyncio.sleep(self.interval)
