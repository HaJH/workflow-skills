# Round 1 dispatch templates

Three stages, in order. Fill the placeholders and pass each block as that subagent's **entire**
prompt — the agent definition carries how to work, so these carry only what to work on.

`subagent_type` is mandatory on every dispatch. It is the only thing that pins model and effort.

**Stages hand off through files, not through your context.** Pass paths and ranges. Put working
files in the session scratchpad, not in the repo.

---

## 1. Extract — `design-claim-extractor`

```
Design under review: <spec absolute path>
Output file: <scratchpad>/claims.md

Code-design sections (extract 구조적 결정 from these): <section names>
Context sections (사실 주장 only, no 결정): <scope/background sections>
Review-record section (extract nothing from this): <the 설계 검토 기록 section, if any>

Extract per your instructions and write both tables to the output file.

The spec's alternatives table is at <section>. Use it for the 대안표 행 있음 column.
```

Name the review-record section explicitly whenever one exists. With no spec document, replace the
first line with the decision text verbatim and drop the section lines.

---

## 2. Verify — `design-fact-verifier`, one per batch, all dispatched in a single message

Size batches by weight: a 완전성 주장 counts as 3. Aim for equal weight per batch.

```
Repo root: {PROJECT_PATH}
Claims file: <scratchpad>/claims.md
Your rows: F<a>-F<b>
Spec (context only — do not read end to end): <spec absolute path>

Settle your rows against the code. Return one ledger row per claim, in order, plus 연 파일 and 부수 관찰.
```

Ranges must be contiguous and must together cover every claim. Check the union before dispatching.

---

## 3. Judge — `design-structure-judge`

Assemble the verifier rows into the ledger first (SKILL.md 「Fact Ledger」), then:

```
Design under review: <spec absolute path>
Code design is in: <sections>. <Other sections> are scope and evidence — read for context. <Review-record section> is the prior review record.

설계 헌법: docs/design-constitution.md
팩트 원장: <ledger path>

Read the ledger first. It is authoritative: <n> claims were settled against the code by a prior stage. Do not reopen a file to re-confirm a ledger row.

## 결정 목록
<stage 1's decision table, verbatim, including the 대안표 행 있음 column>

## 사실표 — 거짓 · 부분 (참 <n>건은 원장 파일의 한 줄 인덱스 참조)
<only the 거짓 and 부분 rows>

## 설정되지 않은 주장
<numbers, and one line each on why — from the verifiers' 부수 관찰>
```

Inline the 결정 목록 and the 거짓·부분 rows. The 참 index stays in the ledger file.

Do not add a summary of what the design is trying to achieve or why the author chose an approach.
The spec speaks for itself; everything else is advocacy.
