# C++ Review Rules

리뷰 렌즈. 심각도와 검출 패턴만 둔다. **P** 항목의 정본은 `CLAUDE.md`(또는 프로젝트 코딩 규칙
문서)이며 둘이 어긋나면 정본이 이긴다. 컴파일러·clang-tidy·포매터가 거절하는 것은 findings로 쓰지
않는다 — 보이면 「게이트를 안 돌렸다」 한 줄.

엔진/프레임워크 규칙은 addon 파일(`review-rules-cpp-<framework>.md`)로 덧붙인다.

## Severity

| Severity | Criteria |
|---|---|
| **Critical** | 런타임 오류, 빌드 파손, 정책 위반 (예외 사용, `new`/`delete`, 초기화되지 않은 포인터) |
| **Warning** | 가이드라인 위반, 유지보수성 (네이밍, `const`/`override`/`explicit` 누락) |
| **Info** | 개선 제안 |

## NC: Naming Conventions

**Warning:** PascalCase 미준수, bool 변수 `b` 접두사 누락, 함수명 동사 미시작, out 파라미터 `Out` 접두사 누락
**Info:** 과도한 축약 (루프 변수 외 3자 미만)

**Check pattern**: 클래스 선언, bool 변수, 함수명, non-const `&` 파라미터.

## FMT: Formatting

**Critical:** **P** 익명 네임스페이스 — Unity Build 병합 시 동명 심볼 충돌로 빌드 파손 (Unity Build
프로젝트 한정)
**Warning:** `#pragma once` 누락, 여는 중괄호 위치 불일치, 탭/스페이스 불일치, 한 줄에 여러 변수 선언,
파일 스코프 `using namespace`
**Info:** 단일 구문 if/else 중괄호 누락

**Check pattern**: `namespace {`, `using namespace` at file scope, 줄 끝 `{`.

## ES: Expressions & Statements

**Critical:** `NULL`/`0` 포인터 값 (→ `nullptr`), `const_cast`, 초기화되지 않은 포인터
**Warning:** 가상 오버라이드에 `override` 누락, 단일 인자 생성자에 `explicit` 누락, 상태를 바꾸지 않는
멤버 함수에 `const` 누락, 포인터 타입에 `auto` (→ `auto*`), `typedef` (→ `using`)
**Info:** 변수 선언이 사용 지점과 먼 곳, 이름 없는 매직 상수 (0/1/true/false 제외)

**Check pattern**: `= NULL`, 포인터 `= 0`, `virtual` without `override`, 단일 파라미터 생성자.

## EH: Error Handling

**Critical:** `throw`/`try`/`catch` (예외 금지 정책 시), null 체크 없는 포인터 역참조
**Warning:** 함수 전제조건 assertion 누락

**Check pattern**: Grep `throw `, `try {`, `catch (`.

## R: Resource Management

**Critical:** 리소스 관리 클래스 밖의 직접 `new`/`delete`, `malloc`/`free`
**Warning:** 소유권이 불명확한 원시 포인터 멤버, RAII 없는 리소스 획득

**Check pattern**: Grep `= new `, `delete `, `malloc(`, `free(`.

## TEST: Testing

**Warning:** 테스트 없는 공개 함수, 되돌려도 안 깨지는 가드 테스트
**Info:** 엣지 케이스 누락

## P: 프로젝트 고유

(셋업 시 채운다. 컴파일도 게이트도 통과하는데 사고가 나는 자리 — 예: 래퍼 우회, 모듈 의존 방향,
fail-safe 처리. 각 항목은 심각도 + 검출 패턴 + `→ 정본 「절」`)
