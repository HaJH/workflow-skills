# Autonomous Review-Fix Loop (module: review-loop)

The loop's procedure and convergence check live in `workflow-md.md`. This document covers **what
each review mode generates and how to fill the dispatch table**, plus the skeletons for the
custom review skills and agents.

## Review Modes

| Value | Rule conformance and correctness | Structural judgment | Generates |
|---|---|---|---|
| `mixed` (default) | built-in `/code-review` | `{PREFIX}-refactor-reviewer` | `refactor-review` skill + agent |
| `official` | built-in `/code-review` | covered by the same review's simplification suggestions | none |
| `custom` | `{PREFIX}-code-reviewer` + `review-code` skill + language rules | `{PREFIX}-refactor-reviewer` | 2 skills + 2 agents + rules.md |

**Properties of the built-in `/code-review`** (the basis for the choice): clean context
(`context: fork`, no conversation history) · effort pinned as an argument (`/code-review high …`)
· model is the session model · reads only CLAUDE.md (REVIEW.md is not read locally) · the target
can be given as a ref range such as `main...HEAD` · it is a background subagent, so completion
arrives as a task notification · Claude can invoke it autonomously. `ultra` can be run by the
user only.

Why `mixed` is the default: rule conformance is covered by `/code-review` plus the CLAUDE.md
conventions section, and the maintenance burden of a language rules file disappears. Structural
judgment stays custom because the value is in the **pinned model** (opus even when the session is
sonnet) and in the judgment criteria (no generalization before the second case · no finding
without an alternative).

## Dispatch Table (`{DISPATCH_TABLE}`)

### `mixed`

```markdown
| Lens | Call | Tier | Target |
|---|---|---|---|
| Correctness and rule conformance | `Skill: code-review {REVIEW_EFFORT} main...HEAD` | session model / {REVIEW_EFFORT} | the whole branch |
| Structural judgment | `Agent(subagent_type: "{PREFIX}-refactor-reviewer")` | opus / xhigh | target file list matching `{SOURCE_GLOB}` |

- **State the effort every time** for `/code-review` — omit it and it reuses the level typed last,
  so the bar wobbles from round to round
- Grade mapping for `/code-review` findings: **a correctness defect = Critical**, a reuse,
  simplification, or efficiency suggestion = Warning. The convergence check reads this mapping
- The only project rules `/code-review` reads are `CLAUDE.md` "{LANG} Conventions" — put the
  project-specific rules a tool cannot catch there
- Never launch the structural review as `general-purpose` — it inherits the session effort, and
  because the Agent tool has no `effort` parameter, the `subagent_type` name is the only way to
  pin the tier
```

### `official`

```markdown
| Lens | Call | Tier | Target |
|---|---|---|---|
| Everything | `Skill: code-review {REVIEW_EFFORT} main...HEAD` | session model / {REVIEW_EFFORT} | the whole branch |

- State the effort every time. Grade mapping: a correctness defect = Critical, a cleanup
  suggestion = Warning
- Put the structural judgment criteria (no generalization before the second case, no finding
  without an alternative) in `CLAUDE.md` "{LANG} Conventions", one line each
```

### `custom`

```markdown
| Skill | `subagent_type` | Tier | Character |
|---|---|---|---|
| `/refactor-review` | `{PREFIX}-refactor-reviewer` | opus / xhigh | structural judgment |
| `/review-code` | `{PREFIX}-code-reviewer` | sonnet / medium | rule conformance |

- Never launch as `general-purpose` — it inherits the session effort, and because the Agent tool
  has no `effort` parameter, the `subagent_type` name is the only way to pin the tier. The
  dispatch prompt passes **the target file list and nothing else**
- Add one row per additional lens. A mixed lens (many conformance items plus one judgment item)
  is sonnet / high
```

## Three Things Every Custom Review Skill Has

1. **The argument is required.** Never build a mode where an empty argument takes
   `git diff HEAD` (uncommitted) as the target. When the commit rhythm is "commit each time you
   fix one issue", it passes quietly with zero targets right after a commit, and a local workflow
   with no CI has nothing behind it to catch that. With no argument, print the guidance and stop.
2. **A `## Dispatch` section** — the `subagent_type`, the tier, and why `general-purpose` is
   banned.
3. **A `### Profiling` section** — report the cost in the same message as the results. The
   orchestrator assembles it. Always include the scale. Never pin a baseline value into the skill
   — it goes stale the moment the model or the tier changes.

## Writing the Reviewer Agent Body

- Remove Write and Edit from `tools` (`Read, Grep, Glob, Bash`). A reviewer only reports; it
  cannot fix
