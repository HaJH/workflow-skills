# 자율 리뷰-수정 루프 (module: review-loop)

루프의 절차와 수렴 판정은 `workflow-md.md`에 있다. 이 문서는 **리뷰 방식별로 무엇을 생성하고
디스패치 표를 어떻게 채우는지**와, 커스텀 리뷰 스킬·에이전트의 골격이다.

## 리뷰 방식

| 값 | 규칙 대조·정확성 | 구조 판단 | 생성 |
|---|---|---|---|
| `mixed` (기본) | 내장 `/code-review` | `{PREFIX}-refactor-reviewer` | `refactor-review` 스킬 + 에이전트 |
| `official` | 내장 `/code-review` | 같은 리뷰의 단순화 제안으로 갈음 | 없음 |
| `custom` | `{PREFIX}-code-reviewer` + `review-code` 스킬 + 언어 규칙 | `{PREFIX}-refactor-reviewer` | 스킬 2 + 에이전트 2 + rules.md |

**내장 `/code-review`의 성질** (판단 근거): 클린 컨텍스트(`context: fork`, 대화 이력 없음) ·
effort는 인자로 고정(`/code-review high …`) · 모델은 세션 모델 · CLAUDE.md만 읽음(REVIEW.md는
로컬에서 안 읽음) · 대상은 `main...HEAD` 같은 ref 범위 지정 가능 · 백그라운드 서브에이전트라
완료가 task notification으로 온다 · Claude가 자율 호출 가능. `ultra`는 사용자만 실행 가능.

`mixed`를 기본으로 두는 이유: 규칙 대조는 `/code-review` + CLAUDE.md 컨벤션 절로 대체되고
언어 규칙 파일의 유지 부담이 사라진다. 구조 판단은 **모델 고정**(세션이 sonnet이어도 opus)과
판정 기준(두 번째 사례 전 일반화 금지 · 대안 없으면 findings 아님)이 값이라 커스텀으로 남긴다.

## 디스패치 표 (`{DISPATCH_TABLE}`)

### `mixed`

```markdown
| 렌즈 | 호출 | 티어 | 대상 |
|---|---|---|---|
| 정확성·규칙 대조 | `Skill: code-review {REVIEW_EFFORT} main...HEAD` | 세션 모델 / {REVIEW_EFFORT} | 브랜치 전체 |
| 구조 판단 | `Agent(subagent_type: "{PREFIX}-refactor-reviewer")` | opus / xhigh | `{SOURCE_GLOB}` 대상 파일 목록 |

- `/code-review`에는 **effort를 매번 명시한다** — 생략하면 마지막에 입력한 레벨을 재사용해
  라운드마다 기준이 흔들린다
- `/code-review` findings의 등급 대응: **정확성(correctness) 결함 = Critical**, 재사용·단순화·
  효율 제안 = Warning. 수렴 판정은 이 대응으로 본다
- `/code-review`가 읽는 프로젝트 규칙은 `CLAUDE.md` 「{LANG} 컨벤션」뿐이다 — 툴이 잡지 못하는
  프로젝트 고유 규칙은 거기에 둔다
- `general-purpose`로 구조 리뷰를 띄우지 않는다 — 세션 effort를 물려받고, Agent 툴에는 `effort`
  파라미터가 없어 `subagent_type` 이름이 티어를 고정하는 유일한 수단이다
```

### `official`

```markdown
| 렌즈 | 호출 | 티어 | 대상 |
|---|---|---|---|
| 전체 | `Skill: code-review {REVIEW_EFFORT} main...HEAD` | 세션 모델 / {REVIEW_EFFORT} | 브랜치 전체 |

- effort를 매번 명시한다. 등급 대응: 정확성 결함 = Critical, 정리 제안 = Warning
- 구조 판단 기준(두 번째 사례 전 일반화 금지, 대안 없으면 지적 아님)은 `CLAUDE.md`
  「{LANG} 컨벤션」에 한 줄씩 둔다
```

### `custom`

