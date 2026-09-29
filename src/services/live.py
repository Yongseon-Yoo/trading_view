import asyncio
import threading
import time
from collections import deque
from contextlib import suppress
from datetime import timedelta

from src.domain.models import ProviderError, TradeTick, now_kst


class LiveSession:
    """One session-owned worker; bounded buffers, no DB, no Streamlit imports."""

    def __init__(self, provider, codes: list[str]):
        self.provider, self.codes = provider, codes
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._heartbeat = time.monotonic()
        self._buffers = {code: deque(maxlen=300) for code in codes}
        self._status = "대기"
        self._error = ""
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._status = "연결 중"
        self._thread = threading.Thread(target=self._run, daemon=True, name="ys-live")
        self._thread.start()

    def touch(self):
        self._heartbeat = time.monotonic()

    def ingest(self, tick: TradeTick):
        if self._stop.is_set() or tick.code not in self._buffers:
            return
        with self._lock:
            if self._stop.is_set():
                return
            buffer = self._buffers[tick.code]
            signature = (tick.executed_at, tick.price, tick.volume, tick.cumulative_volume)
            if any((t.executed_at, t.price, t.volume, t.cumulative_volume) == signature for t in buffer):
                return
            if buffer and tick.cumulative_volume < buffer[-1].cumulative_volume:
                return  # Do not regress cards on a delayed/out-of-order event.
            buffer.append(tick)
            self._prune(tick.received_at)
            self._status = "연결됨"
            self._error = ""

    def _prune(self, at):
        for buffer in self._buffers.values():
            while buffer and buffer[0].received_at < at - timedelta(minutes=5):
                buffer.popleft()

    def snapshot(self):
        with self._lock:
            self._prune(now_kst())
            return self._status, self._error, {code: list(rows) for code, rows in self._buffers.items()}

    def stop(self):
        self._stop.set()
        with self._lock:
            self._status = "종료"
            for buffer in self._buffers.values():
                buffer.clear()
        if self._thread:
            self._thread.join(timeout=0.8)

    async def _consume(self):
        async for tick in self.provider.stream(self.codes):
            if self._stop.is_set():
                return
            if tick is None:
                with self._lock:
                    if not self._stop.is_set():
                        self._status = "연결됨"
            else:
                self.ingest(tick)
        if not self._stop.is_set():
            raise ProviderError("실시간 연결이 종료되었습니다.")

    async def _supervise(self):
        for attempt in range(3):
            task = asyncio.create_task(self._consume())
            try:
                while not task.done():
                    if self._stop.is_set() or time.monotonic() - self._heartbeat > 30:
                        self._stop.set()
                        return
                    await asyncio.sleep(0.1)
                await task
            except Exception as exc:
                with self._lock:
                    self._error = (
                        str(exc)
                        if isinstance(exc, ProviderError)
                        else "실시간 연결 오류. 환경·네트워크를 확인하세요."
                    )
                    self._status = "오류" if attempt == 2 else "재연결 중"
                if attempt < 2:
                    for _ in range(10 * (attempt + 1)):
                        if self._stop.is_set():
                            return
                        await asyncio.sleep(0.1)
            finally:
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task

    def _run(self):
        try:
            asyncio.run(self._supervise())
        finally:
            if self._stop.is_set():
                with self._lock:
                    self._status = "종료"
                    for buffer in self._buffers.values():
                        buffer.clear()
