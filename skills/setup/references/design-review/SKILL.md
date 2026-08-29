---
name: design-review
description: "Use when a spec contains code-structure design (new/changed types, modules, interfaces, dependencies) and is not yet committed, or when a design decision is about to shape code structure - before any implementation. Not for specs without code design content, and not for code that already exists (use /refactor-review). Invoke with /design-review [spec-path]."
---

# Design Review

## Overview

Structural review of a code design **before implementation**, by reviewers with a **clean
context**. The context that authored a design is the one context that cannot judge it — it
inherits every rationalization that shaped it.

A review is N rounds: one full round, then one re-review per revision, until the design converges.

**Arguments**: `$ARGUMENTS` is a spec path — review its code-design content. Empty: review the
design decision currently under discussion, written into the dispatch prompt explicitly.

## When to Use

- A spec describes code structure — types to add or change, where logic and state land,
  interfaces, module placement
- A structural decision is being made with no spec behind it (write the decision down for the
  dispatch prompt)
- Unsure whether a spec contains code design? It does. One dispatch is cheaper than one reverted
  feature

**Not for**: planning or content design with no code structure; code that already exists — use
`/refactor-review`.

Review only the code-design portion. Most specs are mostly planning, with code as one part.

## Cost model

- **A review is generation-bound, not exploration-bound.** The stage that opens the fewest files
  is often the slowest. Do not diagnose a slow review by counting file reads.
- **How much a stage is asked to *write* is the lever** — not its model, not its effort. Reach for
  output discipline before touching `model` or `effort`.
- Splitting a stage buys quality, not speed: a judge handed pre-verified facts spends its whole
  budget judging.

The 프로파일링 block in each round's report is how you check these — if a round's numbers
contradict them, trust the round.

## The pipeline

One round is three stages. Stage 2 fans out; stages run in order.

| | Stage 1 — 추출 | Stage 2 — 검증 | Stage 3 — 판정 |
|---|---|---|---|
| Agent | `design-claim-extractor` | `design-fact-verifier` x N | `design-structure-judge` |
| Tier | sonnet / medium | sonnet / low | opus / xhigh |
| Count | 1 | 3-5 (parallel) | 1 |
| Input | the spec | claims file + row range | spec + 결정 목록 + 사실표 + 헌법 |
| Output | claims file (결정 + 주장) | ledger rows (참/거짓/부분) | Blockers + Notes |
| Opens code | no | yes — only what its claims name | rarely, and must state the question |

Stages hand off through files. Pass the path and a range, never copy rows into prompts.

Tiers live in each agent's frontmatter (`model`, `effort`), not in the dispatch call — the Agent
tool has no `effort` parameter, so a dispatch that names `subagent_type` is the only thing that
pins effort. **Never dispatch these stages as `general-purpose`.**

## Execution

### Stage 1 — extract

Dispatch `design-claim-extractor` with `prompts/round-1.md` §1 filled in. It **writes** two tables
to the claims file — 구조적 결정 (with an 있음/없음 column for alternatives-table coverage) and
사실 주장 (numbered `F1..Fn`) — and replies with just the ranges.

This stage is the critical path: it opens almost no files, so its whole cost is generating the
tables. Ask for the work list and nothing more.

Sanity-check the ranges against the spec's size. A long spec that yields a handful of claims means
the extractor skimmed; re-dispatch.

### Stage 2 — verify, in parallel

Dispatch one `design-fact-verifier` per batch **in a single message**, each with the claims file
path and its row range.

**Size batches by weight, not row count**: a 완전성 주장 needs a whole-tree Grep and costs about
three ordinary claims. Count each as 3, aim for roughly equal weight per batch. The stage's wall
clock is its slowest batch.

Assemble the returned rows into the ledger. This is concatenation, not authorship.

### Stage 3 — judge

Dispatch `design-structure-judge` with `prompts/round-1.md` §3 filled in. It must not receive
conversation history, and do not summarize the design's rationale beyond what the spec says —
advocacy contaminates the review.

### 프로파일링 — report it with the verdict

Every round reports what it cost, in the same message as the verdict. **The orchestrator
assembles this** from each task notification's `duration_ms`, `subagent_tokens`, `tool_uses`.

| 단계 | 벽시계 | 토큰 | 도구 | 티어 |
|---|---|---|---|---|
| S1 추출 | <s> | <tok> | <n> | sonnet/medium |
| S2 검증 xN | <s> (합 <s>) | <tok> | <n> | sonnet/low |
| S3 판정 | <s> | <tok> | <n> | opus/xhigh |
| 합계 | <s> (<분>) | <tok> | <n> | |

규모: <스펙 줄 수>줄 · 결정 <n> · 주장 <n>(완전성 <n>) · <라운드와 weight>

