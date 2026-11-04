# docs/workflow.md Template

Generate the following as `{PROJECT_PATH}/docs/workflow.md`. Leave the three stop conditions and
the budget-extension rule in "Autonomous Review-Fix Loop" exactly as they are, without
summarizing — together they are the whole reason the loop does not diverge. Fill the "Instruction
Authoring Policy" section by moving in the "Voice", "Counted Values", "One Rule, One Place",
"Line Numbers", and "Memory" sections of `authoring-policy.md`.

```markdown
# {PROJECT_NAME} Development Workflow

## Running and Building

<!-- module:gate-script -->
- **The gate list is `scripts/check.ps1`, and nothing else.** This document and the commands only
  point at it. A document that lists commands diverges from the script, and it always diverges in
  the quiet direction. To see what runs, read that file
- Fix formatting first — the gate rejects rather than fixes: `{FORMAT_CMD}`
<!-- /module:gate-script -->
<!-- module:!gate-script -->
- Verification gate (before committing): `{GATE_CMD}`
<!-- /module:!gate-script -->
- {RUN_NOTES}

## Branch Strategy

- `main` — stable branch. No direct commits; landed only through a local merge
- `feature/*` — feature development · `hotfix/*` — urgent fixes

### Worktree Required (Code Work)

The main tree `{PROJECT_PATH}` **always stays on `main`.** Keep the editor attached there too,
and the only work done there is documentation. Work that changes code happens in a worktree,
without exception:

```powershell
git -C {PROJECT_PATH} worktree add -b feature/<id> {WORKTREES_PATH}/<id>
# work -> commit -> merge from main
git -C {PROJECT_PATH} merge --no-ff feature/<id>
git -C {PROJECT_PATH} worktree remove {WORKTREES_PATH}/<id>
git -C {PROJECT_PATH} branch -d feature/<id>
```

- The folder name is the flat name left after stripping the `feature/` prefix from the branch name
- A worktree branches from the latest local `main` commit. `EnterWorktree` branches from the
  current HEAD, so if the main tree is not on `main` it branches from an old version
- When the `-worktrees` folder is empty, delete the folder itself
- If `git worktree remove` refuses with "Directory not empty" (build output, `node_modules`),
  delete the folder and then run `git worktree prune`. Skip the `prune` and a ghost stays in
  `git worktree list`

**Documentation work with no code change is committed directly on main.** All of `docs/` and
`*.md`. Do not cut a branch and a worktree to fix one line of a document. A design document that
changes together with code rides that code's branch.

## Agent Roles

- **PM** (main session): defines features, directs Dev, checks reports, calls Reviewer, executes
  merges. Judges from the report without reading code directly — keeping context light.
  <!-- module:watch -->Watches Dev's commits and relays them to the user (`/pm` "Progress Reporting").<!-- /module:watch -->
- **Dev** (worktree subagent): isolated development. Implement → autonomous QA loop → finalize
  report → report to PM.
  <!-- module:commit-rhythm -->Commits at every logical unit even mid-work, so the state is visible ("Commit Rhythm").<!-- /module:commit-rhythm -->
- **Reviewer**: reviews from the diff plus the report. Records the verdict in the report.

## Feature Lifecycle

Plan (PM) → develop (Dev, worktree) → autonomous QA (Dev) → report (Dev) → review (Reviewer) →
merge (PM) → clean up → **user verification in real use (after merge)**

### User Verification Happens After Merge

There are areas whose runtime results (GUI, sound, interaction) neither Dev nor Reviewer can see.
Those defects are not ones the review misses — they are ones the review **cannot reach**, and
more rounds will not surface them. Do not make that blind spot a gate.

- **PM does not ask for a smoke test.** PM does not launch the app either. Once Dev's report is
  in, go straight to review and on to the merge
- The user verifies **in real use after the merge**. If a problem shows up, cut a fix card on a
  new worktree and branch. The original card is closed as it is
- Keep **"For the User to Check by Eye"** in the Dev report. It is the only place that records
  where the code could not reach, and it tells a fix card where to look first. It is not a pass
  condition
<!-- module:board -->
- At the merge that list moves into the card's issue file, and the card waits in the board's Done
  column until the user, having used the work, says it holds up, or a fix card takes over
<!-- /module:board -->

The cost is accepted: defects can remain in merged code. What makes this trade-off possible is a
fully local repository, where a merge is not a hard-to-reverse operation.

### The Only Time You May Ask the User — Observation

Ask only when you cannot pin the cause alone and need a log or a reproduction. When you ask,
state **what to look at and what you will decide from it**. "Please take a look" is not an
observation.
<!-- module:discipline -->
The rationale and the checklist are in `docs/discipline.md` "No Causal Claims Without Observation".
<!-- /module:discipline -->

<!-- module:commit-rhythm -->
## Commit Rhythm (Dev)

Dev **commits at every logical unit.** A commit is not the wrapping on a finished product; it is
Dev's progress log — the user and PM must be able to see how far the work has come from `git log`
alone. Finish in one commit and nothing is visible until everything is done, with no point to
return to when the direction goes wrong.

A logical unit is one meaningful piece of work: "add the DTO", "implement the scanner", "wire the
command", "add tests". Cut at these points: after adding one new module, type, or command · after
finishing one chunk of a change to existing behavior · after fixing one review issue · right
before changing direction.

### Intermediate Commits May Be Broken

- Commit a state that does not even compile. Prefix the subject with **`wip:`**
  (`wip: sketch scanner walk`)
- A `wip:` commit is not required to pass the gate
- The gate is required only **at the moment HEAD becomes visible to someone else**: right before
  `/report` · at the end of each review-fix round · the HEAD being merged. If the last commit is
  still a `wip:`, add one more commit that gets the gate to pass

The cost is accepted: `wip:` commits stay in main's history and `git bisect` is meaningless over
that stretch. Skip `wip:` commits when bisecting. Do not tidy the intermediate commits before
merging — the ban on squash and rebase stands.
<!-- /module:commit-rhythm -->

<!-- module:review-loop -->
## Autonomous Review-Fix Loop

Dev runs this after finishing the implementation, without PM involvement. The review **does not
run inside the Dev session** — it is dispatched to clean-context subagents.

### Why Subagents

Not for speed, but **so that nobody judges the code they wrote themselves.** That is this
review's only value, which is why **the conversation history is not passed on** — a subagent gets
the target file list and nothing else, and everything about how to review comes from the skill
and the canonical documents.

**Pin the tiers.** Inherited, the judgment bar shifts from round to round with the session
settings. Structural judgment is exactly the part pattern matching cannot do, so it must not drop
along with a lowered session effort.

{DISPATCH_TABLE}

### Each Round

When a step finishes, **move to the next one without asking for confirmation**.

1. **Assemble the target** — everything the branch changed:

   ```bash
   git diff --name-only main...HEAD          # committed changes
   git diff --name-only HEAD                 # uncommitted
   git diff --name-only --cached             # staged
   git ls-files --others --exclude-standard  # new, untracked
   ```

   Take the union, subtract `{EXCLUDE_DIRS}` and generated files, then split it by lens.

2. **Dispatch in parallel** — put the review calls **in one message**. Drop a lens that has no
   targets. Each reviewer gets only **its own target file list**.

3. **Merge the results** — combine the reports per file and carry the profiling line with them.
   **The orchestrator assembles it** — a subagent cannot see its own wall clock (`duration_ms` ·
   `subagent_tokens` · `tool_uses` from the task notification).

4. **Fix** — commit each time you fix one issue. At the end of the round, get the gate to pass and
   update the report.

5. **Prose sweep** — <!-- module:discipline -->`docs/discipline.md` "Prose Sweep"<!-- /module:discipline --><!-- module:!discipline -->`git grep` + `grep -r docs/reports/` for symbols this round deleted or newly introduced<!-- /module:!discipline -->

6. **Convergence check** — below. If it has not converged, go back to 1.

### Convergence Check

**There is one condition for continuing: if a live top grade (Critical / Refactor) remains, run
another round.**

**Stop** (any one of these):

1. **Zero findings.**
2. **No top grade remains.** For the low grades that are left, write the reason in the report and
   move on — **trying to drive those to zero as well leads back to comment self-propagation.**
3. **The previous fix changed only comments or document text** (no code token changed). That is
   the point that breaks the self-propagation where a comment invites the next round's finding.

**Gates** (not an automatic stop — **the user decides**):

- **Non-convergence** — round N's findings brought back round N-1's material **with no new
  evidence in the code**. Do not fix it one more time; stop. A review that does not converge is
  not a problem more rounds will solve.
- **The round budget {ROUND_BUDGET} was reached and a top grade remains** — organize the
  remaining findings by grade, report to PM, and stop. **Do not pass it through automatically.**
  Whether to keep going, pass it through as is, or rescope is the user's decision.

  **An extension is not made by editing this document.** When the user approves "N more rounds",
  that approval is valid **for that branch only**. Leave the constant {ROUND_BUDGET} alone —
  editing the document means the next feature starts from there and extends again, so **the
  budget ratchets upward feature by feature** and its whole purpose as a loop safeguard is gone.

Limit the check to **comparing the material in the findings text**. Do not re-adjudicate whether
a finding is valid here — that belongs to the clean-context reviewer, and reversing it from this
side reproduces the self-judgment problem exactly. The place to refuse with evidence is the
Response section of the report.
<!-- /module:review-loop -->

## Report Format

- Path (**absolute path required** — the same path is used from inside a worktree):
  `{PROJECT_PATH}/docs/reports/<branch-name>.md`
- Replace `/` in the branch name with `-` (e.g. `feature/scan` → `feature-scan.md`)
- Excluded from git tracking (gitignored). Because the report is gitignored it is not copied into
  the worktree, so read and write it by absolute path only
- Never edit or delete an earlier Review/Response section
- Delete it after the merge completes

### What the User Will Need Later Does Not Live in the Report

The report is gitignored and `/merge-branch` deletes it. Whatever is read after the merge needs a
place to move to before then — what is left only in the report **is erased, with no way to recover
it from history either.**

- The test is "**does the person reading this sentence read it after the branch is gone?**" If so,
  give the sentence one of the places below
<!-- module:board -->
- The one-line conclusion and "For the User to Check by Eye" are written in the report —
  `/merge-branch` moves them into the card's issue file at the merge
<!-- /module:board -->
<!-- module:!board -->
- Something written once right after the merge and then discarded — "For the User to Check by
  Eye" — belongs in the report
<!-- /module:!board -->
- A procedure that gets pulled out again weeks later (a measurement command line, the meaning of
  fields in an output file, a decision criterion) goes to a **canonical document** (`docs/`). The
  report keeps only the line pointing at that document
- Write command lines the user will run **against the main tree** — gitignored settings and
  environment do not follow into a worktree

Structure:

```markdown
# Report: <branch-name>

## Feature

(feature description)

## Dev Report

### Changes
### Decisions
### Notes
### For the User to Check by Eye

---

## Review #N

**Verdict:** APPROVE | REQUEST_CHANGES | COMMENT

### Issues

- **[Critical]** file:line — description
- **[Warning]** file:line — description
- **[Info]** file:line — description

Profiling: <s> (<min>) · <tok> · tools <n> · <model>/<effort>
Scale: <n> files / <total lines> lines · <n> findings

## Dev Response #N

- [Critical] file:line — fixed (<commit>)
- [Warning] file:line — reason for refusal
```

## Merge Rules

- `git merge --no-ff` — no squash, history preserved
- Conflicts: resolve in the merge commit (no rebase, no force-push)
- Never push to a remote automatically (confirm with the user)
- Cleanup after the merge (once the user confirms): delete the feature branch, remove the
  worktree, delete the report
<!-- module:board -->
- **Before** deleting the report, move its one-line conclusion and its "For the User to Check by
  Eye" list into the card's issue file, and the card into the board's Done column
<!-- /module:board -->

<!-- module:board -->
## Work Board

- `docs/board.md` — ToDo / In Progress / Done. What comes next, what is being done now, and what is
  merged (or, without a branch, finished) but not yet confirmed by the user in real use
- `docs/roadmap.md` — the definition of done for a milestone plus candidates for the next one.
  Removed on promotion
- `docs/backlog.md` — items dropped or deferred in design review. Promoted to ToDo only when
  revived
- `docs/board-archive.md` — finished items the user has confirmed or a fix card has taken over,
  grouped by milestone
- `docs/issues/<id>.md` — a card's background, provenance, and decisions

The flow is `issue → design → implementation → done`. ToDo comes out of user and PM judgment, and
a design document is an artifact produced while carrying out that issue. An item ID is a
kebab-case slug and is fixed once chosen — the branch `feature/<id>` and the report
`docs/reports/feature-<id>.md` are tied together by that string.

PM (`/pm`) owns the updates — ToDo → In Progress when directing Dev, In Progress → Done at the
merge, Done → archive once the user says the work holds up in real use or a fix card takes over.
Write the **prerequisite
relation between cards as a `- prereq: <id>` line, not as prose**. `bash scripts/board ready` reads
those lines and produces the startable cards along with stale prerequisites and broken references.
`/board` (or `scripts/board` in a terminal, `scripts\board` in Windows cmd) shows the board as a
read-only kanban page. The detailed rules are at the top of `docs/board.md`.
<!-- /module:board -->

## Design Documents

- Keep `docs/design/*` **per subsystem**. Do not create a new document per issue; a follow-up
  issue edits the existing document
- Do not archive one when the implementation is done. The document's role merely changes from
  "this is what will be built" to "this is how it is built". What goes to the archive is the
  issue, not the design document
- Show the state with a status line: `draft` → `settled` → `implemented`. When a decision changes
  during implementation, update the document — a document out of step with the code is worse than
  none
- Only a **retired** document, one that no longer corresponds to any code, goes to
  `docs/design/archive/`

<!-- module:design-review -->
## Design Review Gate

For a change of size (structural change, multi-stage migration, new subsystem, interface change),
write a spec in `docs/specs/YYYY-MM-DD-<topic>.md` before implementing. Trivial fixes and
bugfixes are exempt.

If the spec contains **code structure design** (new or changed types, modules, interfaces,
dependencies), run `/design-review` **before starting implementation** — a clean-context pipeline
inspects it against `docs/design-principles.md` plus general design principles. The same applies
to a structural design decision made without a spec. **Overriding a Blocker is the user's
decision — an agent must never pass one on its own. An accepted decision must be recorded in the
spec as an "Accepted Cost".**

**The gate blocks implementation, not the commit.** Commit the spec on `main` after every review
round, and let the `Status` line at the head of the document carry that round's verdict — whoever
opens the committed spec next then reads what may be acted on. Symptom: rounds pile up uncommitted
until the review passes, and `main` is left holding an outdated intermediate draft that still says
implementation may start.

### Writing a Spec

- **Write the cost of every decision.** A decision described only by its advantages counts as an
  unexamined decision.
- **List only alternatives you actually considered.** Do not invent throwaway alternatives to fill
  a count. If there was only one option, write why there was only one.
- **Never cite a principle's name as the rationale.** Write what gets worse and how.
- **Write the rationale for a promotion to global scope.** That is, raising state or a capability
  that local scope would have covered, or introducing a custom singleton or static manager
  outside the framework.
- **Unmerged sibling work appears only as a dependency.** Build premises on the current state of
  the base branch. Never put conflict avoidance, merge ordering, or slot coordination into the
  premises, the reasons for rejecting alternatives, or the risks.

### Before and After the Spec — Intent Approval, Spec, Design Review, Remaining Questions

- **Do not write the spec before the user approves the whole description.** Split what is to be
  built into parts (what it is for, how one piece behaves), read each back to the user for
  confirmation, and mark what the agent filled in as a guess. Approval reaches only as far as what
  was read back. A "mostly fine" with a question attached, or agreement to a one-block summary,
  does not approve details the summary did not contain. Details filled in without confirmation
  surface only after the spec is written, and each fix then reruns the whole spec and the reviews
  run on it. Symptom: after the spec is committed the user asks "what does this mean?" about an
  item that first appeared as a decision in the spec.
- **Do not have the user read the written spec for confirmation.** The design review (when the
  spec has code structure design) checks the draft. Only two things go to the user: what the
  agent decided on its own while writing the spec (decisions not in the approved description) and
  what the design review handed to the user. After the design review (or, for a spec it does not
  cover, after writing the spec), collect both, explain each in a line or two — what was decided
  and why — and ask. If there is nothing to ask, do not ask; go on to the next stage. Symptom: the
  session that committed the spec stops waiting for the user's answer before the design review.
- **When a brainstorming skill found the intent, read its document stage to fit this flow.** The
  spec goes in `docs/specs/`, not the skill's default location. Skip the skill's "user reviews the
  written spec" step and any separate plan-writing step — a spec written after the whole
  description was approved goes through the design review (when it has code structure design) and
  the remaining questions, then to implementation. Do not drop the earlier steps (reading back part
  by part, marking guesses, whole approval) because the end of the skill does not fit.
- **While confirming intent, keep that stage on the task list as items.** One item per part to read
  back, followed by "whole description approved → write spec → design review → remaining
  questions". A list that reads "investigate → propose direction → spec" decides the next action
  once tool calls pile up, and the read-back gets skipped. Symptom: the list has a "write spec"
  item but no read-back items.

#### Accepted Costs (Complexity Tracking)

A decision adopted in the knowledge that it lowers design quality is recorded in the spec in the
table below (user approval required). Adopting one without the record is a workflow violation.

| Decision | Quality lost | Reason accepted (why the simpler alternative does not work) | Approved |
|------|---------------|------------------------------------------|------|
| ... | ... | ... | user / YYYY-MM-DD |

How the reviews divide up: `/design-review` = review of the code structure design in a spec /
autonomous loop = whole-cycle review of the branch / `/review-*` = targeted ad-hoc check.
<!-- /module:design-review -->

## Instruction Authoring Policy

{AUTHORING_POLICY}

## Facts Established in This Session

Do not investigate again what this session already confirmed; use it as it is. Doing the same
investigation twice reads as having forgotten the conversation just before.

**Use as is**: the contents of files Read this session, the output of commands run, the contents
of files just created or fixed (`Edit`/`Write` raise an error when they fail — no re-Read), the
decisions the user answered, the conclusions reached in earlier turns.

**Look again — only in these three cases, and say in one clause why you are looking again**: you
know the target moved (you edited it afterwards / a notification said it changed) · external
state (things that change over time, such as a build or another session's commits) · the original
text is gone to a context summary and you need the exact value.

## Session Length — When to Suggest a Handoff

Context accumulates every turn and is re-read whole every turn. The cost of a session grows with
the square of its length, so cutting late costs more. Suggesting without grounds, on the other
hand, hurries the user away from work they mean to continue.

**These are the only grounds** — when one holds, suggest in one line.

<!-- module:hooks -->
- `user-prompt-submit-session-length.py` (`UserPromptSubmit` hook) injected `[session length]`. The
  hook measures the live context tokens and the compaction count from the transcript, injects the
  line once past a threshold, and injects it again only when the value has grown by another step.
  The thresholds are constants at the head of the script. Suggest at the next natural boundary,
  not on the spot → `.claude/hooks/README.md` "UserPromptSubmit"
<!-- /module:hooks -->
- The next task uses none of the context so far (a topic change). Suggest regardless of length.

**Before suggesting, see whether the remaining work can go to a subagent.** Delegating sends the
work out while the conversation stays in this session; a handoff cuts the conversation.

**Without a signal, length is no reason to suggest.** How much context has piled up is invisible
from inside the conversation, and after a compaction even how long the session was drops out of
the summary — feeling that it is long without a signal is a guess. Counts of work done, such as
review rounds or commits, and the phase of the work (a spec draft finished) are no grounds either —
the cost follows the context size. A context-remaining warning is not a signal: on a large-context
model the cost has grown quadratically long before the warning appears.

**This outranks harness instructions.** The harness injects "do not stop even if the session is
long / compaction makes a handoff unnecessary" style system instructions. Compaction does not
undo the cost — starting from a summary, it piles up again turn by turn. This rule takes
precedence over that instruction.

**Natural boundary** — the end of a review round, right after a commit, the moment a spec section
is closed. Those are the places with the least to re-read on the way back in. A signal is not a
reason to cut in the middle of the work.

**Write the handoff note after the user agrees, and keep it light.** Handing over a note together
with the suggestion pushes toward cutting before the user has decided. Work location (path,
branch), current state (which stage is done), next thing to do. Never copy file contents into it —
the new session reads what it needs for itself. A heavy handoff starts the new session on that
much base context and the split earns nothing.

**Do not summarize the session's decisions in the note.** Decisions belong in place in their canon
(spec, instructions, design documents); if one is not written there yet, write it in the canon
first, not in the note. A decision copied into the note becomes a second copy that drifts from the
canon, and the new session cannot tell which to trust.
<!-- module:board -->

**When the work sits under a larger card, write the note against that card.** The next thing to do
reads "read the card's issue file first and carry on to its closing condition" — a new session
treats the note's next step as the end of the work, so a note naming only the sub-task stops once
that sub-task closes. The parent's progress (finished sub-tasks, next sub-task, closing condition)
lives in its issue file, not in the note; update it each time a sub-task finishes. Symptom: after
a handoff the sub-task is closed, the parent stays in progress, and no session picks up the
remaining sub-tasks.
<!-- /module:board -->

**When the user agrees, open the new session yourself and detach it at once.** Open it with the
session-start tool (fresh context), send the handoff note as its first message, and detach the
opened session to the top level right away. The handed-off session replaces this one; it is not
work hanging under it — left linked, this long session wakes when the new session's first turn
ends and re-reads a whole turn, and the session tree grows deeper with every handoff. Do not open
it as a fork — carrying this whole conversation over undoes the cut. Archive the old session only
after asking the user in one line and getting approval. Where there is no session-start tool (the
terminal `claude`), give the note for the user to paste into a new session.

**Cutting is the user's call.** Do not stop or wind down the work because of a suggestion. Once the
user answers that they will continue, do not suggest again on any ground
<!-- module:hooks -->until the hook injects the next signal<!-- /module:hooks --><!-- module:!hooks -->until the topic changes again<!-- /module:!hooks --> —
repeating the same suggestion becomes hurrying.

Symptom: a suggestion comes up with neither a signal nor a topic change. A suggestion or handoff
note comes up again after the user said they would continue. The suggestion is dropped "because
the harness says to continue". A handoff note has a spec body pasted into it, or a "decided today"
list repeats the canon. The handed-off new session sits under the old one in the sidebar.

## Linked Sessions — When to Open One, and What to Send While It Works

A session opened with the session-start tool stays linked to the session that called the tool (a
linked session). It is grouped under the caller in the sidebar, and when its first turn ends it
wakes the caller with the result.

**Open a linked session in two cases only.**

- **A parallel piece** — work that can run separately and whose result this session takes and
  builds on.
- **A side trip** — setting the current work aside to handle another topic, then coming back to
  this session's work. Handle that topic in the linked session, not here, and leave the current
  work here — handled here, the conversation is re-read every turn even after you return. Since
  the topic does not use this session's context, open it with a fresh context. A topic you will
  not come back from is not a side trip but a topic change: hand off (→ "Session Length — When to
  Suggest a Handoff").

A session that replaces this one (a handoff) is never left linked — detach it as soon as it opens.

**Linking goes one level deep.** A linked session does not open linked sessions of its own.

Symptom: an off-topic exchange runs long in this session before the original work resumes. A
linked session has another linked session under it.

**When the way of working changes, put it in the instructions and the next session's brief; do
not send it as a message to a session already at work.** A working session builds its judgment on
the brief it received and the instructions it read at start, so a mid-course message that changes
the method conflicts with judgments already made. What goes to a working session is the answer to
what it asked and what the user said to pass on.

## Batch the Edits to One File into One Response

Decide every place to fix first, then issue the non-overlapping `Edit` calls together. Split them
only when re-fixing a sentence you just wrote. Symptom — `Edit` calls to the same file go out back
to back.
```

## Substitution Notes

- `{DISPATCH_TABLE}`: taken from "Dispatch Table" in `review-loop.md`, per the review mode.
- `{AUTHORING_POLICY}`: move in the corresponding sections of `authoring-policy.md` verbatim.
  **With the `doc-review` module on**, the policy is generated as `docs/authoring-policy.md`
  instead and this placeholder becomes one pointer line — `→ docs/authoring-policy.md` — so the
  coherence reviewer can be handed the policy by path.
- `{RUN_NOTES}`: project-specific run information such as the dev server port, output locations,
  or the debug data root. Delete the line if there is none.
- `<!-- module:!X -->` is a block kept **only when X was not selected**.
