import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from threading import RLock

import httpx

from src.domain.models import FlowRow, ProviderError, Quote
from src.providers.http import request_json
from src.services.market_calendar import market_state, price_day

MARKETS = {"KOSPI": "001", "KOSDAQ": "101"}


def number(value, multiplier: int = 1) -> int:
    try:
        decimal = Decimal(str(value).strip().replace(",", "")) * multiplier
        if not decimal.is_finite() or decimal != decimal.to_integral_value():
            raise ValueError
        return int(decimal)
    except (InvalidOperation, ValueError, TypeError):
        raise ProviderError("숫자 또는 금액 단위 변환에 실패했습니다.") from None


class KiwoomClient:
    def __init__(self, key: str, secret: str, env: str, client: httpx.Client | None = None):
        if env not in {"mock", "real"}:
            raise ProviderError("KIWOOM_ENV는 mock 또는 real이어야 합니다.")
        self.key, self.secret, self.env = key, secret, env
        host = "mockapi" if env == "mock" else "api"
        self.base = f"https://{host}.kiwoom.com"
        self.ws_url = f"wss://{host}.kiwoom.com:10000/api/dostk/websocket"
        self.client = client or httpx.Client(timeout=12)
        self._token, self._expiry, self._last_request = "", 0.0, 0.0
        self._lock = RLock()

    def token(self) -> str:
        with self._lock:
            if time.monotonic() < self._expiry:
                return self._token
            data, _ = request_json(
                self.client,
                "POST",
                self.base + "/oauth2/token",
                json={"grant_type": "client_credentials", "appkey": self.key, "secretkey": self.secret},
            )
            if str(data.get("return_code", 0)) != "0" or not data.get("token"):
                raise ProviderError("키움 인증 실패: 선택한 운영/모의 환경과 발급 키를 확인하세요.")
            self._token = data["token"]
            # Refresh well before the documented expiration; never persist tokens.
            self._expiry = time.monotonic() + 1800
            return self._token

    def pages(self, api_id: str, path: str, body: dict, field: str, max_pages: int = 100) -> list[dict]:
        result, next_key, seen = [], "", set()
        for _ in range(max_pages):
            data, headers = self.call(api_id, path, body, next_key)
            rows = data.get(field)
            if not isinstance(rows, list):
                raise ProviderError(f"{api_id}: 목록 응답 필드가 누락되었습니다.")
            result.extend(rows)
            if headers.get("cont-yn") != "Y":
                return result
            next_key = headers.get("next-key", "")
            if not next_key or next_key in seen:
                raise ProviderError("연속조회 키가 유효하지 않습니다. 불완전한 순위는 표시하지 않습니다.")
            seen.add(next_key)
        raise ProviderError("연속조회 상한에 도달했습니다. 불완전한 순위는 표시하지 않습니다.")

    def call(self, api_id: str, path: str, body: dict, next_key: str = ""):
        allowed = {"ka10001", "ka10032", "ka10065", "ka10099"}
        if api_id not in allowed:
            raise ProviderError("허용되지 않은 조회 API입니다.")
        with self._lock:
            token = self.token()
            delay = 0.55 - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            data, headers = request_json(
                self.client,
                "POST",
                self.base + path,
                json=body,
                headers={
                    "authorization": f"Bearer {token}",
                    "api-id": api_id,
                    "cont-yn": "Y" if next_key else "N",
                    "next-key": next_key,
                },
            )
            self._last_request = time.monotonic()
            if str(data.get("return_code", 0)) != "0":
                raise ProviderError(f"키움 {api_id} 조회 실패: 권한·환경·종목과 호출 제한을 확인하세요.")
            return data, headers


class KiwoomMarketProvider:
    def __init__(self, client: KiwoomClient):
        self.client = client
        self.label = "키움 모의 API" if client.env == "mock" else "키움 운영 API"
        self._masters: dict[str, tuple[float, dict]] = {}

    def master(self, market: str) -> dict:
        cached = self._masters.get(market)
        if cached and time.monotonic() - cached[0] < 3600:
            return cached[1]
        rows = self.client.pages(
            "ka10099", "/api/dostk/stkinfo", {"mrkt_tp": "0" if market == "KOSPI" else "10"}, "list"
        )
        data = {row["code"]: row for row in rows}
        self._masters[market] = (time.monotonic(), data)
        return data

    def quote(self, code: str, name: str, at: datetime) -> Quote:
        if market_state(at) in {"휴장", "장전"}:
            for market in MARKETS:
                row = self.master(market).get(code)
                if row:
                    price = abs(number(row["lastPrice"]))
                    if not price:
                        raise ProviderError("유효한 전일 종가가 없습니다.")
                    return Quote(code, name, price, None, None, "전일 종가", price_day(at), at)
            raise ProviderError("코스피·코스닥 종목 마스터에서 종목을 찾지 못했습니다.")
        data, _ = self.client.call("ka10001", "/api/dostk/stkinfo", {"stk_cd": code})
        try:
            price = abs(number(data["cur_prc"]))
            if price <= 0:
                raise ProviderError("유효한 현재가가 없습니다.")
            return Quote(
                code,
                name,
                price,
                number(data["pred_pre"]),
                float(data["flu_rt"]),
                "조회 시점 현재가",
                price_day(at),
                at,
            )
        except (KeyError, ValueError):
            raise ProviderError("현재가 응답 필드가 올바르지 않습니다.") from None

    def ranks(self, market: str, investor: str, side: str) -> list[FlowRow]:
        if investor == "value":
            data = self.client.pages(
                "ka10032",
                "/api/dostk/rkinfo",
                {"mrkt_tp": MARKETS[market], "mang_stk_incls": "1", "stex_tp": "1"},
                "trde_prica_upper",
            )
            value_field = "trde_prica"
        else:
            data = self.client.pages(
                "ka10065",
                "/api/dostk/rkinfo",
                {
                    "trde_tp": "1" if side == "buy" else "2",
                    "mrkt_tp": MARKETS[market],
                    "orgn_tp": "9000" if investor == "foreign" else "9999",
                    "amt_qty_tp": "1",
                },
                "opmr_invsr_trde_upper",
            )
            value_field = "netslmt"
        # A master outage must not turn valid rankings into fake sector data.
        try:
            master = self.master(market)
        except ProviderError:
            master = {}
        rows = {}
        try:
            for row in data:
                code = row["stk_cd"].removeprefix("A")
                raw = row[value_field]
                amount = abs(number(raw, 1_000_000)) * (-1 if side == "sell" else 1)
                if amount == 0:
                    continue
                rows[code] = FlowRow(
                    code,
                    row["stk_nm"],
                    master.get(code, {}).get("upName") or "미분류",
                    amount,
                    str(raw),
                    "백만원",
                    abs(number(row["cur_prc"])) if row.get("cur_prc") else None,
                    float(row["flu_rt"]) if row.get("flu_rt") else None,
                    number(row["now_trde_qty"]) if row.get("now_trde_qty") else None,
                    amount if investor == "value" else None,
                )
        except (KeyError, ValueError, TypeError):
            raise ProviderError("순위 응답 필드가 올바르지 않습니다.") from None
        return sorted(rows.values(), key=lambda r: abs(r.amount), reverse=True)[:10]
