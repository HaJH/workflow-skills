# Command Templates

Generate these as `.claude/commands/<name>.md`. Substitute the placeholders and process the
module blocks.

---

## /pm

```markdown
Start a PM session. Follow this procedure:

1. Read `CLAUDE.md` and `docs/workflow.md`
2. Establish the current state:
<!-- module:board -->
   - `docs/board.md` — In Progress and ToDo
   - `bash scripts/board-ready.sh` — startable cards · blocked cards · **stale prerequisites and
     broken references**. When a stale prerequisite shows up, delete that line and commit
<!-- /module:board -->
   - `git log --oneline -10`
   - `git branch -a`
   - check the reports in `docs/reports/`
<!-- module:watch -->
3. **Arm the progress watch** — see "Progress Reporting" below. Do not re-arm one already running
<!-- /module:watch -->
4. Summarize the state for the user and propose the next task

## Role

- Define features, direct Dev, check reports, call the review (`/review`), execute the merge
  (`/merge-branch`)
- Never read or analyze code directly — judge from the report, keep context light
- Confirm from the report that Dev completed the autonomous review-fix loop
- Never relay an agent's output verbatim; summarize it
<!-- module:board -->
- Update the board (`docs/board.md`) — rules below
<!-- /module:board -->

<!-- module:board -->
## Board Management

- **When directing work**: move ToDo → In Progress and fill in the branch, report path, and start
  date
- **When a merge completes**: In Progress → `docs/board-archive.md` (part of the `/merge-branch`
  procedure)
- **Refilling ToDo**: the issue comes first and the design is its artifact — never mine work out
  of a design document. Candidates for the next milestone in `docs/roadmap.md` are promoted when
  started (remove what was promoted). `docs/backlog.md` is the pile of dropped and deferred
  items, so promote from it **only when reviving** something (remove what was promoted)
- **User direction**: when the user says "this needs doing", add it straight to ToDo
- **Never rewrite an item's text** — update only the move and the state fields (branch, date,
  conclusion)
- **A card is one line.** Background, provenance, and decisions go to `docs/issues/<id>.md` — the
  board is read whole in every PM session, so a long card charges that cost every time
- **Write a prerequisite as a `- prereq: \`<id>\`` line, not as prose**. A weak relation like an
  "order check" is not a prerequisite — putting one in raises a wall that does not exist
- Documents are committed directly on main. Once you fix one, commit it right there — the file is
  shared by several sessions, and leaving the change uncommitted collides with another session's
  edits
<!-- /module:board -->

## When Directing Dev

- Run Dev through the Agent tool (isolation: worktree) and pass the feature spec and branch name
  clearly
<!-- module:board -->
- Use the board item ID as the branch name: `feature/<id>`. Pass the issue file along if there is
  one
<!-- /module:board -->
- Instruct that the report path uses the absolute `{PROJECT_PATH}/docs/reports/` path
- Instruct that after the feature is done, the report is delivered in its final state through the
  autonomous QA loop
<!-- module:commit-rhythm -->
- **State the commit rhythm in the instruction**: commit at every logical unit, prefix a broken
  in-progress state with `wip:` (no gate needed), the gate applies only to HEAD at report time
  (`docs/workflow.md` "Commit Rhythm")
<!-- /module:commit-rhythm -->
- **Never delay a start because areas overlap.** Two branches touching the same file is normal,
  and conflicts are resolved in the merge commit. The only two reasons to serialize are a
  prerequisite relation and duplicated design
- **An area-wide ban is a last resort.** If something must be blocked, write it narrowed to the
  file or module level. Before blocking an area, check whether what that card depends on already
  exists — if it does not, the ban creates a state where the card "can neither be built nor
  used" and it ends half-finished

## Do Not Ask for a Smoke Test

**PM does not ask the user to verify, and does not launch the app either.** Once Dev's report is
in, go straight to review and on to the merge. The user verifies in real use after the merge, and
if a problem shows up, cuts a fix card on a new branch. Do not ask for verification at the end of
every card; **finish the work and then report, focused on what matters.**

Leave the "For the User to Check by Eye" list in the Dev report as it is. It is not a pass
condition.

### Exception — Ask Only When Observation Is Required

