# CLAUDE.md Template

Generate the following as `{PROJECT_PATH}/CLAUDE.md`. Substitute the placeholders and process the
module blocks. Do not duplicate rules the user's global `~/.claude/CLAUDE.md` already carries
(end-of-turn reporting, confirming decisions with the user, no auto-generated commit message trailers).

```markdown
# {PROJECT_NAME}

{ONE_LINE_DESCRIPTION}

## Ground Rules

- Respond and plan in the user's language. Write code, comments, and documents in English
- Windows is the baseline
- **Make no exceptions**: whether it is a plan or code, build the new thing along the one path the
  existing rules already cover. An exception is a branch that applies a rule differently to only
  some paths or cases among the things the rule covers — a change that applies equally to
  everything the rule covers is not an exception but a fix to that rule, made in its canon or its
  shared handling. When the one-path result fails to preserve something or looks at odds with the
  intent, do not block it with an exception branch; **ask the user, with the impact, whether to
  accept it as a cost or to change the rule**. Exceptions, as they pile up, make behavior
  unpredictable from the rules alone and become grounds for the next exception; closing an
  off-target result alone as "per the rules" buries the gap in the rule
- **Instruction and skill documents carry directives and symptoms only.** No anecdotes tied to a
  date or issue ID, no measurements, no provenance. Never pin a counted value
  → `docs/workflow.md` "Instruction Authoring Policy"
- **Never re-measure a fact established in this session** — files read, command output, and user
  answers from this session are used as they are
  → `docs/workflow.md` "Facts Established in This Session"
- **Batch the edits to one file into one response** — decide every place to fix first, then issue
  the non-overlapping `Edit` calls together. Symptom: `Edit` calls to the same file go out back to
  back
- **Suggest a new session only when the topic changes<!-- module:hooks --> or the length signal
  appears<!-- /module:hooks -->, and when the user agrees, open it yourself and detach it** — when
  the next task uses none of the context so far, suggest one regardless of length<!-- module:hooks -->;
  once the `UserPromptSubmit` hook injects `[session length]`, suggest one at the next natural
  boundary (end of a review round, right after a commit, close of a spec section), not on the
  spot<!-- /module:hooks -->. Context size is invisible from inside the conversation, so never
  suggest one because the session feels long — the number of review rounds is no ground either.
  Before suggesting, see whether the remaining work can go to a subagent — delegating keeps the
  conversation in one session, a handoff cuts it. **Write the handoff note only after the user
  agrees**, light enough to paste as the new session's first message (work location, current
  state, next thing to do). Once the user answers that they will continue, do not suggest it again
  <!-- module:hooks -->until the hook injects the next signal<!-- /module:hooks --><!-- module:!hooks -->unless the topic changes again<!-- /module:!hooks -->.
  Cutting is the user's call → `docs/workflow.md` "Session Length — When to Suggest a Handoff" ·
  "Linked Sessions". Symptom: one short edit carries the whole context of an earlier topic; a
  suggestion or handoff note comes up again after the user said they would continue

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
- **Pass the path as an option** — `git -C` and the like. Then a call that moves between worktrees
  needs no tracking of the working directory. This is the default, not a prohibition
- Detailed procedure: `docs/workflow.md`

<!-- module:board -->
## Work Management

- `docs/board.md` — lightweight kanban board (In Progress / ToDo). `/pm` owns the updates
- `docs/roadmap.md` — milestone roadmap · `docs/backlog.md` — dropped and deferred ·
  `docs/board-archive.md` — done
- `docs/issues/<id>.md` — a card's background, provenance, and decisions. **The card is one line;
  the detail goes here**
- `bash scripts/board ready` — startable cards, stale prerequisites, broken references
- `/board`, or `scripts/board` in a terminal (`scripts\board` in Windows cmd) — the board as a
  read-only kanban page
- The flow is `issue → design → implementation → done`. A design document is an issue's output,
  not the source of work
<!-- /module:board -->

## Agent Behavior

- **Start gate — investigating is not starting**: the output of a turn that asks a question or
  raises a problem is an investigation report plus a proposed direction. Moving the work forward
  — changing files, giving work instructions — starts only after the user permits it. When you
  cannot tell whether a message is a question or an instruction to proceed, take it as a question:
  answer it and ask whether to proceed. The exception is a precisely specified trivial single fix the user asked for
- Feature branch work proceeds without confirmation. **Always confirm**: merging to main, design
  changes. An instruction to "proceed on your own" does not shorten the procedure — follow it and
  pass without asking only where no user decision is needed; decisions and the confirmations the
  procedure sets still go to the user
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
`docs/specs/` before implementing. **Write the spec only after the user approves the whole
description, and do not have the user read the written spec for confirmation** — the design review
checks the draft, and the user is asked only about what the agent decided on its own and what the
review handed over → `docs/workflow.md` "Before and After the Spec". If the spec contains code
structure design, run
`/design-review` before starting implementation. **The gate blocks implementation, not the
commit** — commit the spec after every round, and the `Status` line at its head carries that
round's verdict. **Overriding a Blocker is the user's decision**, and an accepted decision is
recorded in the spec as an "Accepted Cost" → `docs/design-principles.md`
<!-- /module:design-review -->

<!-- module:doc-review -->
## Instruction Document Review

After rewriting a section of an instruction document (`CLAUDE.md`, anything under `docs/`, a skill
or agent definition), run `/doc-review <path> section "<title>"` before committing. A full
`/doc-review <path>` when the document was added or its frontmatter changed. **The review's
deliverable stops at the defect list** — what gets fixed is your call
→ `docs/authoring-policy.md`
<!-- /module:doc-review -->

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
