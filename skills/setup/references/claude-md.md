# CLAUDE.md 템플릿

아래를 `{PROJECT_PATH}/CLAUDE.md`로 생성한다. 자리표시자를 치환하고 모듈 블록을 처리한다.
사용자의 글로벌 `~/.claude/CLAUDE.md`에 이미 있는 규칙(턴 종료 보고, AskUserQuestion 확인,
커밋 메시지 자동 문구 금지)은 복제하지 않는다.

```markdown
# {PROJECT_NAME}

{ONE_LINE_DESCRIPTION}

## 기본 원칙

- 응답/계획: 한국어, 코드/주석: 영어
- Windows 기준
- **지침·스킬 문서는 지시문 + 증상만 쓴다.** 날짜·이슈 ID를 건 사례, 측정치, 경위 금지.
  세는 값을 박지 않는다 → `docs/workflow.md` 「지침 작성 정책」
- **세션 내 확정 사실 재실측 금지** — 이번 세션에서 읽은 파일·명령 출력·사용자 답변은
  그대로 쓴다 → `docs/workflow.md` 「세션 내 확정 사실」

## Git

- 호스팅: {HOSTING}
- 브랜치: `main`(안정) + `feature/*` + `hotfix/*`
- **main 직접 코드 커밋 금지** — 로컬 `git merge --no-ff`로만 반영 (squash 금지)
- **메인 트리 `{PROJECT_PATH}`는 항상 `main`에 둔다.** 코드를 고치는 작업은 예외 없이
  워크트리 `{WORKTREES_PATH}/<브랜치명에서 feature/ 뗀 이름>`에서 한다. 메인 트리에서
  브랜치를 바꾸면 같은 워킹트리를 쓰는 에디터·다른 세션의 미커밋 변경이 그 브랜치로 딸려간다
- **코드 변경이 없는 문서 작업은 main 직접 커밋** (`docs/` 전체·`*.md`). 코드와 함께
  바뀌는 문서는 그 코드의 브랜치를 탄다
- `cd` 패턴 금지 → `git -C` 사용
- 상세 절차: `docs/workflow.md`

<!-- module:board -->
## 작업 관리

- `docs/board.md` — 간이 칸반보드 (In Progress / ToDo). 갱신은 `/pm`이 담당
- `docs/roadmap.md` — 마일스톤 로드맵 · `docs/backlog.md` — 탈락·후순위 · `docs/board-archive.md` — 완료
- `docs/issues/<id>.md` — 카드의 배경·경위·결정. **카드는 한 줄이고 상세는 여기로**
- `bash scripts/board-ready.sh` — 착수 가능 카드·낡은 선행·깨진 참조
- 흐름은 `이슈 → 설계 → 구현 → 완료`. 설계 문서는 이슈의 산출물이지 일감의 출처가 아니다
<!-- /module:board -->

## 에이전트 행동

- **착수 게이트 — 조사 ≠ 착수**: 질문·문제 제시 턴의 산출물은 조사 보고 + 방향 제안이다.
  사용자 허락 후에만 파일을 바꾼다. 예외는 정확히 지정된 사소한 단일 수정
- 피처 브랜치 작업은 확인 없이 진행. **반드시 확인**: main 머지, 설계 변경
<!-- module:commit-rhythm -->
- **Dev는 논리 단위마다 커밋한다.** 진행 중 깨진 상태는 `wip:` 접두사로 커밋하고 게이트를
  요구하지 않는다. 게이트는 보고·리뷰·머지 시점의 HEAD에만 → `docs/workflow.md` 「커밋 리듬」
<!-- /module:commit-rhythm -->
- **사용자에게 빌드·실행·확인을 요청하지 않는다.** 확인은 머지 뒤 실사용에서 한다. 예외는
  혼자 원인을 확정할 수 없어 관측이 필요할 때뿐 → `docs/workflow.md` 「사용자 확인은 머지 뒤다」
- **메모리에 영구 규칙 금지** — 메모리는 머신 로컬이고 서브에이전트에 전달되지 않는다.
  영구 규칙은 이 파일·`docs/`·스킬 문서로

<!-- module:review-loop -->
## 피처 완료 흐름

Dev 자율 진행. 매 라운드:

1. `/report`
2. **대상 조립** — `main...HEAD` + 미커밋 + 미추적의 합집합에서 `{EXCLUDE_DIRS}`를 뺀다
3. **병렬 디스패치** — 리뷰들을 한 메시지에. 클린 컨텍스트이고 티어를 고정한다
   → `docs/workflow.md` 「자율 리뷰-수정 루프」의 디스패치 표
4. **수정** — 이슈 하나당 커밋. 라운드 끝에 게이트 통과 + 보고서 갱신
5. **수렴 판정** — 최고 등급이 남았으면 1로. 없으면 종료
6. PM에게 보고

낮은 등급을 0으로 만들려 들지 않는다 — 사유를 보고서에 적고 넘긴다. 라운드 예산은
{ROUND_BUDGET}이고 도달하면 자동으로 넘기지 않고 사용자 판단을 받는다.
`/review-*` 스킬은 **대상 지정 임시 점검 전용**(인자 필수)이다.
<!-- /module:review-loop -->

## 커맨드

- `/pm` — PM 세션 시작
- `/commit` — 커밋 생성
- `/report` — Dev 보고서 작성/업데이트
<!-- module:review-loop -->
- `/review <branch>` — Reviewer 코드 리뷰
<!-- /module:review-loop -->
- `/merge-branch <branch>` — 승인 브랜치를 main에 머지
<!-- module:just -->
- `/just <할 일>` — 절차 생략 모드. 요청한 작은 변경만 현재 트리에서 바로
<!-- /module:just -->

<!-- module:review-loop -->
## 스킬

{SKILL_LIST}
<!-- /module:review-loop -->

<!-- module:design-review -->
## 설계 검토 게이트

규모 있는 변경(구조 변경·신규 서브시스템·인터페이스 변경)은 구현 전 `docs/specs/`에 spec을
쓰고, spec에 코드 구조 설계가 들어 있으면 커밋 전 `/design-review`. **Blocker 기각은 사용자
결정**이며 수용된 결정은 spec에 「감수한 대가」로 기록한다 → `docs/design-principles.md`
<!-- /module:design-review -->

<!-- module:discipline -->
## 개발 규율

관측 없이 인과를 단정하지 않는다 · 테스트가 무엇을 지지하는지 되돌려 본다 · 세지 말고
누구를 적는다 · 주석은 기본값이 없음 → `docs/discipline.md`. Dev와 Reviewer 양쪽에 적용된다.
<!-- /module:discipline -->

## {LANG} 컨벤션

{LANG_CONVENTIONS}
```

## 치환 안내

- `{SKILL_LIST}`: 리뷰 방식에 따라. `mixed` → `/refactor-review` 한 줄. `custom` → `/review-code`
  + `/refactor-review`(+ 추가 렌즈). `official` → 「스킬」 절 자체를 지운다.
- `{LANG_CONVENTIONS}`: 게이트 명령(`{GATE_CMD}`), 포매터·린터, 프로젝트 고유 금지사항.
  글로벌 언어 스킬(`rust-guide` 등)이 있으면 「패턴·관용구는 글로벌 `<스킬>` 참조」 한 줄로
  갈음하고 여기에 중복 작성하지 않는다. `review-loop`가 `mixed`/`official`이면 내장
  `/code-review`가 읽는 규칙이 이 절뿐이므로 **툴이 잡지 못하는 프로젝트 고유 규칙**을
  여기에 둔다(린터가 잡는 것은 쓰지 않는다).
