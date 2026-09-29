# 주식대시보드YS Architecture

> 상태: IMPLEMENTED - 샘플·자동 테스트 검증, 실제 키 통합 검증 대기

승인된 기술 구성: Python + Streamlit + SQLite + Plotly

## 1. 목표

- 외부 API 변경이 UI와 핵심 로직에 직접 전파되지 않게 한다.
- 실제 API 키 없이도 샘플 데이터로 전체 흐름을 검증한다.
- 뉴스와 수급 컴포넌트를 독립적으로 개발·테스트한다.
- 하루짜리 MVP에 맞게 단일 프로세스와 SQLite를 유지한다.

## 2. 아키텍처

```text
Streamlit UI
    ↓
Application Services
    ↓
Domain Models / Rules
    ↓
Provider Interfaces + Repositories
    ↓
Market Data API | Naver Search | SQLite | Sample Providers
```

Streamlit은 로컬 웹 UI, SQLite는 영구 로컬 저장소, Plotly는 모든 대화형 차트에 사용한다.

### 레이어 규칙

1. UI는 외부 API 응답을 직접 파싱하지 않는다.
2. 공급자 코드는 도메인 모델만 반환한다.
3. 서비스는 화면 프레임워크를 import하지 않는다.
4. 저장소는 SQLite 구현 세부사항을 서비스에 노출하지 않는다.
5. 외부 응답 필드명은 공급자 계층 밖으로 노출하지 않는다.

## 3. 디렉터리 구조

```text
app.py
src/
├── config.py
├── domain/
│   └── models.py
├── providers/
│   ├── protocols.py
│   ├── factory.py
│   ├── http.py
│   ├── kiwoom.py
│   ├── kiwoom_realtime.py
│   ├── naver_news.py
│   ├── sample.py
│   └── sample_realtime.py
├── services/
│   ├── morning_brief.py
│   ├── evening_flow.py
│   ├── news_dedup.py
│   ├── live.py
│   └── market_calendar.py
├── repositories/
│   └── database.py
└── ui/
    ├── morning.py
    ├── live.py
    ├── evening.py
    ├── history.py
    ├── common.py
    └── settings.py
tests/
└── test_*.py
```

## 4. 주요 인터페이스

```python
class NewsProvider(Protocol):
    def search(self, query: str, start: datetime, end: datetime) -> SearchResult: ...


class MarketProvider(Protocol):
    def quote(self, code: str, name: str, at: datetime) -> Quote: ...
    def ranks(self, market: str, investor: str, side: str) -> list[FlowRow]: ...


class RealtimeMarketProvider(Protocol):
    def stream(self, codes: list[str]) -> AsyncIterator[TradeTick | None]: ...


class Database:
    def save_report(self, report: dict) -> str: ...
    def reports(self) -> list[dict]: ...
    def report(self, report_id: str) -> dict: ...
```

실시간 스트림의 `None`은 구독 승인 신호다. 체결 데이터로 저장하지 않는다.

## 5. 데이터 흐름

### 아침

```text
Watchlist/Theme DB
 → build_morning
 → NewsProvider
 → normalize/deduplicate/filter
 → report dict
 → Database.save_report
 → Streamlit
```

### 저녁

```text
User request
 → build_evening
 → MarketProvider
 → normalize/enrich/group
 → report dict
 → Database.save_report
 → Streamlit
```

### 장중 실시간

```text
Watchlist DB
 → Live Watchlist UI
 → RealtimeMarketProvider
 → Kiwoom 0B WebSocket 또는 SampleRealtimeProvider
 → normalize / rolling 5-minute buffer
 → Streamlit cards and line chart
```

## 6. 상태 관리

- 영구 상태: SQLite
- 비밀정보: 환경변수
- 화면 세션 상태: Streamlit session state
- 실시간 체결 버퍼: 메모리 전용, 종목당 최근 5분·최대 300건
- 종목 마스터 캐시: 키움 공급자 인스턴스에서 1시간 유지
- 리포트: 생성 당시 JSON 스냅샷으로 불변 저장

## 7. 오류 처리

외부 오류는 인증정보와 원본 응답을 노출하지 않는 사용자용 `ProviderError` 메시지로 변환한다. 수집 결과의 경고와 부분 실패는 리포트에도 기록한다.

서비스는 부분 성공을 허용한다. 예를 들어 기관 수급 조회가 실패해도 외국인 수급과 거래대금 표는 생성한다.

## 8. 테스트 전략

- 도메인·서비스: 외부 통신 없는 단위 테스트
- 공급자: 저장된 응답 fixture를 이용한 파싱 테스트
- 저장소: 임시 SQLite 통합 테스트
- 전체 흐름: 샘플 공급자를 이용한 스모크 테스트
- 실제 API: 별도 수동 검증, 자동 테스트 기본 제외
- 실시간 공급자: 저장된 이벤트 fixture와 SampleRealtimeProvider로 스트림 테스트

## 9. 보안

- `.env`는 커밋하지 않는다.
- `.env.example`에는 빈 값만 둔다.
- 공급자별 필수 키가 모두 비어 있으면 해당 SampleProvider를 사용한다.
- 일부 키만 존재하면 외부 호출을 막고 설정 오류를 표시한다.
- 키움의 기본 연결 환경은 모의투자로 한다.
- API 응답 또는 예외에 인증정보가 포함되지 않게 한다.
- 주문 API 클라이언트는 구현하지 않는다.
- 로그에는 종목·시각·응답 상태만 기록한다.
