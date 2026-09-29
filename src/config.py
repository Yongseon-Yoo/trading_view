import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def credential_mode(first: str, second: str) -> str:
    if first and second:
        return "api"
    return "invalid" if first or second else "missing"


@dataclass(frozen=True)
class Settings:
    naver_id: str = field(default="", repr=False)
    naver_secret: str = field(default="", repr=False)
    kiwoom_key: str = field(default="", repr=False)
    kiwoom_secret: str = field(default="", repr=False)
    kiwoom_env: str = "mock"
    db_path: str = "data/dashboard.db"

    @property
    def news_mode(self) -> str:
        return credential_mode(self.naver_id, self.naver_secret)

    @property
    def market_mode(self) -> str:
        if self.kiwoom_env not in {"mock", "real"}:
            return "invalid"
        return credential_mode(self.kiwoom_key, self.kiwoom_secret)

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        return cls(
            *(
                os.getenv(k, "").strip()
                for k in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KIWOOM_APP_KEY", "KIWOOM_APP_SECRET")
            ),
            kiwoom_env=os.getenv("KIWOOM_ENV", "mock").strip(),
            db_path=os.getenv("DASHBOARD_DB_PATH") or os.getenv("YS_DB_PATH", "data/dashboard.db"),
        )
