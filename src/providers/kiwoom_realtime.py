import asyncio
import json
from datetime import datetime

from websockets.asyncio.client import connect

from src.domain.models import ProviderError, TradeTick, now_kst
from src.providers.kiwoom import KiwoomClient, number


def registration(codes: list[str]) -> dict:
    return {
        "trnm": "REG",
        "grp_no": "1",
        "refresh": "0",
        "data": [{"item": list(dict.fromkeys(codes)), "type": ["0B"]}],
    }


def parse_ticks(message: dict, at: datetime) -> list[TradeTick]:
    result = []
    if message.get("trnm") != "REAL":
        return result
    for event in message.get("data", []):
        if event.get("type") != "0B":
            continue
        try:
            values = event["values"]
            clock = datetime.strptime(values["20"], "%H%M%S").time()
            stamp = datetime.combine(at.date(), clock, at.tzinfo)
            result.append(
                TradeTick(
                    event["item"].removeprefix("A"),
                    abs(number(values["10"])),
                    float(values["12"]),
                    number(values["15"]),
                    number(values["13"]),
                    stamp,
                    at,
                )
            )
        except (KeyError, ValueError, TypeError):
            raise ProviderError("실시간 체결 데이터 형식이 올바르지 않습니다.") from None
    return result


class KiwoomRealtimeProvider:
    def __init__(self, client: KiwoomClient):
        self.client = client

    async def stream(self, codes: list[str]):
        token = await asyncio.to_thread(self.client.token)
        async with connect(self.client.ws_url, open_timeout=10, close_timeout=1, max_queue=32) as ws:
            await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
            async with asyncio.timeout(12):
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("trnm") == "PING":
                        await ws.send(json.dumps(message))
                    elif message.get("trnm") == "LOGIN":
                        if str(message.get("return_code")) != "0":
                            raise ProviderError("웹소켓 인증 실패: 모의/운영 환경과 키를 확인하세요.")
                        break
            await ws.send(json.dumps(registration(codes)))
            try:
                async for raw in ws:
                    message = json.loads(raw)
                    if message.get("trnm") == "PING":
                        await ws.send(json.dumps(message))
                        continue
                    if "return_code" in message and str(message["return_code"]) != "0":
                        raise ProviderError("실시간 구독 요청이 거부되었습니다.")
                    if message.get("trnm") == "REG":
                        yield None  # Connection acknowledgement, including no-trade sessions.
                    for tick in parse_ticks(message, now_kst()):
                        yield tick
            finally:
                try:
                    await ws.send(
                        json.dumps(
                            {"trnm": "REMOVE", "grp_no": "1", "data": [{"item": codes, "type": ["0B"]}]}
                        )
                    )
                except Exception:
                    # A disconnected socket cannot acknowledge unsubscribe; context closes it.
                    pass
