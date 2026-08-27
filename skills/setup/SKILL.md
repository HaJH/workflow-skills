---
name: setup
description: "Use when initializing a new local project (no CI, no remote MR) with the PM-Dev-Reviewer workflow - CLAUDE.md, docs/workflow.md, commands, and selectable modules (autonomous review loop, commit rhythm, board, progress watch, /just, gate script, hooks, discipline doc, design-review gate). Also use to re-apply or update the workflow in an existing project. Not for GitLab/GitHub MR-based CI workflows."
---

# Setup Project Workflow

로컬 머지 기반 PM-Dev-Reviewer 워크플로를 **핵심 + 선택 모듈**로 셋업한다. CI가 없으므로 로컬
리뷰가 조용히 통과하면 잡아줄 뒷단이 없다 — 그것을 막는 장치(인자 필수·수렴 조건·프로파일링·
파일 패턴 게이트)가 이 워크플로의 값이다.

모든 템플릿은 `references/`에 있다. 이 문서는 절차 인덱스다. **이 스킬을 고칠 때도
`references/authoring-policy.md`를 따른다** — 규칙+증상만, 사례·날짜·세는 값 금지.

## 절차

### 1. 정보 수집

사용자에게 확인 (`references/modules.md` 「자리표시자」):

- 프로젝트 이름 · 한 줄 설명 · 주 언어 · 메인 트리 절대 경로
- 워크트리 부모 경로 (기본 `<parent>/<Repo>-worktrees`)
- 호스팅 (GitHub private / 완전 로컬)
- 소스 디렉터리 · 소스 glob · 리뷰에서 뺄 디렉터리(벤더·생성물)
- 게이트 명령 (포매터·린터·테스트·빌드)
- 추가 컨벤션

기존 프로젝트에 재적용하면 현재 `CLAUDE.md`·`docs/workflow.md`·`.claude/`를 먼저 읽고, 프로젝트
고유 절(컨벤션·실행 정보·도메인 규칙)을 보존한다.

### 2. 모듈 선택

`references/modules.md`의 표를 AskUserQuestion(multiSelect)으로 낸다. 기본값이 켜진 것은 뺄 것을
묻고, `design-review`는 켤지 묻는다. 의존 모듈은 함께 켠다.

`review-loop`를 골랐으면 리뷰 방식을 묻는다: `mixed`(기본) / `official` / `custom`. 그리고
라운드 예산(기본 3)과 `/code-review` effort(기본 `high`)를 확정한다.

`review-loop`가 `mixed`·`custom`이면 **「Where the value is」**를 묻는다 — 그 프로젝트에서 컴파일도
게이트도 통과하는데 사고가 나는 구조 결함 하나나 둘. 답이 없으면 언어 기본값(레이어 경계 위반)으로.

### 3. 파일 생성

템플릿을 복사하고 자리표시자를 치환하고 모듈 블록을 처리한다 (`<!-- module:X -->` 블록은 X를
골랐을 때만, `<!-- module:!X -->`는 안 골랐을 때만 남긴다. 마커 줄은 항상 지운다).

| 대상 | 템플릿 |
|---|---|
| `CLAUDE.md` | `references/claude-md.md` |
| `docs/workflow.md` | `references/workflow-md.md` (+ `authoring-policy.md` 절 삽입) |
| `.claude/commands/*.md` | `references/commands.md` |
| `.gitignore` | `docs/reports/` · `.claude/settings.local.json` 추가 |
| [discipline] `docs/discipline.md` | `references/discipline-md.md` |
| [review-loop] 스킬·에이전트 | `references/review-loop.md` (+ `custom`이면 `review-rules-{lang}.md` → `references/rules.md`) |
| [board] 보드 문서 4종 · `docs/issues/` · `scripts/board-ready.sh` | `references/board.md` · `references/scripts/board-ready.sh` |
| [watch] `scripts/watch-commits.sh` | `references/scripts/watch-commits.sh` |
| [just] `.claude/commands/just.md` | `references/commands.md` 「/just」 |
| [gate-script] `scripts/check.ps1` | `references/scripts/check.ps1` (언어 블록만 남긴다) |
| [hooks] `.claude/settings.json` · `.claude/hooks/*` | `references/hooks.md` · `references/scripts/` |
| [design-review] 스킬·에이전트 3종·설계 헌법·`docs/specs/` | `references/design-review.md` · `references/design-review/` |

생성 문서 전체가 `references/authoring-policy.md`의 문체를 따라야 한다 — 프로젝트 고유 절을 쓸
때도 사례·날짜·세는 값을 넣지 않는다.

### 4. 검증

- [hooks] `references/hooks.md` 「검증」의 명령을 실제로 돌린다. `requires.reads` 경로가 실재하는지
  `Test-Path`로 확인한다 — 오타가 있으면 그 룰에 걸린 파일을 아무도 편집할 수 없다
- [board] `bash scripts/board-ready.sh`가 exit 0
- [gate-script] `scripts/check.ps1`이 현재 트리에서 통과하거나, 실패 이유가 프로젝트 상태(미완성
  코드)이지 스크립트가 아님을 확인
- 자리표시자 잔존 검사: `grep -rn '{[A-Z_]*}' CLAUDE.md docs .claude scripts`가 0건
- 모듈 마커 잔존 검사: `grep -rn 'module:' CLAUDE.md docs .claude`가 0건

### 5. 커밋

```bash
git add CLAUDE.md docs .claude .gitignore scripts
git commit -m "Add project workflow setup"
```

## 설계 원칙 (왜 이 모양인가)

- **리뷰는 클린 컨텍스트에서.** 자기가 쓴 코드를 자기가 판정하지 않는다. 대화 이력을 넘기지 않고
  대상 파일 목록만 넘긴다
- **티어는 고정한다.** 상속시키면 라운드마다 판정 기준이 달라진다. 내장 `/code-review`는 effort를
  인자로, 커스텀 에이전트는 frontmatter로
- **낮은 등급을 0으로 만들지 않는다.** 주석 자기증식으로 되돌아간다
- **예산 연장은 문서를 고쳐서 하지 않는다.** 그 브랜치에 한해서만
- **사용자 액션을 게이트로 두지 않는다.** 확인은 머지 뒤 실사용에서. 요청은 관측이 필요할 때만
- **게이트 목록은 한 곳에.** 문서가 명령을 나열하면 스크립트와 갈라진다
- **서브에이전트는 CLAUDE.md를 상속하지 않는다.** 에이전트 본문이 정본을 경로로 가리키고, 훅이
  헤더를 주입한다
- **지침에 있어도 읽지 않으면 위반은 반복된다.** 파일 패턴 게이트가 편집 전 Read를 강제한다

## 참조

| 파일 | 내용 |
|---|---|
| `references/modules.md` | 모듈 카탈로그 · 자리표시자 |
| `references/authoring-policy.md` | 지침 작성 정책 (스킬 자신 + 생성 문서) |
| `references/claude-md.md` · `workflow-md.md` · `discipline-md.md` | 문서 템플릿 |
| `references/commands.md` | 커맨드 6종 |
| `references/review-loop.md` | 리뷰 방식 3안 · 디스패치 표 · 스킬/에이전트 골격 |
| `references/board.md` · `hooks.md` · `design-review.md` | 모듈 상세 |
| `references/scripts/` | 복사할 스크립트·훅·설정 |
| `references/review-rules-*.md` | 언어별 리뷰 렌즈 (`custom`만) |
