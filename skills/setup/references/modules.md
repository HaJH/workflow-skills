# 모듈 카탈로그

셋업은 **핵심 + 선택 모듈**로 구성한다. 사용자가 고른 모듈만 생성하고, 템플릿 안의
`<!-- module:<id> -->` … `<!-- /module:<id> -->` 블록은 해당 모듈을 골랐을 때만 남긴다
(안 골랐으면 블록 전체를 지운다. 마커 줄 자체는 항상 지운다).

## 핵심 (항상)

| 생성 | 템플릿 |
|---|---|
| `CLAUDE.md` | `claude-md.md` |
| `docs/workflow.md` | `workflow-md.md` |
| `.claude/commands/pm.md` · `commit.md` · `report.md` · `merge-branch.md` | `commands.md` |
| `.gitignore`에 `docs/reports/` · `.claude/settings.local.json` 추가 | — |

## 모듈

| id | 이름 | 기본 | 생성하는 것 | 의존 |
|---|---|---|---|---|
| `review-loop` | 자율 리뷰-수정 루프 | 켬 | `/review` 커맨드, 리뷰 방식에 따른 스킬·에이전트 (`review-loop.md`) | — |
| `commit-rhythm` | 커밋 리듬 (`wip:`) | 켬 | — (CLAUDE.md·workflow.md·커맨드의 블록) | — |
| `board` | 작업 보드 | 켬 | `docs/board.md` · `roadmap.md` · `backlog.md` · `board-archive.md` · `docs/issues/` · `scripts/board-ready.sh` (`board.md`) | — |
| `watch` | PM 진행 감시 | 켬 | `scripts/watch-commits.sh` | `commit-rhythm` |
| `just` | `/just` 절차 생략 커맨드 | 켬 | `.claude/commands/just.md` | — |
| `gate-script` | 게이트 스크립트 | 켬 | `scripts/check.ps1` (Windows) 또는 `scripts/check.sh` | — |
| `hooks` | 훅 (파일 패턴 게이트 + 세션 주입) | 켬 | `.claude/settings.json` · `.claude/hooks/*` (`hooks.md`) | — |
| `discipline` | 개발 규율 문서 | 켬 | `docs/discipline.md` (`discipline-md.md`) | — |
| `design-review` | 설계 검토 게이트 | 끔 | `.claude/skills/design-review/*` · 에이전트 3종 · `docs/design-constitution.md` · `docs/specs/` (`design-review.md`) | — |

의존 모듈을 껐는데 의존하는 모듈을 켰으면 의존 모듈을 같이 켠다고 알리고 켠다.

### `review-loop`의 리뷰 방식 (하위 선택)

| 값 | 규칙 대조·정확성 렌즈 | 구조 판단 렌즈 | 생성 |
|---|---|---|---|
| `mixed` (기본) | 내장 `/code-review <effort>` | 커스텀 `{PREFIX}-refactor-reviewer` (opus/xhigh) | `refactor-review` 스킬 + 에이전트 |
| `official` | 내장 `/code-review <effort>` | 없음 (같은 리뷰가 단순화 제안까지 냄) | — |
| `custom` | 커스텀 `{PREFIX}-code-reviewer` (sonnet/medium) + 언어 규칙 파일 | 커스텀 `{PREFIX}-refactor-reviewer` (opus/xhigh) | 두 스킬 + 두 에이전트 + `review-rules-*.md` |

프로젝트가 렌즈를 더 가지면(예: 프론트엔드) `custom` 골격으로 스킬·에이전트를 짝으로 하나 더
만든다. 티어는 「섞인 렌즈 = 중간(sonnet/high)」.

## 자리표시자

| 이름 | 뜻 | 예 |
|---|---|---|
| `{PROJECT_NAME}` | 프로젝트 이름 | `MyApp` |
| `{PROJECT_PATH}` | 메인 트리 절대 경로, 슬래시 | `F:/Repo/MyApp` |
| `{WORKTREES_PATH}` | 워크트리 부모 경로 | `F:/Repo/MyApp-worktrees` |
| `{PREFIX}` | 에이전트 이름 접두사 | `myapp` |
| `{LANG}` | 주 언어 | `Rust` |
| `{SOURCE_GLOB}` | 리뷰 대상 소스 패턴 | `**/*.rs` |
| `{SOURCE_DIRS}` | 소스 디렉터리 (훅 scopePath·리뷰 대상) | `crates/`, `ui/src/` |
| `{EXCLUDE_DIRS}` | 리뷰 대상에서 빼는 것 (벤더·생성물) | `vendor/`, `node_modules/` |
| `{GATE_CMD}` | 게이트 명령 한 줄 | `.\scripts\check.ps1` |
| `{ROUND_BUDGET}` | 라운드 예산 | `3` |
| `{REVIEW_EFFORT}` | `/code-review`에 넘기는 effort | `high` |
| `{HOSTING}` | 호스팅 | `GitHub (private, gh)` / `완전 로컬` |

모든 경로는 슬래시로 쓴다. 보고서 경로처럼 워크트리에서도 같아야 하는 경로는 반드시 절대 경로다.

### 템플릿 국소 자리표시자

한 템플릿 안에서만 쓰이며 그 파일의 「치환 안내」가 뜻을 정한다. 생성 뒤 잔존 검사 대상이다.

| 이름 | 파일 | 뜻 |
|---|---|---|
| `{ONE_LINE_DESCRIPTION}` · `{LANG_CONVENTIONS}` · `{SKILL_LIST}` | `claude-md.md` | 한 줄 설명 · 언어 컨벤션 절 · 스킬 목록 |
| `{DISPATCH_TABLE}` · `{AUTHORING_POLICY}` · `{RUN_NOTES}` · `{FORMAT_CMD}` | `workflow-md.md` | 디스패치 표 · 지침 작성 정책 절 · 실행 정보 · 포맷 명령 |
| `{SCOPE_OWNER}` · `{LANG_FENCE}` · `{DEP_PROJECT_RULES}` · `{ARCH_DOC}` · `{WHERE_THE_VALUE_IS}` · `{WHERE_THE_VALUE_IS_CONFORMANCE}` | `review-loop.md` | 범위 밖 담당 · 코드 펜스 태그 · 레이어 규칙 · 아키텍처 정본 · 최고 가치 카테고리 |
| `{AREA_1}` · `{AREA_1_SCOPE}` · `{V0_TITLE}` · `{V0_DEFINITION}` | `board.md` | 첫 영역 그룹 · 첫 마일스톤 |
| `{SOURCE_GLOB_LIST}` · `{SOURCE_SAMPLE}` | `hooks.md` · `scripts/file-pattern-map.json` | 훅 룰 patterns 배열(`"*.rs"`, `"*.ts"` 식으로 확장자별) · 검증용 소스 파일 하나 |
| `{DEP_MANIFEST}` | `design-review/design-constitution.md` | 모듈 의존을 선언하는 파일 |
