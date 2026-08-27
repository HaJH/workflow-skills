# Python Review Rules

리뷰 렌즈. 심각도와 검출 패턴만 둔다. **P** 항목의 정본은 `CLAUDE.md`이며 둘이 어긋나면 CLAUDE.md가
이긴다. 게이트(`ruff` · `ruff format --check` · `mypy` · `pytest`)가 거절하는 것은 findings로 쓰지
않는다 — 보이면 「게이트를 안 돌렸다」 한 줄.

## Severity

- **Critical** — must fix before merge (correctness, safety, security)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## TYPE: Type Safety

**Critical:** `Any` 남용, public 함수의 타입 힌트 완전 누락
**Warning:** `Optional` 처리 없이 `None` 접근, 타입 힌트 부분 누락
**Info:** 제네릭 패턴에서 `TypeVar` 미사용

## ERR: Error Handling

**Critical:** bare `except` + `pass`, 외부 API 에러 미처리, 빈 except 블록
**Warning:** 파일 I/O 에러 미처리, 로깅 없이 re-raise
**Info:** 구체적 예외 대신 `Exception`

## SEC: Security

**Critical:** API 키/시크릿 하드코딩, SQL injection, `eval`/`exec`
**Warning:** 사용자 입력 미검증, 디버그 로그에 민감 정보

## QUAL: Code Quality

**Warning:** 함수 50줄 초과, 중첩 4단계 초과, 매직넘버
**Info:** public docstring 누락, f-string 미사용

## ASYNC: Concurrency

**Critical:** `await` 누락, async 루프 안 동기 I/O
**Warning:** `asyncio.sleep` 대신 `time.sleep`

## TEST: Testing

**Warning:** 테스트 없는 공개 함수, 하드코딩 경로 (`tmp_path` 미사용), 되돌려도 안 깨지는 가드 테스트
**Info:** 엣지 케이스 누락, mock 과도 사용

## P: 프로젝트 고유

(셋업 시 채운다. 게이트가 통과하는데 사고가 나는 자리. 각 항목은 심각도 + 검출 패턴 + `→ CLAUDE.md 「절」`)
