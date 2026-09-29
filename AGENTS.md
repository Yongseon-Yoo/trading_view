# 주식대시보드YS Agent Guide

## 작업 원칙

1. 구현 전에 `docs/PRD.md`, 관련 컴포넌트 스펙, `docs/ARCHITECTURE.md`, `docs/ADR.md`를 읽는다.
2. 현재 Phase는 `docs/IMPLEMENTATION_PLAN.md`에서 확인한다.
3. 요구 변경은 코드보다 문서를 먼저 수정한다.
4. 시스템이 투자 판단을 대신하도록 기능을 확장하지 않는다.
5. 외부 API 응답을 UI에서 직접 파싱하지 않는다.
6. 실제 API 키가 없어도 샘플 모드와 테스트가 동작해야 한다.
7. 주문 API와 실계좌 거래 기능을 구현하지 않는다.
8. API 키, Secret, 토큰, 계좌번호를 코드·로그·fixture에 남기지 않는다.

## 기술 규칙

- Python 타입 힌트를 사용한다.
- 공급자, 서비스, 저장소, UI 계층을 분리한다.
- 서비스 계층은 Streamlit을 import하지 않는다.
- 외부 응답은 도메인 모델로 변환한다.
- 시간은 timezone-aware datetime으로 다룬다.
- 한국 시장 시간은 `Asia/Seoul`을 기준으로 한다.
- 리포트 스냅샷은 생성 후 변경하지 않는다.
- 예외를 무시하지 말고 사용자용 상태로 변환한다.

## 검증 규칙

- 기능 구현에는 관련 단위 테스트를 함께 추가한다.
- 외부 API 자동 테스트에는 실제 키를 요구하지 않는다.
- 실제 API 검증은 수동 통합 테스트로 분리한다.
- Phase 종료 전에 전체 테스트를 실행한다.
- 실패에서 얻은 재사용 가능한 교훈은 `docs/LEARNINGS.md`에 기록한다.

## 실행 명령어

가상환경 생성 및 `python -m pip install -e '.[dev]'` 후 아래 명령을 기준으로 한다.

```bash
python -m pytest -q
ruff check .
ruff format --check .
streamlit run app.py
```

명령이 바뀌면 이 문서와 README를 함께 수정한다.