For the fan-out stage report both wall clock (slowest batch) and agent-time (sum). When they
converge, the batching has collapsed to serial. **Always include the 규모 line.** No baseline is
written into this document — compare against the last few rounds' blocks in each spec's 설계
검토 기록.

### Handle the result

- **PASS** — proceed to spec commit / implementation
- **INCOMPLETE** — not a pass. Report the unsettled claims; ask the user whether to dispatch a
  follow-up scoped to just those or accept the gap
- **Notes** — fold into the spec at your discretion, no user gate
- **Blockers** — one AskUserQuestion each: finding, evidence, alternative(s), and the option to
  keep the original. **The agent cannot dismiss a Blocker.** Committing or implementing before the
  user decides is a workflow violation
- **Blocker accepted as-is** — record it in the spec's 감수한 대가 table (decision, what
  degrades, why it is accepted, approval) **before** committing

### Re-review rounds

Judge the weight, validate the ledger, then run `prompts/re-review.md`.

- **Stage 1** runs only over sections the revision rewrote, and only when the revision introduced
  new factual claims
- **Stage 2** verifies only claims new to this revision, plus any ledger row marked STALE
- **Stage 3** always runs, carrying the round's weight

**Weight** answers: *how much of the previous round's judgment still holds?* Not a finding count.
Nothing moved → **DELTA**. Some passed decisions lost their ground → **SCOPED**. It reads as a
different design → **FULL**. **Unclear → the higher weight.** The weight you assign is a floor;
a reviewer may raise it, never lower it. Weight changes what stage 3 judges, not the tier.

**No round at all** when the last verdict was PASS, or when every finding was resolved by a fact
correction that changed no structure.

**Convergence**: weight should fall across rounds and findings should get shallower. When a round's
weight fails to fall below the last, or its findings cut as deep, stop dispatching and put the
non-convergence to the user as a finding in its own right.

### Record

Append a 설계 검토 entry to the spec: per round, its date, weight, verdict, how each Blocker was
resolved, and **the round's 프로파일링 numbers — total wall clock, total tokens, and the 규모 line**.
One line per round. Then delete the ledger.

## Fact Ledger

Code facts verified by each round, carried to the next. **Between rounds the code does not
change — only the spec does**, so a verified fact stays true and no later round may re-derive it.

- **Path**: `docs/specs/.review-cache/<spec-basename>.facts.md` — git-ignored, append-only across
  the review
- **Assembled by** the orchestrator from stage 2 output, verbatim

**Two shapes, by verdict.** A 거짓 or 부분 row carries its full reasoning. A 참 row is one line —
it exists only to stop the next round reopening that file.

```markdown
# Fact ledger — <spec basename>
Base commit: <git rev-parse HEAD>
Rounds: R1 <YYYY-MM-DD> (Full)

## 확인된 주장 (참)

`F7 §2.2 <claim> · path/file.rs:483-490 · R1`

## 거짓 · 부분

| # | 주장 | 근거 | 판정 | 라운드 |
|---|------|------|------|--------|

## Files read
- `path/file.rs` — F1, F3

## Open questions
```

Every claim appears in exactly one of the first two sections. Write the ledger even when the
verdict is PASS.

**Validate before every re-review dispatch:**

1. `git rev-parse HEAD` matches the ledger's `Base commit` → whole ledger valid
2. Differs → `git diff --name-only <base> HEAD -- {SOURCE_DIRS}`; mark rows whose 근거 file appears
   there **STALE**
3. Missing → dispatch saying so; the round verifies only what its own scope needs

## Common Mistakes

| Mistake | Why it's wrong |
|---|---|
| Dispatching a stage as `general-purpose` | Its tier comes from the agent definition; `general-purpose` inherits session effort |
| Running the three stages as one agent | The stages need different tiers, and stage 2's whole value is fanning out |
| Copying claim rows into each verifier's prompt | Costs orchestration and context, growing with claim count. Pass the file path and a range |
| Letting the extractor mine the 설계 검토 기록 section | Prior-round prose becomes claims no verifier can settle |
| Accepting a 확인 대상 like "관련 소스" or a ticket ID | The verifier runs literal and cheap; it needs a file path or a symbol |
| Letting the judge re-verify a ledger row | The row is authoritative |
| Reading INCOMPLETE as PASS | The reviewer is telling you it did not finish looking |
| Setting a low weight because the last round went smoothly | Weight comes from what the revision did |
| Handing a reviewer conversation history or your rationale | The clean context is the entire value |
| Deciding a Blocker yourself because the fix is obvious | Blockers are the user's call, always |
| Writing 참 claims as full prose ledger rows | Budget spent on text no later round reads |
| Leaving the ledger in place after the review closes | A future review reads it as current |
| Running another round on a design that is not converging | Rounds cannot fix a spec that is too large or too unsettled |