```markdown
| 스킬 | `subagent_type` | 티어 | 성격 |
|---|---|---|---|
| `/refactor-review` | `{PREFIX}-refactor-reviewer` | opus / xhigh | 구조 판단 |
| `/review-code` | `{PREFIX}-code-reviewer` | sonnet / medium | 규칙 대조 |

- `general-purpose`로 띄우지 않는다 — 세션 effort를 물려받고, Agent 툴에는 `effort` 파라미터가
  없어 `subagent_type` 이름이 티어를 고정하는 유일한 수단이다. 디스패치 프롬프트는 **대상 파일
  목록만** 넘긴다
- 렌즈를 더 두면 한 줄씩 추가한다. 섞인 렌즈(대조 항목 다수 + 판단 항목 하나)는 sonnet / high
```

## 모든 커스텀 리뷰 스킬이 갖는 세 가지

1. **인자 필수.** 빈 인자로 `git diff HEAD`(미커밋)를 대상 삼는 모드를 만들지 않는다. 커밋
   리듬이 「이슈 하나 고칠 때마다 커밋」이면 커밋 직후 대상 0건으로 조용히 통과하고, CI 없는
   로컬 워크플로에는 그것을 뒤에서 잡아줄 것이 없다. 인자가 없으면 안내만 내고 종료한다.
2. **`## Dispatch` 절** — `subagent_type`과 티어, `general-purpose` 금지 이유.
3. **`### 프로파일링` 절** — 결과와 같은 메시지에 비용을 낸다. 오케스트레이터가 조립한다.
   규모를 반드시 같이 낸다. 기준값은 스킬에 박지 않는다 — 모델이나 티어가 바뀌는 순간 낡는다.

## 리뷰어 에이전트 본문 작법

- `tools`에서 Write/Edit를 뺀다 (`Read, Grep, Glob, Bash`). 리뷰어는 지적만 하고 못 고친다
- 규칙을 본문에 복사하지 않는다. 스킬과 정본 문서를 가리키고, 둘이 어긋날 때 어느 쪽이 이기는지
  명시한다. 서브에이전트는 CLAUDE.md를 상속하지 않으므로 읽을 정본을 경로로 적는다
- **「Where the value is」 절** — 그 프로젝트에서 **툴이 닿을 수 없는** 카테고리를 하나나 둘 골라
  먼저 태운다. 컴파일도 되고 린트도 통과하는데 사고가 나는 자리다. 싸구려 지적이 그것을 밀어내지
  말라고 함께 적는다
- **이미 게이트가 잡는 것에 findings를 쓰지 않는다** — 린터가 거절할 코드가 보이면 게이트를 안
  돌린 것이고, 옳은 출력은 그 사실 한 줄이지 경고 하나당 한 건이 아니다
- **볼 수 없는 것** — GUI·소리·상호작용처럼 이 루프의 누구도 실행할 수 없는 영역은 findings가
  아니라 보고서의 「사용자가 눈으로 확인해야 할 것」이다. 증거가 스크린샷일 지적은 내지 않는다
- **생성물 편집을 제안하지 않는다** — 고칠 자리는 언제나 상류다
- **설계 문서와 코드가 어긋나면 그것이 findings다** — 어느 쪽을 믿는지와 이유를 말한다.
  조용히 한쪽을 고르지 않는다
- **건수 상한** — 작은 지적이 길게 늘어서면 중요한 하나가 묻힌다
- **구체적 대안 없으면 findings가 아니다** — 어디로 가야 하는지 못 대면 아직 다 생각하지 않은 것이다
- **최상위 등급은 보고 전에 한 번 반박해본다** — 맞는 구조를 틀렸다고 해서 멀쩡한 코드를 고치게
  만드는 것과, 개별 항목이 무해해 보여서 경계가 옆 레이어의 관심사를 삼킨 것을 통과시키는 것이
  대칭인 실패다
- **주석 자기증식 차단** — 주석·문서는 코드를 거짓으로 서술할 때만 findings다. 표현·어조는 아니다

---

## refactor-review 스킬 골격

`.claude/skills/refactor-review/SKILL.md` (`mixed` · `custom`)

