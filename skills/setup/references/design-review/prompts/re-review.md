# Re-review dispatch templates

The code has not changed since the last round — only the spec has. Every ledger row still holds,
so stage 2 has almost nothing to do and stage 1 often nothing at all.

Stage tiers are unchanged from round 1. Weight changes what stage 3 judges, never how hard it thinks.

Validate the ledger first (SKILL.md "Fact Ledger"), then run the stages that have work.

---

## 1. Extract — `design-claim-extractor` — **only if the revision made new factual claims**

Skip entirely when the revision only moved structure around or resolved findings without asserting
anything new about the code.

```
Design under review: <spec absolute path>
Revised sections: <sections the revision rewrote>

This is a revision of a spec already reviewed. Extract from the revised sections ONLY:
- structural decisions introduced or changed by this revision
- factual claims that are NEW to this revision

Already-verified claims are in docs/specs/.review-cache/<basename>.facts.md — a claim already listed there is not new; skip it. Number new claims continuing from <last F number>.
```

---

## 2. Verify — `design-fact-verifier` — **only new claims and STALE rows**

One batch is usually enough. If there are no new claims and no STALE rows, skip this stage.

```
Repo root: {PROJECT_PATH}
Spec (context only — do not read end to end): <spec absolute path>

Settle these claims against the code:

| # | Claim | Spec location | Verification target | Completeness claim |
|---|------|-----------|-----------|-------------|
<new claims from stage 1, plus any ledger rows marked STALE>

Return one ledger row per claim, in this order, plus Files opened and Incidental observations.
```

Append the returned rows to the ledger under this round's number. Leave existing rows untouched.

---

## 3. Judge — `design-structure-judge` — **always runs**

```
You are re-reviewing a code design after its author revised it in response to an earlier review round. The code has NOT changed since that round — only the spec has.

Spec:               <path>
Code design is in:  <sections>
Prior findings:     <the Design Review Log: each finding and its recorded resolution>
Rewritten:          <sections the revision touched>
Design principles:  docs/design-principles.md
Fact ledger:        docs/specs/.review-cache/<basename>.facts.md
                    <"all rows valid" | "rows marked STALE are invalid, the rest valid" | "no ledger">
Weight:             <DELTA | SCOPED | FULL>

## Fact table
<full ledger content inline, new rows included>

## Decision list
<updated decision table if stage 1 ran, else the prior round's>

## What this round judges

Every weight judges these three:

1. Does each prior finding's stated resolution actually appear in the spec, and does it resolve the finding? A finding "resolved" by a sentence that restates the problem is not resolved.
2. Did any resolution introduce a new structural problem, or contradict a part of the spec it did not touch?
3. Are the claims new to this revision true? Rows carrying this round's number are the new ones.

Then, by weight:

**DELTA** — nothing further. Stop after the three questions. If the revision holds, say PASS and stop.

**SCOPED** — run the full structural pass over the rewritten sections, plus any decision an earlier round passed whose *premise* this revision changed. Name the moved premise when you reopen one.

**FULL** — judge the whole design as if seeing it fresh. Claim verification stays fact-table-first.

The weight above is a floor. You may raise it — say why — and may never lower it.

## Report

1. **Verdict** — `PASS` / `N Blockers` / `INCOMPLETE`
2. **Findings** — each with evidence. Every [Blocker] carries at least one concrete alternative
3. **Convergence** — one line: did this round's findings come out shallower than the previous round's? If they cut as deep, say so plainly
4. **Reads report** — what you opened past the fact table. `none` is the expected answer

Prose in the user's language; code identifiers stay as-is.
```
