from datetime import datetime
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd

from src.domain.models import KST


@lru_cache(maxsize=1)
def calendar():
    return xcals.get_calendar("XKRX")


def session_day(at: datetime) -> str:
    return str(
        calendar().date_to_session(pd.Timestamp(at.astimezone(KST).date()), direction="previous").date()
    )


def is_session(at: datetime) -> bool:
    return calendar().is_session(pd.Timestamp(at.astimezone(KST).date()))


def session_times(day: str) -> tuple[datetime, datetime]:
    cal = calendar()
    return (
        cal.session_open(day).to_pydatetime().astimezone(KST),
        cal.session_close(day).to_pydatetime().astimezone(KST),
    )


def last_close(at: datetime) -> datetime:
    if at.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    day = session_day(at)
    close = session_times(day)[1]
    if close >= at:
        day = str(calendar().previous_session(day).date())
        close = session_times(day)[1]
    return close


def market_state(at: datetime) -> str:
    if not is_session(at):
        return "휴장"
    opened, closed = session_times(session_day(at))
    return "장전" if at < opened else "장중" if at < closed else "장후"


def price_day(at: datetime) -> str:
    if market_state(at) in {"휴장", "장전"}:
        return last_close(at).date().isoformat()
    return at.astimezone(KST).date().isoformat()
