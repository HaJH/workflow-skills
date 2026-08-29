# CLAUDE.md Template

Generate the following as `{PROJECT_PATH}/CLAUDE.md`. Substitute the placeholders and process the
module blocks. Do not duplicate rules the user's global `~/.claude/CLAUDE.md` already carries
(end-of-turn reporting, AskUserQuestion confirmation, no auto-generated commit message trailers).

```markdown
# {PROJECT_NAME}

{ONE_LINE_DESCRIPTION}

## Ground Rules

- Respond and plan in the user's language. Write code, comments, and documents in English
- Windows is the baseline
- **Instruction and skill documents carry directives and symptoms only.** No anecdotes tied to a
  date or issue ID, no measurements, no provenance. Never pin a counted value
  → `docs/workflow.md` "Instruction Authoring Policy"
- **Never re-measure a fact established in this session** — files read, command output, and user
  answers from this session are used as they are
  → `docs/workflow.md` "Facts Established in This Session"

## Git

- Hosting: {HOSTING}
- Branches: `main` (stable) + `feature/*` + `hotfix/*`
- **No direct code commits on main** — land work only through a local `git merge --no-ff` (never
  squash)
- **The main tree `{PROJECT_PATH}` always stays on `main`.** Work that changes code happens
  without exception in the worktree `{WORKTREES_PATH}/<branch name with feature/ stripped>`.
  Switching branches in the main tree drags uncommitted changes from editors and other sessions
  sharing that working tree onto that branch
- **Documentation work with no code change is committed directly on main** (all of `docs/`,
  `*.md`). Documents that change together with code ride that code's branch
- No `cd` pattern → use `git -C`
- Detailed procedure: `docs/workflow.md`

<!-- module:board -->
## Work Management

- `docs/board.md` — lightweight kanban board (In Progress / ToDo). `/pm` owns the updates
- `docs/roadmap.md` — milestone roadmap · `docs/backlog.md` — dropped and deferred ·
  `docs/board-archive.md` — done
- `docs/issues/<id>.md` — a card's background, provenance, and decisions. **The card is one line;
  the detail goes here**
- `bash scripts/board-ready.sh` — startable cards, stale prerequisites, broken references
- The flow is `issue → design → implementation → done`. A design document is an issue's output,
  not the source of work
<!-- /module:board -->

## Agent Behavior

- **Start gate — investigating is not starting**: the output of a turn that asks a question or
  raises a problem is an investigation report plus a proposed direction. Change files only after
  the user permits it. The exception is a precisely specified trivial single fix
- Feature branch work proceeds without confirmation. **Always confirm**: merging to main, design
  changes
<!-- module:commit-rhythm -->
- **Dev commits at every logical unit.** Commit a broken in-progress state with a `wip:` prefix
  and do not demand a gate for it. The gate applies only to HEAD at report, review, and merge
  time → `docs/workflow.md` "Commit Rhythm"
<!-- /module:commit-rhythm -->
- **Never ask the user to build, run, or verify.** Verification happens in real use after the
  merge. The one exception is when you cannot pin the cause alone and need an observation
  → `docs/workflow.md` "User Verification Happens After Merge"
- **No permanent rules in memory** — memory is machine-local and is not passed to subagents.
  Permanent rules go in this file, `docs/`, or skill documents

<!-- module:review-loop -->
## Feature Completion Flow

Dev proceeds autonomously. Each round:

1. `/report`
2. **Assemble the target** — the union of `main...HEAD`, uncommitted, and untracked, minus
   `{EXCLUDE_DIRS}`
3. **Dispatch in parallel** — all reviews in one message. Clean context, pinned tiers
   → the dispatch table in `docs/workflow.md` "Autonomous Review-Fix Loop"
4. **Fix** — one commit per issue. At the end of the round the gate passes and the report is
   updated
5. **Convergence check** — if any top-grade finding remains, go to 1. Otherwise stop
6. Report to PM

Never try to drive the low grades to zero — write the reason in the report and move on. The round
budget is {ROUND_BUDGET}, and on reaching it you do not auto-continue but take the user's
decision. The `/review-*` skills are **for targeted ad-hoc checks only** (argument required).
<!-- /module:review-loop -->

## Commands

- `/pm` — start a PM session
- `/commit` — create a commit
- `/report` — write or update the Dev report
<!-- module:review-loop -->
- `/review <branch>` — Reviewer code review
<!-- /module:review-loop -->
- `/merge-branch <branch>` — merge an approved branch into main
<!-- module:just -->
- `/just <task>` — procedure-skip mode. Only the small requested change, right in the current tree
<!-- /module:just -->

<!-- module:review-loop -->
## Skills

{SKILL_LIST}
<!-- /module:review-loop -->

<!-- module:design-review -->
## Design Review Gate

For a change of size (structural change, new subsystem, interface change), write a spec in
`docs/specs/` before implementing, and if the spec contains code structure design, run
`/design-review` before committing. **Overriding a Blocker is the user's decision**, and an
accepted decision is recorded in the spec as an "Accepted Cost" → `docs/design-principles.md`
<!-- /module:design-review -->

<!-- module:discipline -->
## Development Discipline

Never assert causality without observation · trace back what a test actually supports · name them
instead of counting them · comments have no default → `docs/discipline.md`. Applies to Dev and
Reviewer alike.
<!-- /module:discipline -->

## {LANG} Conventions

{LANG_CONVENTIONS}
```

## Substitution Notes

- `{SKILL_LIST}`: depends on the review mode. `mixed` → one line for `/refactor-review`. `custom`
  → `/review-code` + `/refactor-review` (+ any extra lenses). `official` → delete the "Skills"
  section itself.
- `{LANG_CONVENTIONS}`: gate command (`{GATE_CMD}`), formatter and linter, project-specific
  prohibitions. If a global language skill exists (`rust-guide` and the like), replace this with
  one line — "for patterns and idioms see the global `<skill>`" — and do not duplicate it here.
  When `review-loop` is `mixed` or `official`, this section is the only rules source the built-in
  `/code-review` reads, so put **the project-specific rules a tool cannot catch** here (do not
  write what the linter catches).