- Do not copy rules into the body. Point at the skill and the canonical documents, and state
  which one wins when the two disagree. A subagent does not inherit CLAUDE.md, so write the paths
  of the canonical documents to read
- **A "Where the value is" section** — pick the one or two categories in that project that
  **tools cannot reach** and run them first. They are the places that compile and lint clean and
  still cause incidents. Write alongside them that cheap findings must not crowd them out
- **Never spend a finding on what the gate already catches** — code the linter would refuse means
  the gate was not run, and the right output is one line saying so, not one finding per warning
- **What you cannot see** — areas nobody in this loop can run, such as GUI, sound, and
  interaction, go not into findings but into the report's "For the User to Check by Eye". Never
  raise a finding whose evidence would be a screenshot
- **Never propose editing generated files** — the place to fix is always upstream
- **A design document out of step with the code is itself a finding** — say which one you believe
  and why. Do not silently pick one
- **A cap on the count** — small findings in a long line bury the one that matters
- **No finding without a concrete alternative** — if you cannot say where it should go, you have
  not finished thinking
- **Argue against a top-grade finding once before reporting it** — calling a correct structure
  wrong and making someone fix healthy code, and waving through a boundary that swallowed the
  next layer's concern because each item looked harmless, are symmetric failures
- **Block comment self-propagation** — a comment or document is a finding only when it describes
  the code falsely. Wording and tone are not

---

## refactor-review Skill Skeleton

`.claude/skills/refactor-review/SKILL.md` (`mixed` · `custom`)

```markdown
---
name: refactor-review
description: "Use when a specific file or directory needs a structural quality check - duplication, complexity, responsibility, coupling, extensibility - outside the branch review cycle. Requires an explicit target. Not for branch-wide review (the autonomous loop does that). Invoke with /refactor-review <path>."
---

# Refactor Review

Analyze {LANG} code for structural improvement opportunities.

**This is for a targeted ad-hoc check.** The whole-branch cycle review is carried out by
`docs/workflow.md` "Autonomous Review-Fix Loop" through clean-context subagents — so that nobody
judges the code they wrote themselves.

**Arguments**: `$ARGUMENTS` — **required**
- File path: review that file
- Directory path: review all `{SOURCE_GLOB}` files in that directory

## Dispatch

When this review runs as a subagent — the normal case in the feature completion flow — dispatch
it as `subagent_type: "{PREFIX}-refactor-reviewer"` (opus / xhigh), never `general-purpose`.

The tier is deliberately the high one and is pinned rather than inherited: structural judgment
cannot be pattern-matched, so it must not drop when the session effort does. `general-purpose`
inherits whatever the session is set to, and the Agent tool has no `effort` parameter.

The dispatch prompt only needs the target files — the agent loads this skill and the canonical
documents itself.

### Profiling — report it with the results

When dispatched, report what the review cost in the same message as the findings. **The
orchestrator assembles this** — a subagent cannot see its own wall clock. The task notification
carries `duration_ms`, `subagent_tokens`, and `tool_uses`.

```
Profiling: <s> (<min>) · <tok> · tools <n> · opus/xhigh
Scale: <n> files / <total lines> lines · <n> findings
```

Always include the scale. No baseline is written into this skill — compare against recent runs.
If duration climbs while the scale holds steady, the cause is almost always how much it is being
asked to *write*.

## Execution

### 1. Determine Target Files

- File → read that file
- Directory → Glob `$ARGUMENTS/{SOURCE_GLOB}`

Exclude `{EXCLUDE_DIRS}` in every case.

**With no argument, do not run.** Print the guidance and stop:

> `/refactor-review` needs a file or a directory. The whole-branch review is carried out by the
> autonomous review-fix loop over the `main...HEAD` diff.

Taking uncommitted changes as the target on an empty argument passes quietly with zero targets
right after a commit.

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

#### EXT: Extensibility (only where the need is demonstrated)
- Hardcoded values that should be configurable — only when a sibling value already is
- Type-specific branches that should be polymorphic — only when duplicated in 2+ places
- Missing abstraction where a **second implementation already exists**

**Never report**: speculative extension suggestions of the "likely extension point" kind,
purposeless wrapping or intermediate layers, generalization with no second case. Conversely,
**speculative generality already in the code** (an abstraction with a single use site) is a
**Consider**.

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

Substitution: `{DEP_PROJECT_RULES}` — the project's layer rules (for example, "the core crate is
ignorant of the UI"), one line each. Delete it if there are none. `{SCOPE_OWNER}` — for `mixed`,
"`/code-review`"; for `custom`, "`/review-code`". `{LANG_FENCE}` — the code fence language tag.

---

## {PREFIX}-refactor-reviewer Agent Skeleton

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
2. {ARCH_DOC} — the **canon** for the layer graph and boundaries every DEP judgment rests on.
3. `CLAUDE.md` — project conventions. Subagents do not inherit it; read it.
<!-- module:discipline -->
4. `docs/discipline.md` — "Name Them, Do Not Count Them" and "Comments" govern what counts as a
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
results; a risk you cannot confirm belongs in the report's "For the User to Check by Eye", said
once.

## Comments and docs are structure too, but not prose to polish

A doc or comment is a finding only when it **misdescribes the structure** — a module doc claiming
a boundary the code no longer honors, a `Consumers:` list that has fallen out of date. Wording,
tone, and phrasing are never structural findings. At most one such finding per review, and it
does not move the verdict.

## Output

Exactly the report format in `SKILL.md` §5, including the summary table. Omit files with no
findings. Prose in the user's language; code identifiers and code blocks stay as-is.
```

