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

Code-design sections (extract structural decisions from these): <section names>
Context sections (factual claims only, no decisions): <scope/background sections>
Review-record section (extract nothing from this): <the Design Review Log section, if any>

Extract per your instructions and write both tables to the output file.

The spec's alternatives table is at <section>. Use it for the "Alternatives row" column.
```

Name the review-record section explicitly whenever one exists. With no spec document, replace the
first line with the decision text verbatim and drop the section lines.

---

## 2. Verify — `design-fact-verifier`, one per batch, all dispatched in a single message

Size batches by weight: a completeness claim counts as 3. Aim for equal weight per batch.

```
Repo root: {PROJECT_PATH}
Claims file: <scratchpad>/claims.md
Your rows: F<a>-F<b>
Spec (context only — do not read end to end): <spec absolute path>

Settle your rows against the code. Return one ledger row per claim, in order, plus Files opened and Incidental observations.
```

Ranges must be contiguous and must together cover every claim. Check the union before dispatching.

---

## 3. Judge — `design-structure-judge`

Assemble the verifier rows into the ledger first (SKILL.md "Fact Ledger"), then:

```
Design under review: <spec absolute path>
Code design is in: <sections>. <Other sections> are scope and evidence — read for context. <Review-record section> is the prior review record.

Design principles: docs/design-principles.md
Fact ledger:       <ledger path>

Read the ledger first. It is authoritative: <n> claims were settled against the code by a prior stage. Do not reopen a file to re-confirm a ledger row.

## Decision list
<stage 1's decision table, verbatim, including the "Alternatives row" column>

## Fact table — FALSE · PARTIAL (for the <n> TRUE claims, see the one-line index in the ledger file)
<only the FALSE and PARTIAL rows>

## Unsettled claims
<numbers, and one line each on why — from the verifiers' Incidental observations>
```

Inline the decision list and the FALSE/PARTIAL rows. The TRUE index stays in the ledger file.

Do not add a summary of what the design is trying to achieve or why the author chose an approach.
The spec speaks for itself; everything else is advocacy.