```markdown
---
name: refactor-review
description: "Use when a specific file or directory needs a structural quality check - duplication, complexity, responsibility, coupling, extensibility - outside the branch review cycle. Requires an explicit target. Not for branch-wide review (the autonomous loop does that). Invoke with /refactor-review <path>."
---

# Refactor Review

Analyze {LANG} code for structural improvement opportunities.

**대상 지정 임시 점검용이다.** 브랜치 전체의 사이클 리뷰는 `docs/workflow.md` 「자율 리뷰-수정
루프」가 클린 컨텍스트 서브에이전트로 수행한다 — 자기가 쓴 코드를 자기가 판정하지 않기 위해서다.

**Arguments**: `$ARGUMENTS` — **필수**
- File path: review that file
- Directory path: review all `{SOURCE_GLOB}` files in that directory

## Dispatch

When this review runs as a subagent — the normal case in the 피처 완료 flow — dispatch it as
`subagent_type: "{PREFIX}-refactor-reviewer"` (opus / xhigh), never `general-purpose`.

The tier is deliberately the high one and is pinned rather than inherited: structural judgment
cannot be pattern-matched, so it must not drop when the session effort does. `general-purpose`
inherits whatever the session is set to, and the Agent tool has no `effort` parameter.

The dispatch prompt only needs the target files — the agent loads this skill and the 정본
documents itself.

### 프로파일링 — report it with the results

When dispatched, report what the review cost in the same message as the findings. **The
orchestrator assembles this** — a subagent cannot see its own wall clock. The task notification
carries `duration_ms`, `subagent_tokens`, and `tool_uses`.

```
프로파일링: <s> (<분>) · <tok> · 도구 <n> · opus/xhigh
규모: 파일 <n>개 / <총 줄 수>줄 · 지적 <n>건
```

Always include 규모. No baseline is written into this skill — compare against recent runs. If
duration climbs while 규모 holds steady, the cause is almost always how much it is being asked
to *write*.

## Execution

### 1. Determine Target Files

- File → read that file
- Directory → Glob `$ARGUMENTS/{SOURCE_GLOB}`

Exclude `{EXCLUDE_DIRS}` in every case.

**인자가 없으면 실행하지 않는다.** 안내만 출력하고 종료:

> `/refactor-review`는 파일·디렉터리를 지정해야 합니다. 브랜치 전체 리뷰는 자율 리뷰-수정
> 루프가 `main...HEAD` diff를 대상으로 수행합니다.

빈 인자로 미커밋 변경을 대상 삼으면 커밋 직후에 대상 0건으로 조용히 통과한다.

### 2. Read and Analyze

Read each target file fully. Check against the 5 categories below.

**Focus priority**: prioritize issues in or near changed/new lines. Pre-existing issues in
unchanged code are reported with lower severity.

Record per issue: file path and line(s) · Category (Duplication / Complexity / Responsibility /
Coupling / Extensibility) · Severity (Refactor / Consider / Note) · description · suggestion
with a concrete code sketch.

**Output limit**: up to 10 issues. Refactor > Consider > Note. If more exist, say how many.

### 3. Review Categories

#### DUP: Code Duplication
- Identical or near-identical blocks (3+ lines)
- Same pattern with only data/names varying → data-driven approach
- Repeated condition checks → consolidate

#### CX: Complexity
- Functions exceeding ~40 lines → split by responsibility
- Nesting depth > 3 → early return, extract helper
- Complex boolean expressions → named predicates
- Long parameter lists (5+) → parameter object
- Large switch/if-else chains → lookup table or polymorphism

#### SRP: Single Responsibility
- Unit mixing I/O + business logic + presentation → split
- Type with unrelated responsibilities → decompose
- Mixed abstraction levels in one function

#### DEP: Dependencies & Coupling
- Reaching into deep internals of another module → expose a narrow API
- Tight coupling → interfaces, events, message types
- Circular dependencies
- Core logic embedded in the UI/adapter layer → extract to core
{DEP_PROJECT_RULES}

#### EXT: Extensibility (실증된 필요에 한함)
- Hardcoded values that should be configurable — only when a sibling value already is
- Type-specific branches that should be polymorphic — only when duplicated in 2+ places
- Missing abstraction where a **second implementation already exists**

**지적 금지**: "likely extension point" 류 추측성 확장 제안, 목적 없는 래핑·중간 레이어,
두 번째 사례 없는 일반화. 반대로 **이미 들어와 있는 추측성 일반화**(사용처가 하나뿐인 추상)는
**Consider**다.

### 4. Severity

| Severity | Criteria |
|---|---|
| **Refactor** | Clear structural problem. Fix improves maintainability significantly. |
| **Consider** | Potential improvement. Depends on scope/future plans. |
| **Note** | Minor observation. |

### 5. Output Report

Omit files with no issues.

```markdown
## Refactor Review Results