Substitution: `{ARCH_DOC}` — the path of the architecture canon (`docs/design/architecture.md`).
If there is none, delete that line and replace it with "the structure section of CLAUDE.md".
`{WHERE_THE_VALUE_IS}` — the one or two structural defects in the project that tools cannot reach
(for example, "a UI type entering the core crate — it compiles and passes the gate while quietly
losing the room to move to a server"). Ask the user at setup.

---

## review-code Skill Skeleton (`custom` only)

`.claude/skills/review-code/SKILL.md`

```markdown
---
name: review-code
description: "Use when a specific file or directory needs a convention check against {PROJECT_NAME}'s {LANG} review rules, outside the branch review cycle. Requires an explicit target. Not for branch-wide review. Invoke with /review-code <path>."
---

# Code Review

Analyze {LANG} code against project rules and report violations.

**This is for a targeted ad-hoc check.** The whole-branch cycle review is carried out by
`docs/workflow.md` "Autonomous Review-Fix Loop" through clean-context subagents.

**Arguments**: `$ARGUMENTS` — **required** (file or directory)

## Dispatch

Dispatch as `subagent_type: "{PREFIX}-code-reviewer"` (sonnet / medium), never `general-purpose`.
Conformance checking against a written rule set does not need the top tier; structural judgment
does, and that is `/refactor-review`'s job at its own tier. The dispatch prompt only needs the
target files.

### Profiling — report it with the results

```
Profiling: <s> (<min>) · <tok> · tools <n> · sonnet/medium
Scale: <n> files / <total lines> lines · <n> findings
```

The orchestrator assembles this from the task notification. Always include the scale. No baseline.

## Execution

### 1. Determine Target Files

- File → read that file · Directory → Glob `$ARGUMENTS/{SOURCE_GLOB}`
- Exclude `{EXCLUDE_DIRS}`

**With no argument, do not run.** Print the guidance and stop:

> `/review-code` needs a file or a directory. The whole-branch review is carried out by the
> autonomous review-fix loop over the `main...HEAD` diff.

### 2. Load Rules

Read [references/rules.md](references/rules.md). rules.md is a **review lens, not the source of
truth**: items marked **P** (project-specific) carry only a severity and a check pattern; their
canon is `CLAUDE.md`. If the two disagree, CLAUDE.md wins.

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

`references/rules.md` is a copy of `review-rules-{lang}.md` (+ any framework addon) with the
"P: Project-Specific" section filled in.

---

## {PREFIX}-code-reviewer Agent Skeleton (`custom` only)

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
3. `CLAUDE.md` — the canon for every **P** item. **If rules.md and CLAUDE.md disagree, CLAUDE.md wins.**
<!-- module:discipline -->
4. `docs/discipline.md` "Comments" — what counts as a comment finding.
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
confirm belongs in the report's "For the User to Check by Eye", said once.

**Never suggest editing generated files.** The fix is always upstream.

## Comments and docs are code you are reviewing, not prose to polish

Flag a comment only when it **states something false about the code**. Wording, tone, and phrasing
are not findings. At most one such finding per review; it does not move the verdict.

## Output

Exactly the report format in `SKILL.md`, including the summary table. Omit files with no findings.
Prose in the user's language; code identifiers and code blocks stay as-is.
```

Substitution: `{WHERE_THE_VALUE_IS_CONFORMANCE}` — the highest-value category in the
rule-conformance lens that tools cannot catch (for example, "code translated line by line from a
GPL source entering the main repo — it compiles, passes the gate, and ships under MIT", or "an
`unwrap()` on a production path — this workspace has no `[lints]`, so the clippy default allows
it"). Ask the user at setup.
