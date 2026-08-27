# Rust Review Rules

리뷰 렌즈. 심각도와 검출 패턴만 둔다. **P** 항목의 정본은 `CLAUDE.md`이며 둘이 어긋나면 CLAUDE.md가
이긴다. 게이트(`cargo fmt --check` · `clippy -D warnings` · `cargo test`)가 거절하는 것은 findings로
쓰지 않는다 — 보이면 「게이트를 안 돌렸다」 한 줄.

## Severity

- **Critical** — must fix before merge (correctness, safety, security)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## OWN: Ownership & Lifetimes

**Critical:** 대용량 데이터의 불필요한 clone, 댕글링 참조, `'static` 남용
**Warning:** 참조로 충분한 곳에서 소유권 이전, 불필요한 `Arc`/`Rc`

## ERR: Error Handling

**Critical:** 프로덕션 경로의 `unwrap`/`expect`/`panic!` (워크스페이스에 `[lints]`가 없으면 clippy
기본값이 허용하므로 게이트가 못 잡는다), 에러 삼킴
**Warning:** 컨텍스트 없는 `?` 전파, `Box<dyn Error>` 남용

## ASYNC: Concurrency

**Critical:** `await` 누락, `Send` 바운드 미충족, 데드락 가능성
**Warning:** 불필요한 `block_on`, `unbounded_channel` 무분별 사용, async 안 동기 I/O

## SEC: Security

**Critical:** 미검증 `unsafe`, 외부 입력 미검증, 하드코딩 시크릿
**Warning:** `unsafe`의 `// SAFETY:` 주석 누락, 프로세스 호출 시 인자 이스케이프 누락

## QUAL: Code Quality

**Warning:** 함수 50줄 초과, 중첩 4단계 초과, `pub` 과도 노출, 매직넘버
**Info:** `todo!()` 잔존, type alias 부재

## SERDE: Serialization

**Warning:** `serde(default)` 누락, `rename_all` 불일치

## TEST: Testing

**Warning:** 테스트 없는 공개 함수, 하드코딩 경로 (`tempdir` 미사용), 되돌려도 안 깨지는 가드 테스트
**Info:** 테스트명이 동작 미설명

## P: 프로젝트 고유

(셋업 시 채운다. 컴파일도 게이트도 통과하는데 사고가 나는 자리 — 예: 레이어 경계 위반, 라이선스
격리 위반, 생성물 수동 편집. 각 항목은 심각도 + 검출 패턴 + `→ CLAUDE.md 「절」`)
