---
name: setup
description: "Use when initializing a new local project (no CI, no remote MR) with the PM-Dev-Reviewer workflow - CLAUDE.md, docs/workflow.md, commands, and selectable modules (autonomous review loop, commit rhythm, board, progress watch, /just, gate script, hooks, discipline doc, design-review gate). Also use to re-apply or update the workflow in an existing project. Not for GitLab/GitHub MR-based CI workflows."
---

# Setup Project Workflow

Sets up the local-merge PM-Dev-Reviewer workflow as **core + optional modules**. With no CI, a
local review that passes quietly has no backstop behind it — the devices that prevent that
(required arguments, convergence conditions, profiling, file-pattern gates) are what this
workflow is worth.

Every template lives in `references/`. This document is the procedure index. **When editing this
skill, follow `references/authoring-policy.md` too** — rules and symptoms only, no anecdotes,
dates, or counted values.

All generated documents are written in English. Agent responses follow the user's language.

## Procedure

### 1. Gather information

Confirm with the user (`references/modules.md` "Placeholders"):

- Project name · one-line description · primary language · absolute path of the main tree
- Worktree parent path (default `<parent>/<Repo>-worktrees`)
- Hosting (GitHub private / fully local)
- Source directories · source glob · directories excluded from review (vendor, generated)
- Gate commands (formatter, linter, test, build)
- Additional conventions

When re-applying to an existing project, read the current `CLAUDE.md`, `docs/workflow.md`, and
`.claude/` first and preserve project-specific sections (conventions, run info, domain rules).

### 2. Select modules

Present the table in `references/modules.md` through AskUserQuestion (multiSelect). For modules
on by default, ask what to turn off; for `design-review`, ask whether to turn it on. Turn
dependency modules on together with their dependents.

If `review-loop` was selected, ask for the review mode: `mixed` (default) / `official` /
`custom`. Then settle the round budget (default 3) and the `/code-review` effort (default
`high`).

If `review-loop` is `mixed` or `custom`, ask **"Where the value is"** — the one or two structural
defects in that project that pass both the compiler and the gate and still cause incidents. With
no answer, fall back to the language default (layer boundary violations).

### 3. Generate files

Copy the templates, substitute the placeholders, and process the module blocks (keep a
`<!-- module:X -->` block only when X was selected, and a `<!-- module:!X -->` block only when it
was not. Always delete the marker lines themselves).

| Target | Template |
|---|---|
| `CLAUDE.md` | `references/claude-md.md` |
| `docs/workflow.md` | `references/workflow-md.md` (+ insert the `authoring-policy.md` sections) |
| `.claude/commands/*.md` | `references/commands.md` |
| `.gitignore` | add `docs/reports/` · `.claude/settings.local.json` |
| [discipline] `docs/discipline.md` | `references/discipline-md.md` |
| [review-loop] skills and agents | `references/review-loop.md` (+ for `custom`, `review-rules-{lang}.md` → `references/rules.md`) |
| [board] 4 board documents · `docs/issues/` · `scripts/board-ready.sh` | `references/board.md` · `references/scripts/board-ready.sh` |
| [watch] `scripts/watch-commits.sh` | `references/scripts/watch-commits.sh` |
| [just] `.claude/commands/just.md` | `references/commands.md` "/just" |
| [gate-script] `scripts/check.ps1` | `references/scripts/check.ps1` (keep only the language block) |
| [hooks] `.claude/settings.json` · `.claude/hooks/*` | `references/hooks.md` · `references/scripts/` |
| [design-review] skill · 3 agents · design principles · `docs/specs/` | `references/design-review.md` · `references/design-review/` |

Every generated document follows the voice in `references/authoring-policy.md` — even when
writing project-specific sections, no anecdotes, dates, or counted values.

### 4. Verify

- [hooks] Actually run the commands in `references/hooks.md` "Verification". Confirm with
  `Test-Path` that every `requires.reads` path exists — a typo means nobody can edit the files
  that rule matches
- [board] `bash scripts/board-ready.sh` exits 0
- [gate-script] `scripts/check.ps1` passes on the current tree, or the failure is confirmed to be
  the project state (unfinished code) and not the script
- Leftover placeholder check: `grep -rn '{[A-Z_]*}' CLAUDE.md docs .claude scripts` returns none
- Leftover module marker check: `grep -rn 'module:' CLAUDE.md docs .claude` returns none

### 5. Commit

```bash
git add CLAUDE.md docs .claude .gitignore scripts
git commit -m "Add project workflow setup"
```

## Design rationale (why it is shaped this way)

- **Review runs in a clean context.** Nobody judges code they wrote themselves. Pass the target
  file list, not the conversation history
- **Tiers are pinned.** Inherited, the judgment bar shifts from round to round. The built-in
  `/code-review` takes effort as an argument; custom agents take it in frontmatter
- **Never drive the low grades to zero.** That leads back to comment self-propagation
- **Budget extensions are not made by editing the document.** They apply to that branch only
- **A user action is never a gate.** Verification happens in real use after the merge; ask only
  when observation is required
- **The gate list lives in one place.** A document that lists commands diverges from the script
- **Subagents do not inherit CLAUDE.md.** The agent body points at the canonical document by path
  and the hook injects the header
- **A rule that goes unread is a rule that keeps getting violated.** The file-pattern gate forces
  a Read before an edit
- **A promise is not progress.** A turn ending on "I'll continue from here" with no resume
  condition stops the loop silently and the user has to prod it back; the turn-end gate makes that
  ending cost one line instead

## References

| File | Contents |
|---|---|
| `references/modules.md` | Module catalog · placeholders |
| `references/authoring-policy.md` | Instruction authoring policy (this skill + generated documents) |
| `references/claude-md.md` · `workflow-md.md` · `discipline-md.md` | Document templates |
| `references/commands.md` | The 6 commands |
| `references/review-loop.md` | 3 review modes · dispatch table · skill and agent skeletons |
| `references/board.md` · `hooks.md` · `design-review.md` | Module detail |
| `references/scripts/` | Scripts, hooks, and settings to copy |
| `references/review-rules-*.md` | Per-language review lenses (`custom` only) |
