# TypeScript Review Rules

리뷰 렌즈. 심각도와 검출 패턴만 둔다. **P** 항목의 정본은 `CLAUDE.md`이며 둘이 어긋나면 CLAUDE.md가
이긴다. 게이트(린터 · `tsc` · 포매터)가 거절하는 것은 findings로 쓰지 않는다 — 보이면 「게이트를
안 돌렸다」 한 줄. 미사용 import, 포맷, 린트 규칙 위반은 여기 없다.

React를 쓰면 `review-rules-typescript-react.md`를 덧붙인다.

## Severity

- **Critical** — must fix before merge (correctness, boundary violations)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## TYPE: Type Quality

**Critical:** 외부 경계(IPC·API·파일)의 페이로드 타입을 수기로 재정의 — 생성 타입이나 스키마
추론 타입을 import할 것 (수기 사본은 상대편 변경 시 조용히 어긋난다), 오류 분기를 `error.message`
문자열 매칭으로 — 코드/타입으로 분기할 것
**Warning:** `any`, 근거 없는 `as` 단언, non-null 단언(`!`) — 좁히기 가드 대상, 유니언 리터럴 타입이
존재하는 곳에 느슨한 `string`, exported 함수 반환 타입 누락
**Info:** `unknown` 대신 `any`를 받는 catch/파라미터

## ERR: Error Handling

**Critical:** 호출부가 `void`로 버리는 async 액션의 실패 무시 — 내부에서 catch해 표면의 오류 필드로
라우팅할 것 (unhandled rejection이 유일한 흔적이면 안 된다), 빈 catch
**Warning:** 외부 입력·파일 I/O의 에러 처리 누락, loading/error 상태 누락

## SEC: Security

**Critical:** 비정제 HTML 삽입(XSS), `eval`/`Function`, 경로 traversal
**Warning:** 파일 경로 미검증, 하드코딩 자격증명

## BOUNDARY: 경계 (project-specific)

**Critical:** **P** 백엔드·IPC·네트워크 호출을 단일 게이트웨이 모듈 밖에서 직접 — 게이트웨이의
존재 이유가 조용히 거짓이 된다. 새 백엔드 접점마다 확인
**Critical:** **P** 생성물(`*.gen.ts`, 바인딩) 수동 편집 제안·수행 — 상류를 고치고 재생성
**Warning:** 루프 안 원격 호출 (N+1), 낙관적 갱신이 확정 응답과 경합 — 확정 스냅샷이 단일 진실 소스

## STRUCT: Structure

**Warning:** 3+줄 중복 블록 → 공유 함수/컴포넌트, 역할이 섞인 모듈 → 역할선으로 분할, 모듈 간 직접
결합(다른 모듈의 내부 상태에 의존)
**Info:** 하드코딩 값 (매직넘버·문자열)

## TEST: Testing

**Warning:** 테스트 없는 공개 함수, 되돌려도 안 깨지는 가드 테스트
**Info:** 엣지 케이스 누락, snapshot 테스트 과도 의존

## P: 프로젝트 고유

(셋업 시 채운다. BOUNDARY의 게이트웨이 경로·생성물 목록을 구체 경로로. 각 항목은 심각도 + 검출
패턴 + `→ CLAUDE.md 「절」`)
