# 프로젝트 컨텍스트 자동 로드

이하는 SessionStart/SubagentStart 훅이 매 세션·에이전트에 주입하는 {PROJECT_NAME} 핵심 규칙이다.
**작업 규모와 무관하게 적용된다.** 상세 규칙은 아래 「상세 문서」를 작업 진입 시 Read.

## 반복 위반 함정 — 매 세션 재인지

지침에 있어도 반복 위반된 항목만 올린다. _강조용이며 진실 소스는 각 지침 문서._ 위반이 멎으면
내린다.

- **🚫 메인 트리는 항상 `main`** — 코드는 예외 없이 워크트리에서. 메인 트리에서 브랜치를 바꾸면
  다른 세션·에디터의 미커밋 변경이 딸려간다 → `CLAUDE.md` 「Git」
- **🚫 조사 ≠ 착수** — 질문 턴의 산출물은 보고 + 방향 제안. 사용자 허락 후에만 파일 변경 →
  `CLAUDE.md` 「에이전트 행동」
- **🚫 사용자에게 빌드·실행·확인 요청 금지** — 확인은 머지 뒤 실사용. 예외는 관측이 필요할 때뿐 →
  `docs/workflow.md` 「사용자 확인은 머지 뒤다」
- **🚫 세션 내 확정 사실 재실측 금지** → `docs/workflow.md` 「세션 내 확정 사실」
- **🚫 지침·문서에 사례·날짜·세는 값 금지** → `docs/workflow.md` 「지침 작성 정책」
<!-- module:commit-rhythm -->
- **논리 단위마다 커밋, 깨진 상태는 `wip:`** — 게이트는 보고·리뷰·머지 시점 HEAD에만 →
  `docs/workflow.md` 「커밋 리듬」
<!-- /module:commit-rhythm -->
<!-- module:review-loop -->
- **리뷰는 클린 컨텍스트 + 티어 고정** — `general-purpose` 금지. `/code-review`에는 effort 명시 →
  `docs/workflow.md` 「자율 리뷰-수정 루프」
<!-- /module:review-loop -->
<!-- module:discipline -->
- **주석 기본값은 없음** — 쓰기 직전 3문 → `docs/discipline.md` 「주석」
- **세지 말고 누구를 적는다** — `Consumers:` 고정 표기 → `docs/discipline.md`
<!-- /module:discipline -->
- **메모리에 영구 규칙 금지** → `CLAUDE.md` 「에이전트 행동」

## 상세 문서 — 작업 진입 시 Read (매 세션 통째 주입 X)

- **워크플로·역할·루프·보고서·머지** → `docs/workflow.md` _(메인 세션에는 주입됨)_
<!-- module:discipline -->
- **개발 규율 (관측·테스트·서술·주석)** → `docs/discipline.md`
<!-- /module:discipline -->
- **{LANG} 컨벤션·게이트** → `CLAUDE.md` 「{LANG} 컨벤션」
<!-- module:board -->
- **작업 보드 규칙** → `docs/board.md` 상단
<!-- /module:board -->
<!-- module:design-review -->
- **설계 원칙·설계 검토** → `docs/design-principles.md` · `.claude/skills/design-review/SKILL.md`
<!-- /module:design-review -->
- **훅 룰 추가·검증** → `.claude/hooks/README.md`
