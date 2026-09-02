---
name: doc-review
description: "Use when an instruction document - CLAUDE.md, docs/workflow.md, docs/discipline.md, docs/authoring-policy.md, docs/design-principles.md, .claude/skills/*/SKILL.md, .claude/agents/*.md - was added or revised and is not yet committed, especially right after rewriting one section, or when a section reads ambiguous and needs a clean-context reading. Not for specs with code design (/design-review) or source code (/review-code, /refactor-review). Invoke with /doc-review <md-path> [sections | section \"<title>\"]."
---

# Doc Review

Reviews an instruction document whose unit is the section, in two layers.

- **Section-standalone layer** — one reviewer per `##` section. The reviewer gets **that section's
  text and one line naming the kind of document**, nothing else. No other section, no project
  context, no account of how it was written.
- **Whole-document coherence layer** — one reviewer reads the whole document plus the authoring
  policy (`docs/authoring-policy.md`).

The two layers take different input, so they produce different kinds of defect. Which layers run
this time is set by the mode.

**The deliverable stops at the defect list.** Never edit the document under review — what is left
behind is the report and the record it is copied into, and what gets fixed is decided by the user
who read the report (the start gate).

The context that wrote a document cannot judge it. Reviewers get no conversation history, no
statement of purpose, no self-justification, and the synthesis is done by a separate subagent that
receives only the review-results file, not by this session.

**Arguments** `$ARGUMENTS`: the markdown path (required) plus a mode (`sections`, or `section
"<title>"`; omitted means the full run). With no path, do not run — print the usage and stop.

## Modes

| Mode | Argument | What runs |
|---|---|---|
| full (default) | `/doc-review <path>` | every section + coherence + synthesis |
| sections only | `/doc-review <path> sections` | every section + synthesis |
| single section | `/doc-review <path> section "<title>"` | that one section |

The mode is set by the invocation argument — whatever you just edited, never drop to a mode the
argument did not name. The title argument accepts both a `##` and a `###` section, and takes the
title string without the `#` marks.

**When frontmatter was edited, call the full mode** — `description` is read by the coherence layer,
which reads the document as a whole rather than a section, so in the two modes without it nobody
reads that line.

## Execution

### 1. Split into sections

Read the document and cut it at `##`.

- The body before the first `##` (the document's opening) is one unit too; its title is the
  document title. Exclude the `#` title line and the frontmatter — a coherence reviewer opens the
  file and reads the frontmatter itself.
- In the full and sections-only modes, a `###` stays inside its parent `##` — a subsection is meant
  to be read under its parent, so splitting it out produces nothing but reference dependencies.
- Single-section mode: for a `###` title, from that heading to the next heading at the same level
  or above.
- Settle one line naming the kind of document, from the "Type:" marker on the document's first
  line or from its path. For example: "the design principles document of a Rust CLI project (design
  quality perspective)". Give no more than that.
- **In the full and sections-only modes, when the split yields more than 12 units**, say how many
  reviewers that dispatches and take a yes-or-no through AskUserQuestion. Never make the user pick
  how many to run — going ahead runs them all, and cutting it down means calling again in
  single-section mode. Single-section mode dispatches one reviewer and skips this check.

### 2. Dispatch — in one message

Using the templates in `prompts/dispatch.md`, dispatch one `doc-section-reader` per section, all of
them, plus two `doc-coherence-reviewer` **in one message**. Sections-only mode dispatches no
coherence reviewer; single-section mode dispatches one `doc-section-reader` and nothing else.

**The two layers reach the document by different routes.** `doc-section-reader` cannot open files,
so inlining the section text in the prompt is the only route — write nothing in it beyond the
section body, no other part of the document, no purpose, no history. `doc-coherence-reviewer`
receives paths and opens the files itself, frontmatter included. When the document under review
hands its detail off to another file, that path goes to it as well; what is and is not passed is
set by `A Document With Reference Files`.

