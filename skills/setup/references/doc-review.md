# Doc Review (module: doc-review)

Reviews an instruction document in a clean context, in two layers — section-standalone and
whole-document coherence — and merges the results in a separate synthesis agent. Language-agnostic:
the target is prose, not code. Files generated:

| Target | Source | Substitution |
|---|---|---|
| `.claude/skills/doc-review/SKILL.md` | `doc-review/SKILL.md` | none |
| `.claude/skills/doc-review/prompts/dispatch.md` | `doc-review/prompts/dispatch.md` | `{PROJECT_PATH}` |
| `.claude/agents/doc-section-reader.md` | `doc-review/agents/doc-section-reader.md` | none |
| `.claude/agents/doc-coherence-reviewer.md` | `doc-review/agents/doc-coherence-reviewer.md` | none |
| `.claude/agents/doc-review-synthesizer.md` | `doc-review/agents/doc-review-synthesizer.md` | none |
| `docs/authoring-policy.md` | `authoring-policy.md` | the policy as its own document |
| `docs/reports/doc-review/` | empty directory | — |

**With this module on, the authoring policy becomes its own document.** `{AUTHORING_POLICY}` in
`workflow-md.md` is filled with one pointer line (`→ docs/authoring-policy.md`) instead of the
inlined sections, and the coherence reviewer is handed that path. Inlined into `docs/workflow.md`
the reviewer would have to read the whole workflow document to reach the policy, and the section
titles the policy is cited by would be titles inside another document.

## What to Confirm at Setup

- **A second model for the coherence layer.** That layer dispatches the same agent twice, once
  overriding `model`, because one document read twice by two models surfaces different section
  boundaries. Settle which second model this project uses; if there is none available, the skill
  dispatches one reviewer and says so in the report.
- **Where the run record lives.** With the `board` module it is a note on the issue card; without
  it, `docs/reports/doc-review/<basename>.report.md`. A re-run compares against that record, so a
  project that keeps no record loses the re-run comparison — say so if the user turns the board off.

## Maintenance Rules

- **The section layer must never gain the ability to open files.** Its `tools` holds `Glob` alone
  because a subagent with zero tools is refused at spawn — the moment it can read the document,
  reading a section cut off from its context stops being what is measured.
- Refer to a classification axis by the name in the agent's own format block. Never number the
  axes — numbered, the report starts citing "axis 3 violated" and the severity ordering gets read
  as a grade.
- Emit the cost block every run. Never pin a baseline value into the skill.
- The skill never edits the document it reviews. If you extend it, keep that boundary — what gets
  fixed is decided by the user who read the report.
