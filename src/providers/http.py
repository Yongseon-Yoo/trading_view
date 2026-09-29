import time

import httpx

from src.domain.models import ProviderError


def request_json(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[dict, httpx.Headers]:
    for attempt in range(3):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(0.4 * 2**attempt)
                    continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ProviderError("공급자 응답 형식이 올바르지 않습니다.")
            return payload, response.headers
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"API HTTP {exc.response.status_code}: 인증·권한 또는 호출 제한을 확인하세요."
            ) from None
        except (httpx.RequestError, ValueError):
            if attempt == 2:
                raise ProviderError("API 연결 또는 응답 해석에 실패했습니다. 잠시 후 재시도하세요.") from None
            time.sleep(0.4 * 2**attempt)
    raise ProviderError("API 재시도 횟수를 초과했습니다.")
