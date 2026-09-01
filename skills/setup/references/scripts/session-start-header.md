# Automatic Project Context Load

What follows are the core {PROJECT_NAME} rules the SessionStart/SubagentStart hook injects into
every session and every agent. **They apply regardless of the size of the work.** Read the
detailed rules under "Detailed Documents" below when entering the work.

## Repeat-Violation Traps — Re-registered Every Session

Only items already in the instructions that are violated repeatedly go here. _This is emphasis;
the source of truth is each instruction document. If the wording here differs from the document,
follow the document and report the mismatch to the user — quietly doing it the canonical way
leaves this list stale and still being injected._ Demote an item once the violations stop.

- **🚫 The main tree is always on `main`** — code work happens in a worktree, without exception.
  Switching branches in the main tree drags along uncommitted changes from other sessions and
  editors → `CLAUDE.md` "Git"
- **🚫 Never ask the user to build, run, or verify** — verification happens in real use after the
  merge. The one exception is when observation is required → `docs/workflow.md` "User
  Verification Happens After Merge"
- **🚫 Never re-measure a fact established in this session** → `docs/workflow.md` "Facts
  Established in This Session"
- **Batch the edits to one file into one response** — decide every place to fix first, then issue
  the non-overlapping `Edit` calls together → `docs/workflow.md` "Batch the Edits to One File into
  One Response"
- **🚫 No anecdotes, dates, or counted values in instructions and documents** →
  `docs/workflow.md` "Instruction Authoring Policy"
<!-- module:commit-rhythm -->
- **Commit at every logical unit; prefix a broken state with `wip:`** — the gate applies only to
  HEAD at report, review, and merge time → `docs/workflow.md` "Commit Rhythm"
<!-- /module:commit-rhythm -->
<!-- module:review-loop -->
- **Reviews run in a clean context with pinned tiers** — no `general-purpose`. State the effort
  for `/code-review` → `docs/workflow.md` "Autonomous Review-Fix Loop"
<!-- /module:review-loop -->
<!-- module:discipline -->
- **Comments have no default** — three questions right before writing one → `docs/discipline.md`
  "Comments"
- **Name them, do not count them** — the fixed `Consumers:` notation → `docs/discipline.md`
<!-- /module:discipline -->
- **No permanent rules in memory** → `CLAUDE.md` "Agent Behavior"

## Detailed Documents — Read When Entering the Work (Not Injected Whole Every Session)

- **Workflow, roles, loop, reports, merge** → `docs/workflow.md` _(injected for the main session)_
<!-- module:discipline -->
- **Development discipline (observation, tests, prose, comments)** → `docs/discipline.md`
<!-- /module:discipline -->
- **{LANG} conventions and gates** → `CLAUDE.md` "{LANG} Conventions"
<!-- module:board -->
- **Work board rules** → the top of `docs/board.md`
<!-- /module:board -->
<!-- module:design-review -->
- **Design principles and design review** → `docs/design-principles.md` ·
  `.claude/skills/design-review/SKILL.md`
<!-- /module:design-review -->
- **Adding and verifying hook rules** → `.claude/hooks/README.md`