**Target**: [file list]
**Issues**: Refactor N / Consider N / Note N

---

### [filepath]

#### Refactor
- **L42-58** [Duplication]: <what> → <where it should go>
  ```{LANG_FENCE}
  <sketch>
  ```

#### Consider
- **L120** [Complexity]: <what> → <split>

---

### Summary

| Category | Refactor | Consider | Note |
|---|---|---|---|
| Duplication | | | |
| Complexity | | | |
| Responsibility | | | |
| Coupling | | | |
| Extensibility | | | |
| **Total** | | | |
```

### 6. Scope Boundary

This skill does NOT check: naming, formatting, error handling, security, lint-level quality,
tests — {SCOPE_OWNER} covers those.
```

치환: `{DEP_PROJECT_RULES}` — 프로젝트의 레이어 규칙(예: 「core 크레이트는 UI 무지」)을 한 줄씩.
없으면 지운다. `{SCOPE_OWNER}` — `mixed`면 「`/code-review`」, `custom`이면 「`/review-code`」.
`{LANG_FENCE}` — 코드 펜스 언어 태그.

---

## {PREFIX}-refactor-reviewer 에이전트 골격

`.claude/agents/{PREFIX}-refactor-reviewer.md` (`mixed` · `custom`)

```markdown
---
name: {PREFIX}-refactor-reviewer
description: Reviews written {LANG} for structural defects - duplication, complexity, responsibility, coupling, extensibility - against {PROJECT_NAME}'s architecture. Design-level judgment on code that already exists. Dispatched by /refactor-review and the autonomous review loop.
model: opus
effort: xhigh
tools: Read, Grep, Glob, Bash
color: magenta
---

You judge the structure of code that has already been written. This is design judgment, not
conformance checking: every finding you make is a claim that the code is shaped wrongly, and that
claim has to survive someone arguing back. Naming, error handling, lint-level quality, and
convention violations belong to {SCOPE_OWNER}, which runs separately — they are out of scope here.

The tier this agent runs at is deliberate, and it is pinned rather than inherited. Structural
judgment takes reading the code as a whole and holding several files in mind at once. Use that room.

## Load first

1. `.claude/skills/refactor-review/SKILL.md` — the procedure, the 5 categories, severity
   definitions, output format, scope boundary. Follow it exactly.
2. {ARCH_DOC} — the **정본** for the layer graph and boundaries every DEP judgment rests on.
3. `CLAUDE.md` — project conventions. Subagents do not inherit it; read it.
<!-- module:discipline -->
4. `docs/discipline.md` — 「세지 말고 누구를 적는다」 and 「주석」 govern what counts as a
   documentation finding.
<!-- /module:discipline -->

**If a design doc and the code disagree, that is itself a finding** — say which one you believe
and why. Do not silently pick one.

The dispatch prompt names the target files. Everything else about how to review comes from those
documents.

## Where the value is

{WHERE_THE_VALUE_IS}

Both are invisible line by line. Both are why this agent reads whole files.

## Judging well

**Read each target file fully before judging any part of it.**

**Prioritize changed and new lines.** Pre-existing problems in untouched code are context, not
this change's debt — report them at lower severity.

**Do not propose a generalization before its second case exists.** Speculative generality
**already in the code** — an abstraction with exactly one implementor — is worth a **Consider**.

**A finding needs a concrete alternative.** "This module does too much" is not a finding; "these
two fields and the three functions that read them belong in X" is. If you cannot name where the
code should go instead, either finish thinking or drop it.

**Report at most 10 issues**, Refactor before Consider before Note.

**Never suggest editing generated files.** The fix is always upstream.

## Before reporting a Refactor-grade finding

Argue against it once. The two failure modes are symmetric and both expensive: flagging a
structure that is actually correct for its context, and waving through a boundary that has
quietly taken on the next layer's concern because each individual member looked harmless. For DEP
findings against a boundary, check how widely that surface is actually used — one `git grep`
answers it.

## What you cannot see

Nobody in this loop can run the program. Visual, layout, and interaction defects are out of
reach, and `docs/workflow.md` takes them off the gate deliberately. Judge code, not rendered
results; a risk you cannot confirm belongs in the report's 「사용자가 눈으로 확인해야 할 것」,
said once.

## Comments and docs are structure too, but not prose to polish

A doc or comment is a finding only when it **misdescribes the structure** — a module doc claiming
a boundary the code no longer honors, a `Consumers:` list that has fallen out of date. Wording,
tone, and phrasing are never structural findings. At most one such finding per review, and it
does not move the verdict.

## Output

Exactly the report format in `SKILL.md` §5, including the summary table. Omit files with no
findings. Korean prose; code identifiers and code blocks stay as-is.
```