Model and effort are pinned by the agent frontmatter. **Never dispatch as `general-purpose`** — it
inherits the session effort. The coherence layer is the one exception to that pinning: **dispatch
the same agent twice, overriding `model` on the second one.** When no second model is available,
dispatch one and say so in the report.

### 3. Synthesis

Collect the reviewers' output **verbatim** into `docs/reports/doc-review/<basename>.reviews.md` —
under `## Sections`, a `###` per section title; under `## Whole Document`, `### Coherence A`
(fable) and `### Coherence B` (the second model). Never summarize or select.

Dispatch `doc-review-synthesizer` with that file path, the document path, and the repo root — do
not pass it the mode. Synthesis decides what to emit from whether the review-results file has a
`## Whole Document`.

Single-section mode skips synthesis — report the one reviewer's output as it is.

### 4. Report

Emit the synthesis output (in single-section mode, the reviewer output) and the cost block below in
one message. **Write the same content into the run record** — it is the only thing the next run has
to compare against, and the review-results file is disposable.

- With the `board` module, the record is a note appended to the issue card `docs/issues/<id>.md`.
- Without it, the record is `docs/reports/doc-review/<basename>.report.md`.

**On a run where synthesis ran, never list the reviewers' output in the report** — what goes in is
only the table and lists synthesis newly assembled, and a table a reviewer produced is not carried
over either. Single-section mode has no synthesis, so the reviewer output is the report.

Pin these at the head of the report:

- **The path of the document under review.** When several documents are run under one record,
  reports without this line cannot be told apart.
- **Sections-only mode** — "coherence between sections was not examined".
- **Single-section mode** — the above plus the title of the section read. That line is the only
  thing revealing that nobody read the other sections.
- **A run that gave the coherence layer `Read alongside`** — those paths.
- **When there is no earlier run to compare against** — "no earlier run on record".

A subagent cannot see its own wall clock or tokens, so **the orchestrator assembles this.** Record
each stage's `duration_ms`, `subagent_tokens`, and `tool_uses` from the task notifications.

| Stage | Wall clock | Tokens | Tools |
|---|---|---|---|
| sections xN | <longest> (sum <s>) | <sum of N> | <sum of N> |
| coherence x2 | <longest> (sum <s>) | <sum of 2> | <sum of 2> |
| synthesis | <s> | <tok> | <n> |
| total | <s> (<min>) | <tok> | <n> |

Scale: <document line count> lines · <n> sections · <mode>

Drop the row for a stage that did not run. Total wall clock is the longer of the section and
coherence stages plus synthesis — those two run together and only synthesis follows. The section
and coherence rows carry both the longest and the sum — the gap between them is the only evidence
the parallelism actually happened. The scale line always goes in. Never pin a baseline into this
document — the comparison is against the earlier run in the record.

## A Document With Reference Files

When the document under review hands its detail off to another file (`references/`, `prompts/`),
**put that path in the coherence prompt's `Read alongside`.** A coherence reviewer that has not
read the file it was handed off to reports that reference as pointing at nothing, and the rules
that live only in the other file as a missing section.

- Never put it in the prompt of the layer that receives only a section body — that layer cannot
  open files.
- **A file read alongside is reference material, not a document under review.** Its own sections'
  standalone quality is not examined this run — to review it, call `/doc-review` again with its path.

## Re-runs

A run over a document that has been run before **compares against the earlier run's record.** The
comparison is done by the orchestrator while assembling the report — synthesis receives the
review-results file and the document, and knows nothing of the earlier run.

1. Read the earlier `/doc-review` record for the same document. With none, report without comparing.
2. **Compare by the sentence the earlier run pointed at and the sentence that replaced it**, never
   by classification axis label — the same defect draws a different axis depending on whether the
   quotation spanned one sentence or two.
3. When the same place is caught again, split it two ways.
   - When a reviewer **quotes the sentence newly written this time** and names that sentence's
     misapplication path, record that place in the report as **a place to rewrite** — the fix added
     description without giving a discriminator.
   - When **the same sentence is caught on the same misapplication path as the earlier run**,
     suspect the synthesis rules rather than the document, and say so in the report.
