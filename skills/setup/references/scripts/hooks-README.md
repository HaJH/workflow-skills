# Claude Code Hooks

## SessionStart / SubagentStart — 프로젝트 컨텍스트 자동 로드

`session-start.ps1`이 컨텍스트를 `additionalContext`로 주입한다. 계층화한다:

- **항상 (메인 + 서브)**: `session-start-header.md` — 반복 위반 함정 + 상세 문서 인덱스
- **메인 세션만 추가**: `docs/workflow.md` — 서브에이전트는 git·보고서 워크플로를 안 하므로 제외
- **온디맨드 (주입 X)**: 헤더 인덱스가 가리키는 나머지 문서. 필요할 때 Read

문서 목록 변경은 `session-start.ps1`의 `$files` 편집.

**SubagentStart도 등록하는 이유**: 서브에이전트는 부모 세션의 CLAUDE.md·settings 훅·SessionStart
컨텍스트를 상속하지 않는다. 같은 스크립트를 등록해야 메인/서브 동작이 같아진다.
`additionalContext`는 user context에 들어가므로 컨텍스트 압축 시 드롭될 수 있다.

## PreToolUse — Edit/Write 게이트 + 환기

matcher는 `Edit|Write|Read|Skill`. 역할이 둘이다.

- **관측 (Read/Skill)**: 어떤 문서를 Read했고 어떤 스킬을 로드했는지 세션 상태 파일에 기록만 하고 통과
- **게이트+환기 (Edit/Write)**: 파일 경로를 `file-pattern-map.json` 룰과 매칭. 매칭된 룰에
  `requires`가 있고 미이행이면 **`permissionDecision: deny`로 편집을 차단**하고 무엇을 해야 하는지
  안내. 이행됐으면 룰 메시지를 `additionalContext`로 주입

**셸로 읽으면 인정되지 않는다** — `cat`/`sed`로 열어도 훅은 알 수 없다. `Read` 툴과 `Skill` 툴만.

### 경로 정규화 — 워크트리

파일 경로는 프로젝트 상대경로로 정규화한 뒤 매칭한다. 워크트리 규약
(`<parent>/<Repo>-worktrees/<폴더>/`)을 먼저 인식하므로 워크트리에서 편집해도 메인 트리와 동일하게
매칭된다. 단순 prefix 매칭이면 `<Repo>-worktrees/...`가 `<Repo>`에 걸려 상대경로가 잘리고 룰이
전부 빗나간다.

### 룰 스키마

```json
{
  "id": "고유 ID",
  "patterns": ["*.rs", "Source/Foo/*.cpp"],
  "scopePath": ["crates/"],
  "excludePath": ["vendor/"],
  "requires": {
    "reads": ["CLAUDE.md"],
    "skills": ["rust-guide"]
  },
  "message": "환기 메시지 — 정본 경로를 가리키는 포인터"
}
```

| 필드 | 의미 |
|---|---|
| `id` | 룰 고유 식별자. 세션당 1회 알림 추적에 사용 |
| `patterns` | 파일명 또는 상대경로 와일드카드 (PowerShell `-like`). `**` 미지원 — 디렉터리 제약은 `scopePath` |
| `scopePath` | (선택) 상대경로가 이 prefix 중 하나로 시작해야 매칭 |
| `excludePath` | (선택) 상대경로에 이 substring 포함 시 제외 |
| `requires` | (선택) 편집 전 이행할 것. `reads`는 프로젝트 상대경로, `skills`는 스킬 이름. 미이행 시 **차단** |
| `message` | 게이트 통과 후 주입할 환기. **규칙 요약을 복제하지 않는다** — 정본이 바뀌면 낡는다 |

### 매칭 동작

- 한 파일에 여러 룰 동시 매칭 가능 → 모두 알림. `requires`는 합쳐진다
- 알림은 **세션당 룰 id별 1회**. 게이트는 이행될 때까지 **매 편집마다** 검사
- 상태 파일: `$env:TEMP\claude-code-hook-state\fired-rules-{session_id}.txt` · `requires-done-{session_id}.txt`
- 예외 시 exit 0 — 깨진 훅이 작업을 막지 않는다

### requires 승격 기준

새 룰은 `message`로 시작하고, 지침이 그 문서를 「필수 / 정독 후 진행」이라 선언한 경우에만
`requires`로 올린다. **편집 시점이 아닌 요구**(커밋 전·머지 전 게이트)는 `requires`로 걸지
않는다 — 작성 자체가 막힌다.

**`reads` 경로와 `skills` 이름은 실재해야 한다.** 오타가 있으면 그 항목은 영원히 충족되지 않아
해당 파일을 **아무도 편집할 수 없다.** 룰 추가 후 반드시 「검증 방법」으로 확인.

### 검증 방법

```powershell
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"<프로젝트 절대경로>/<룰에 걸리는 파일>"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1
```

매칭 + 미이행 시 `permissionDecision: deny` JSON. 이행 후 재실행 시 `additionalContext` JSON.
매칭 없으면 빈 출력. 상태 리셋:

```powershell
Remove-Item "$env:TEMP\claude-code-hook-state\*-test.txt" -ErrorAction SilentlyContinue
```

## 파일 인코딩

- `*.ps1`: **ASCII 문자만** (PowerShell 5.1 cp949 기본 — BOM 없는 한글 리터럴 깨짐)
- `*.json` 룰 파일, `*.md` 헤더: UTF-8 (스크립트가 `-Encoding UTF8`로 명시 로드)

## settings 등록

`.claude/settings.json`(팀 공유)에 등록되어 있다. settings를 수정한 직후엔 `/hooks` 메뉴를 한 번
열거나 재시작해야 반영된다.