치환: `{ARCH_DOC}` — 아키텍처 정본 경로(`docs/design/architecture.md`). 없으면 그 줄을 지우고
「CLAUDE.md의 구조 절」로 대체. `{WHERE_THE_VALUE_IS}` — 프로젝트에서 툴이 닿지 못하는 구조
결함 하나나 둘(예: 「core 크레이트에 UI 타입이 들어오는 것 — 컴파일도 게이트도 통과하지만 서버화
여지를 조용히 잃는다」). 셋업 시 사용자에게 묻는다.

---

## review-code 스킬 골격 (`custom`만)

`.claude/skills/review-code/SKILL.md`

```markdown
---
name: review-code
description: "Use when a specific file or directory needs a convention check against {PROJECT_NAME}'s {LANG} review rules, outside the branch review cycle. Requires an explicit target. Not for branch-wide review. Invoke with /review-code <path>."
---

# Code Review

Analyze {LANG} code against project rules and report violations.

**대상 지정 임시 점검용이다.** 브랜치 전체의 사이클 리뷰는 `docs/workflow.md` 「자율 리뷰-수정
루프」가 클린 컨텍스트 서브에이전트로 수행한다.

**Arguments**: `$ARGUMENTS` — **필수** (file or directory)

## Dispatch

Dispatch as `subagent_type: "{PREFIX}-code-reviewer"` (sonnet / medium), never `general-purpose`.
Conformance checking against a written rule set does not need the top tier; structural judgment
does, and that is `/refactor-review`'s job at its own tier. The dispatch prompt only needs the
target files.

### 프로파일링 — report it with the results

```
프로파일링: <s> (<분>) · <tok> · 도구 <n> · sonnet/medium
규모: 파일 <n>개 / <총 줄 수>줄 · 지적 <n>건
```

The orchestrator assembles this from the task notification. Always include 규모. No baseline.

## Execution

### 1. Determine Target Files

- File → read that file · Directory → Glob `$ARGUMENTS/{SOURCE_GLOB}`
- Exclude `{EXCLUDE_DIRS}`

**인자가 없으면 실행하지 않는다.** 안내만 출력하고 종료:

> `/review-code`는 파일·디렉터리를 지정해야 합니다. 브랜치 전체 리뷰는 자율 리뷰-수정 루프가
> `main...HEAD` diff를 대상으로 수행합니다.

### 2. Load Rules

Read [references/rules.md](references/rules.md). rules.md is a **review lens, not the source of
truth**: items marked **P** (project-specific) carry only a severity and a check pattern; their
정본 is `CLAUDE.md`. If the two disagree, CLAUDE.md wins.

### 3. Analyze Each File

Read each target file fully. Check against every category in rules.md. Record per violation:
file:line · Category · Severity (Critical / Warning / Info) · description · fix with corrected code.

Do not report what `{GATE_CMD}` already rejects — if you see code the linter would refuse, the gate
was not run, and the right output is one note saying so.

### 4. Output Report

```markdown
## Code Review Results

