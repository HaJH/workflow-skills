# 훅 (module: hooks)

두 장치를 한 모듈로 묶는다. 같은 상태 파일(읽은 문서·로드한 스킬 기록)을 공유한다.

| 장치 | 훅 | 하는 일 |
|---|---|---|
| 세션 컨텍스트 주입 | `SessionStart` · `SubagentStart` | `session-start-header.md`(반복 위반 함정 + 상세 문서 인덱스)를 `additionalContext`로 주입. 메인 세션에는 `docs/workflow.md`도 |
| 파일 패턴 게이트 | `PreToolUse` (`Edit\|Write\|Read\|Skill`) | `file-pattern-map.json` 룰에 걸리는 파일을 편집하기 전에 정본 Read·스킬 로드를 강제(미이행 시 deny). 통과하면 환기 메시지를 세션당 1회 주입 |

**왜 SubagentStart도 등록하나**: 서브에이전트는 부모 세션의 CLAUDE.md·SessionStart 컨텍스트를
상속하지 않는다. 리뷰어 에이전트가 프로젝트 규칙을 알게 하는 공식 경로가 이것뿐이다.
`additionalContext`는 user context에 들어가므로 컨텍스트 압축 시 드롭될 수 있다.

**왜 파일 패턴 게이트인가**: 지침에 「편집 전 X를 읽는다」가 있어도 읽지 않고 편집하는 위반이
반복된다. 게이트는 그 편집을 막고 무엇을 읽어야 하는지 말한다. 셸(`cat`)로 읽으면 인정되지
않는다 — `Read` 툴과 `Skill` 툴만 기록된다.

## 생성 파일

| 대상 | 원본 | 치환 |
|---|---|---|
| `.claude/settings.json` | `scripts/settings.json` | 없음 (기존 settings.json이 있으면 `hooks` 키를 병합) |
| `.claude/hooks/session-start.ps1` | `scripts/session-start.ps1` | 없음 |
| `.claude/hooks/session-start-header.md` | `scripts/session-start-header.md` | `{PROJECT_NAME}` · 모듈 블록 |
| `.claude/hooks/pre-tool-use.ps1` | `scripts/pre-tool-use.ps1` | 없음 |
| `.claude/hooks/file-pattern-map.json` | `scripts/file-pattern-map.json` | `{SOURCE_GLOB_LIST}` · `{SOURCE_DIRS}` · 모듈 블록(JSON이라 주석 대신 아래 표로 처리) |
| `.claude/hooks/README.md` | `scripts/hooks-README.md` | 없음 |

`file-pattern-map.json`의 기본 룰:

| id | 대상 | requires | 남기는 조건 |
|---|---|---|---|
| `source` | `{SOURCE_GLOB_LIST}` in `{SOURCE_DIRS}` | reads: `CLAUDE.md` (+ `docs/discipline.md`) | 항상. `discipline` 모듈이 없으면 그 경로를 뺀다 |
| `instructions` | `CLAUDE.md`, `docs/workflow.md`, `docs/discipline.md`, `.claude/hooks/session-start-header.md`, `.claude/skills/*`, `.claude/agents/*`, `.claude/commands/*` | 없음 (message만) | 항상 |
| `hook-config` | `.claude/hooks/*` | reads: `.claude/hooks/README.md` | 항상 |
| `specs` | `docs/specs/*.md` | 없음 (message: `/design-review`) | `design-review` 모듈 |
| `board` | `docs/board.md`, `docs/board-archive.md` | 없음 (message: 선행 줄·`board-ready.sh`) | `board` 모듈 |

도메인 룰(특정 서브시스템 파일 → 그 가이드)은 프로젝트가 추가한다. 스킬은 자리만 만든다.

## 검증 (생성 직후 반드시)

```powershell
# 파일 패턴 게이트 — source 룰에 걸리는 경로로. deny JSON이 나와야 한다
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1

# Read를 기록한 뒤 다시 — additionalContext JSON(환기)이 나와야 한다
$json = '{"session_id":"test","tool_name":"Read","tool_input":{"file_path":"{PROJECT_PATH}/CLAUDE.md"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1
# (discipline 모듈이 있으면 docs/discipline.md Read도 한 번)
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1

# 세션 주입 — additionalContext에 헤더 내용이 들어 있어야 한다
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1 -HookEventName SubagentStart

# 상태 리셋
Remove-Item "$env:TEMP\claude-code-hook-state\*-test.txt" -ErrorAction SilentlyContinue
```

`requires.reads`의 경로가 실재하는지 `Test-Path`로 확인한다. 오타가 있으면 그 룰에 걸린 파일을
아무도 편집할 수 없다.

## 워크트리 경로

훅은 `<parent>/<Repo>-worktrees/<folder>/<rel>`을 먼저 인식해 프로젝트 상대 경로로 정규화한다.
워크트리 규약이 이 형태여야 룰이 워크트리에서도 맞는다.

## 룰 작성 규칙

`authoring-policy.md` 「훅 룰 작성」·「session-start-header 승격 기준」. 생성 후에는
`.claude/hooks/README.md`가 그 프로젝트의 정본이다.
