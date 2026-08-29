# Instruction Authoring Policy

Rules for **adding, editing, and deleting** agent instructions (CLAUDE.md · `docs/workflow.md` ·
`docs/discipline.md` · hook rules · skills · agent definitions). Applies to this skill itself and
to every document this skill generates. At generation time, copy this document's "Voice",
"Counted Values", "One Rule, One Place", "Line Numbers", and "Memory" sections into the
"Instruction Authoring Policy" section of `docs/workflow.md`.

Instructions are written in English. Agent responses follow the user's language.

## Voice — Rules and Symptoms Only

Instructions are opened mid-task. The reader confirms one rule and moves on, and the argument
backing that rule is dead weight carried through that move.

**Keep**

- One directive line. Imperative and declarative ("do X / never do X").
- One clause of **symptom**. How you recognize the situation — a log string, a visible sign,
  the point where it breaks.

**Leave out**

- Violation anecdotes tied to a date, issue ID, or branch name.
- Measurements, reproduction records, evidence.
- The review process, alternatives weighed, excuses, retrospectives from the time of writing.
- Circumstances outside the rule's scope — never wedge one project's situation into a general
  document.

**Write a reason only when it is confirmed.** If the reason is not certain, drop it and keep the
rule and the symptom. Provenance, evidence, and reasoning belong in commit messages, reports,
and specs.

Symptom: the same document is being edited again after a short interval. A single rule grows
"amendment" and "revision" subsections. → Do not append; rewrite the section.

## Counted Values Stay Out of Documents

Values that come from **counting** — number of files, number of entries, number of consumers —
go wrong on a single change. Updating them is not the fix.

- Instead of a number, write the **means to recount** — a command, a script, a search term.
- What the decision needs is usually not the number but the **property** ("most of them are X").
- The exception is a record fixed to a point in time — commit message, report, spec.

Symptom: the count in the document differs from reality. "Both", "the only", "all of them" have
become false.

## One Rule, One Place

Writing the same rule in two places means only one gets fixed, and the other goes stale into an
**instruction that contradicts the current rule**.

- Point at a rule in another document by **path + section title**: `→ docs/workflow.md "Commit
  Rhythm"`.
- If a summary is needed, one line plus the pointer.
- Never point by section number (§3.2) — one inserted section throws it off. Point by section
  title.

## Source-of-Truth Placement

| Location | Holds | Does not hold |
|---|---|---|
| `CLAUDE.md` | Core principles that always apply + pointers to detailed documents | Long procedures, domain detail rules |
| `docs/workflow.md` | Branch, role, loop, report, merge, worktree procedures | Coding rules, domain usage |
| `docs/discipline.md` | Language-agnostic development discipline (observation, testing, prose) | Procedures |
| `.claude/hooks/session-start-header.md` | One-line summaries of repeatedly violated items + index of detailed documents | Rule text |
| `.claude/skills/*/SKILL.md` | Domain usage and patterns (topic lookup) | Copies of project-wide rules |
| `.claude/skills/review-*/references/rules.md` | Review lenses (severity + detection patterns) | Restatements of rule explanations |
| `.claude/hooks/file-pattern-map.json` | Reminders and gates at file-edit time | Rule bodies |

When placement is unclear, decide by **"when is this rule needed?"** Always → CLAUDE.md; when
entering a specific procedure → workflow.md; when opening a specific file → a file-pattern-map
rule; when looking up usage → a skill.

## Writing CLAUDE.md

It consumes context every turn. Length is cost.

- Actionable instructions only. Send project introductions and architecture explanations to
  `docs/` and leave a pointer.
- Do not write what is readable from the code (directory structure, file listings).
- Bullets, no paragraphs. Bold the key verb of each instruction.
- A prohibition is the prohibition plus one clause naming where it breaks.
- If an entry runs past three lines, move it to `docs/` and leave one line plus a pointer.

## Writing SKILL.md

- The frontmatter `description` decides whether the skill gets invoked. Write **"when should this
  be invoked?"** in `Use when …` form, not "what is this skill about?". Add one line on when not
  to use it.
- The body leads with the conclusion. Do not open with background.
- SKILL.md is an index; detail goes to `references/`. Let only the needed topic be read.
- Examples are in the minimal form that gets copied verbatim.
- Do not copy CLAUDE.md or `docs/*` rules into a skill body.

## Writing Agent Definitions

- Pin `model` and `effort` in the frontmatter. Inherited, the judgment bar shifts with the
  session settings.
- Remove `Write` and `Edit` from a reviewer's `tools`.
- Do not copy rules into the body. Point at the skill and the canonical document, and state
  **which one wins** when the two disagree.
- A subagent does not inherit CLAUDE.md — write the paths of the canonical documents it must read
  into the body.

## Writing Hook Rules

A hook is a device that keeps you from forgetting, not a device that teaches.

- `message` is a pointer to the canonical path. Do not copy the rule body into it.
- `requires` is fail-closed. A typo in a `reads` path or a `skills` name means nobody can edit the
  files that rule matches. After adding or editing one, confirm the actual match with the
  verification commands.
- Promote conservatively. Only what the instructions declare "required / read fully before
  proceeding" becomes `requires`. Everything else starts as `message`.
- Requirements that do not belong at edit time (pre-commit, pre-merge gates) are never hooked as
  `requires` — they block the writing itself.
- Notification is once per rule per session.
- Scripts keep exit 0 (fail-open) on exceptions.

## session-start-header Promotion Criteria

It is injected whole into every session and every subagent. One added line = a standing cost on
every session.

- Promote: an item already in the instructions that is violated repeatedly.
- Do not promote: a freshly written rule, or a rule limited to one domain (→ a file-pattern-map
  rule).
- Form: one-line summary + `→ canonical-document.md "Section"`. Do not move the original text.
- Demote it once the violations stop.

## Line Numbers: Never in Committed Documents

Point at code with **file name + symbol name**. `Foo.rs:391` is banned — one added line above
throws it off. The exceptions are the gitignored cache tied to a base commit (the design-review
fact ledger) and gitignored reports.

## Memory: No Permanent Rules

`~/.claude/projects/<slug>/memory/` is machine-local and is not passed to subagents. Putting
permanent rules, conventions, or recurring traps there makes behavior diverge between machines
and between main and sub sessions. Even when told "remember this", if it is a permanent rule,
write it at its place in the placement table and report where you put it.

## Adding a New Rule

1. Check for duplication — grep for a rule with the same intent. If one exists, edit that entry.
2. Decide placement — the placement table.
3. Write — directive + symptom.
4. If an edit-time reminder is needed, add a file-pattern-map rule → verify.
5. If there is a history of repeated violation, add one line to session-start-header.

## Companion Updates on Change or Deletion

Fixing one rule leaves whatever points at it stale. After editing, sweep with grep: the pointer
lines in `CLAUDE.md` · `session-start-header.md` · `message` / `requires.reads` in
`file-pattern-map.json` · the related `SKILL.md` · `.claude/agents/*.md`.

Deleting or moving a document leaves a path in `requires.reads` that can never be satisfied, and
nobody can edit the files that rule matches.

## Per-File Constraints

- `*.md` · `*.json`: UTF-8.
- `*.ps1`: ASCII characters only. PowerShell 5.1 reads non-ASCII literals without a BOM as cp949
  and corrupts them. If non-ASCII is genuinely required, save with a UTF-8 BOM.
- After editing `.claude/settings.json`, open the `/hooks` menu or restart for it to take effect.