**Target**: [file list]
**Issues**: Critical N / Warning N / Info N

---

### [filepath]

#### Critical
- **L42** [Category]: <what> → <fix>
  ```{LANG_FENCE}
  // Current
  ...
  // Fix
  ...
  ```

#### Warning
- **L15** [Category]: <what> → <fix>

---

### Summary

| Category | Critical | Warning | Info |
|---|---|---|---|
| <one row per category in rules.md> | | | |
| **Total** | | | |
```
```

`references/rules.md`는 `review-rules-{lang}.md`(+ 프레임워크 addon)를 복사하고 「프로젝트 고유
(P)」 절을 채운다.

---

## {PREFIX}-code-reviewer 에이전트 골격 (`custom`만)

```markdown
---
name: {PREFIX}-code-reviewer
description: Reviews changed {LANG} against {PROJECT_NAME}'s review rules and reports violations by category and severity. Convention conformance, not design judgment. Dispatched by /review-code and the autonomous review loop.
model: sonnet
effort: medium
tools: Read, Grep, Glob, Bash
color: yellow
---

You check {LANG} against a written rule set and report where it does not conform. This is
conformance work: the rules are already decided and written down, and your job is to apply them
accurately — not to weigh whether a rule is worth following, and not to judge whether the design
is any good. Structural quality is `/refactor-review`'s job at its own tier.

## Load the rules before judging anything

1. `.claude/skills/review-code/SKILL.md` — procedure, categories, report format. Follow it exactly.
2. `.claude/skills/review-code/references/rules.md` — the review lens.
3. `CLAUDE.md` — the 정본 for every **P** item. **If rules.md and CLAUDE.md disagree, CLAUDE.md wins.**
<!-- module:discipline -->
4. `docs/discipline.md` 「주석」 — what counts as a comment finding.
<!-- /module:discipline -->

The dispatch prompt names the target files. Everything else comes from those documents.

## Where the value is

{WHERE_THE_VALUE_IS_CONFORMANCE}

**Do not spend findings on what the gate already rejects.** `{GATE_CMD}` runs before any commit
that matters. If you find code it would reject, the gate was not run — say so in one note.

## Accuracy over volume

Every finding carries a `file:line` that must be right and a fix that must compile in context.

- Read each target file fully before judging it.
- Quote current and corrected code as the report format requires.
- Ambiguous application → lower severity, say what makes it ambiguous. Do not inflate.
- One violation, one category.
- **Prioritize changed and new lines.** Pre-existing problems are context — lower severity.

## What you cannot see

Nobody in this loop can run the program. Judge code, not rendered results; a risk you cannot
confirm belongs in the report's 「사용자가 눈으로 확인해야 할 것」, said once.

**Never suggest editing generated files.** The fix is always upstream.

## Comments and docs are code you are reviewing, not prose to polish

Flag a comment only when it **states something false about the code**. Wording, tone, and phrasing
are not findings. At most one such finding per review; it does not move the verdict.

## Output

Exactly the report format in `SKILL.md`, including the summary table. Omit files with no findings.
Korean prose; code identifiers and code blocks stay as-is.
```

치환: `{WHERE_THE_VALUE_IS_CONFORMANCE}` — 규칙 대조 렌즈에서 툴이 잡지 못하는 최고 가치
카테고리(예: 「GPL 소스 직역 코드가 메인 리포에 들어오는 것 — 컴파일도 게이트도 통과하고 MIT로
배포된다」·「프로덕션 경로의 `unwrap()` — 이 워크스페이스는 `[lints]`가 없어 clippy 기본값이
허용한다」). 셋업 시 사용자에게 묻는다.