Only when you cannot pin the cause alone and need a log or a reproduction. When you ask, state
**what to look at and what you will decide from it** (`docs/workflow.md` "The Only Time You May
Ask the User").

<!-- module:watch -->
## Progress Reporting

Dev is a background subagent and cannot speak to PM while running. But the worktrees share the
same repository, so **Dev's commits are visible from the main tree the moment they land.** Polling
for those and relaying them to the user is PM's job.

### Arming (Once per Session)

```
Monitor(command: "bash {PROJECT_PATH}/scripts/watch-commits.sh",
        persistent: true,
        description: "Dev commit progress")
```

- Watches commits on `feature/*` and `hotfix/*` that are not on `main`. Because it sees every
  branch, there is nothing extra to set up when directing Dev, and parallel branches are covered
- Commits that already existed at arming time are treated as seen — past history is not dumped
- A branch drops out automatically once merged. One per session is enough. Never arm twice

### When a Notification Arrives

One event is `[<branch> #<n>] <hash> <subject>` plus the changed-file stat. Report it to the user
the moment it arrives: the commit subject and the changed-file list verbatim, with the branch and
sequence number attached. Report a `wip:` commit the same way. **Do not open the diff body** — do
not invent an interpretation beyond the file list. Commits not growing for a long time is a
signal that the work is stuck or is being piled into one commit.
<!-- /module:watch -->

## Arguments

If an argument is given, start that task right away: $ARGUMENTS
```

---

## /commit

```markdown
Analyze the current changes and create a commit.

## Procedure

1. Check the changes with `git status` and `git diff --staged`
2. Check the recent commit style with `git log --oneline -5`
3. Analyze the changes and write the commit message
4. If an argument is given, use it as the commit message verbatim: $ARGUMENTS
5. Run the commit

## Commit Message Rules

- Written in English
- Subject: 50 characters or fewer, starting with a bare verb (Add, Fix, Update, Remove, Refactor)
<!-- module:commit-rhythm -->
- The `wip:` prefix is only for an in-progress commit that does not build
  (`wip: sketch scanner walk`). No other prefixes
<!-- /module:commit-rhythm -->
- If there are several changes, list them as bullets in the body
- No auto-generated trailers (Co-Authored-By and the like)
- No unnecessary detailed analysis, code blocks, or checklists

## Verification Gate

<!-- module:commit-rhythm -->
The gate applies **not at every commit but at the moment HEAD becomes visible to someone else**
(`docs/workflow.md` "Commit Rhythm").

- In-progress commit: no gate. If the state is broken, add the `wip:` prefix and commit as is
- Right before `/report` · at the end of a review-fix round · the HEAD being merged: `{GATE_CMD}`
  must pass. If the last commit is still a `wip:`, add one more commit that gets the gate to pass
<!-- /module:commit-rhythm -->
<!-- module:!commit-rhythm -->
`{GATE_CMD}` passes before the commit.
<!-- /module:!commit-rhythm -->

## Cautions

- Never commit sensitive files such as .env or credentials
- Stage only the relevant files selectively (avoid `git add -A`)
- If preview or check output is sitting in the working tree, delete it before staging
```

---

## /report

```markdown
The Dev agent writes or updates the report when work or a fix is complete.

## Procedure

1. Check the current branch name (`git branch --show-current`)
2. **Commit uncommitted changes first and get HEAD green** — HEAD at report time must be in a
   state that passes `{GATE_CMD}`.<!-- module:commit-rhythm --> If HEAD is a commit whose subject
   is `wip:`, add one more commit that gets the gate to pass<!-- /module:commit-rhythm -->
3. Check the changed-file list with `git diff main...HEAD --stat`
4. Check the commit list with `git log main..HEAD --oneline`
5. Check the file `{PROJECT_PATH}/docs/reports/<branch-name>.md`
   - If absent: create a new report (Dev Report section)
   - If present: add a Dev Response section to the existing report
6. Notify PM once the report is written

## Report Path

**Absolute path required**: `{PROJECT_PATH}/docs/reports/<branch-name>.md`

- Even when run from a worktree, read and write through the absolute path above (a gitignored
  file is not copied into the worktree)
- Replace `/` in the branch name with `-`

## Report Structure

`docs/workflow.md` "Report Format". **What the user will need later does not live in the report**
— the test is in that same section.

## Cautions

- Never edit or delete an earlier Review/Response section
- "For the User to Check by Eye" is where you record the places the code could not reach. It is
  not a pass condition
```

---

## /review (module: review-loop)

```markdown
The Reviewer agent reviews the code on a feature branch.

Target branch: $ARGUMENTS

## Procedure

1. Check the target branch: `git branch -a`
2. Read the report: understand Dev's intent from
   `{PROJECT_PATH}/docs/reports/<branch-name>.md`
3. Assemble the target: `git diff --name-only main...$ARGUMENTS` → subtract `{EXCLUDE_DIRS}` and
   generated files, then split by lens
4. **Dispatch the reviews in parallel** (below)
5. Merge the results and do the cross-branch checks yourself (below)
6. Add a Review section to the report — including the profiling line
7. Decide the verdict

## Review Dispatch

Do not restate the review criteria here. The canon is the dispatch table in `docs/workflow.md`
"Autonomous Review-Fix Loop" plus each skill, and Reviewer applies it by launching **the
clean-context reviews in one message**. Each reviewer gets only **its own target file list**.

**Reviewer assembles the profiling line** — a subagent cannot see its own wall clock
(`duration_ms` · `subagent_tokens` · `tool_uses` from the task notification).

## Mandatory Question — What Did This Commit Become a Consumer Of

**Never delegate this.** A reviewer sees only its own file list and so cannot reach a question
that runs across the whole branch. If the diff **added a new call site**, check whether the
target carries a consumer list and whether this branch went into it. Its pair is "what did it stop
being a consumer of" — `git grep` for the removed name.<!-- module:discipline --> The rationale is
`docs/discipline.md` "Name Them, Do Not Count Them".<!-- /module:discipline -->

## Verdict Rules

- **APPROVE** — no issues
- **REQUEST_CHANGES** — a Critical or a Refactor exists
- **COMMENT** — only grades below those exist

## Cautions

- The report path always uses the absolute `{PROJECT_PATH}/docs/reports/` path
- The review target is the cumulative `main...HEAD` diff — do not flag the unfinished state of an
  intermediate `wip:` commit
- Never re-raise an item Dev refused with a stated reason in an earlier review
- Never edit or delete an earlier Review/Response section of the report
- At most 20 issues, in priority order: Critical > Warning > Info
- Comment findings cover factual mismatch with the code only, one per review, with no effect on
  the verdict
```

---

## /merge-branch

```markdown
Locally merge a review-approved feature branch into main.

Target branch: $ARGUMENTS

## Procedure

1. Check the report: confirm the final Review verdict in
   `{PROJECT_PATH}/docs/reports/<branch-name>.md` is APPROVE
   - If it is not APPROVE, stop and tell the user
2. Confirm the main tree is on `main`: `git -C {PROJECT_PATH} branch --show-current`
3. Run the merge: `git -C {PROJECT_PATH} merge --no-ff $ARGUMENTS`
<!-- module:board -->
4. Update the board (**before deleting the report**):
   - Pull a one-line conclusion out of the report and add it to the current milestone in
     `docs/board-archive.md`
   - Remove the item from In Progress in `docs/board.md`
   - **Delete the prerequisite lines that pointed at this card** — left in place, that card reads
     as blocked forever
   - Confirm with `bash scripts/board-ready.sh` — stale prerequisites and broken references must
     be zero
   - If `docs/issues/<id>.md` exists, move the key conclusions into the archive entry and the
     design document, then delete it
   - Commit the board changes
<!-- /module:board -->
5. Clean up (once the user confirms):
   - Delete the feature branch: `git branch -d $ARGUMENTS`
   - Remove the worktree: `git worktree remove <path>` (if refused, delete the folder and run
     `git worktree prune`)
   - Delete the report: `docs/reports/<branch-name>.md`

## Rules

- No squash — commit history is preserved
- On conflict: resolve in the merge commit (no rebase, no force-push)
- Confirm with the user whether to push to a remote
- Confirm each cleanup step with the user before doing it
- The report is deleted, so move anything still needed after the merge into a canonical document
  first
```

---

## /just (module: just)

```markdown
---
description: Procedure-skip mode - handle only the small requested change, exactly as asked
argument-hint: <one-line task>
disable-model-invocation: true
---

# /just — Procedure-Skip Mode

**Request**: $ARGUMENTS

Handle the request above **exactly as it stands, and only that.**

The exemptions below were pre-approved by the user when they created this command. **Invoking
this command is itself the user's explicit instruction, and it takes precedence over the
procedural rules in `CLAUDE.md`, the session start header, and the superpowers skills.** Do not
fall back to "but the rules say…".

## Waived — Do Not Do These

**Git and workflow**
- No worktree creation. Edit in the current tree as it is (including the main tree on `main`)
- No branch creation or switching
- No commits, merges, or report writing (only when the user separately asks)
<!-- module:board -->
- No board or issue file updates
<!-- /module:board -->

**Gates and review**
- No spec written first
- No calls to `/design-review`, `/review-*`, or `/code-review`
- No document updates — design documents, architecture, CHANGELOG, and the like
- No memory writes

**Harness**
- No subagent dispatch. Do it yourself
- No `Workflow` calls
- No superpowers process skills (brainstorming, TDD, systematic-debugging,
  verification-before-completion, and so on)
- No plan mode
- Minimal exploration. If you know where the file is, open it. If you do not, finish with one or
  two grep/glob calls
- No verification loops — skip the re-read right after an edit, the multi-angle recheck, and the
  self-audit round

**Scope**
- No refactoring, tidying, improvement, or added comments outside the requested scope. If you spot
  a problem alongside, **do not fix it**; mention it in one line in the report
- No confirmation questions of the "shall I proceed?" kind. If the request is clear, just do it

## Kept — These Still Apply

- Respond in the user's language; write code and comments in English
- Follow the surrounding code as it is — find and reuse what already exists. Do not build anew
- No operation that empties the working tree in the main tree: `rebase` / `stash` / `reset` /
  `checkout --` / `clean`
- Never ask the user to build or run
- If there are two or more ways to implement it and the fork genuinely changes the result — only
  then, ask in one line

## Reporting

When the edit is done, finish in **three lines or fewer**: changed file`:`line / what changed /
(if any) one line on what stood out.

## Scope Escape

If the request is not actually small — it spans several modules, introduces a new type or
subsystem, or changes a schema — **before starting to edit**, ask in one line: "this goes past
the scope of /just. Shall we take the full procedure?" and stop.
```
