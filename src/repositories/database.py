import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from src.domain.models import serializable


class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS stocks(code TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS themes(name TEXT PRIMARY KEY, keywords TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS links(
                    code TEXT REFERENCES stocks(code) ON DELETE CASCADE,
                    theme TEXT REFERENCES themes(name) ON DELETE CASCADE, PRIMARY KEY(code,theme));
                CREATE TABLE IF NOT EXISTS reports(
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, report_date TEXT NOT NULL,
                    generated_at TEXT NOT NULL, content TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS report_date_idx ON reports(report_date,kind);
            """)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def stocks(self) -> list[dict]:
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM stocks ORDER BY name")]

    def save_stock(self, code: str, name: str):
        code, name = code.strip(), name.strip()
        if not re.fullmatch(r"[0-9]{6}", code) or not 1 <= len(name) <= 60:
            raise ValueError("종목코드는 숫자 6자리, 종목명은 1~60자로 입력하세요.")
        with self.connect() as con:
            con.execute(
                "INSERT INTO stocks VALUES(?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name",
                (code, name),
            )

    def delete_stock(self, code: str):
        with self.connect() as con:
            con.execute("DELETE FROM stocks WHERE code=?", (code,))

    def themes(self) -> list[dict]:
        with self.connect() as con:
            return [
                {
                    "name": r["name"],
                    "keywords": json.loads(r["keywords"]),
                    "codes": [
                        v[0] for v in con.execute("SELECT code FROM links WHERE theme=?", (r["name"],))
                    ],
                }
                for r in con.execute("SELECT * FROM themes ORDER BY name")
            ]

    def save_theme(self, name: str, keywords: list[str], codes: list[str]):
        name = name.strip()
        keywords = list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
        if not 1 <= len(name) <= 60 or not 1 <= len(keywords) <= 10 or any(len(k) > 100 for k in keywords):
            raise ValueError("테마명 1~60자, 검색어 1~10개(각 100자 이하)를 입력하세요.")
        with self.connect() as con:
            con.execute(
                "INSERT INTO themes VALUES(?,?) ON CONFLICT(name) DO UPDATE SET keywords=excluded.keywords",
                (name, json.dumps(keywords, ensure_ascii=False)),
            )
            con.execute("DELETE FROM links WHERE theme=?", (name,))
            con.executemany("INSERT INTO links VALUES(?,?)", [(c, name) for c in set(codes)])

    def delete_theme(self, name: str):
        with self.connect() as con:
            con.execute("DELETE FROM themes WHERE name=?", (name,))

    def save_report(self, report: dict) -> str:
        report_id = uuid4().hex
        data = serializable(report)
        with self.connect() as con:
            con.execute(
                "INSERT INTO reports VALUES(?,?,?,?,?)",
                (
                    report_id,
                    data["kind"],
                    data["report_date"],
                    data["generated_at"],
                    json.dumps(data, ensure_ascii=False, allow_nan=False),
                ),
            )
        return report_id

    def reports(self) -> list[dict]:
        with self.connect() as con:
            return [
                {key: r[key] for key in ("id", "kind", "report_date", "generated_at")}
                for r in con.execute(
                    "SELECT id,kind,report_date,generated_at,content FROM reports ORDER BY generated_at DESC"
                )
                if not any(
                    "샘플" in str(json.loads(r["content"]).get(source, ""))
                    for source in ("news_source", "market_source")
                )
            ]

    def report(self, report_id: str) -> dict:
        with self.connect() as con:
            row = con.execute("SELECT content FROM reports WHERE id=?", (report_id,)).fetchone()
            if row is None:
                raise KeyError("리포트가 없습니다.")
            return json.loads(row[0])
