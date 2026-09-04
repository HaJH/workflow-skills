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

The report is gitignored and `/merge-branch` deletes it. Write something here that must survive
the merge and **it is erased, with no way to recover it from history either.**

- Something written once right after the merge and then discarded — "For the User to Check by
  Eye" — belongs in the report
- A procedure that gets pulled out again weeks later (a measurement command line, the meaning of
  fields in an output file, a decision criterion) goes to a **canonical document** (`docs/`). The
  report keeps only the line pointing at that document
- The test is "**does the person reading this sentence read it after the branch is gone?**"
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
- **Before** deleting the report, move a one-line conclusion into `docs/board-archive.md`
<!-- /module:board -->

<!-- module:board -->
## Work Board

- `docs/board.md` — In Progress / ToDo. Only what is being done now and what comes next
- `docs/roadmap.md` — the definition of done for a milestone plus candidates for the next one.
  Removed on promotion
- `docs/backlog.md` — items dropped or deferred in design review. Promoted to ToDo only when
  revived
- `docs/board-archive.md` — completed items, grouped by milestone
- `docs/issues/<id>.md` — a card's background, provenance, and decisions

The flow is `issue → design → implementation → done`. ToDo comes out of user and PM judgment, and
a design document is an artifact produced while carrying out that issue. An item ID is a
kebab-case slug and is fixed once chosen — the branch `feature/<id>` and the report
`docs/reports/feature-<id>.md` are tied together by that string.

PM (`/pm`) owns the updates. Write the **prerequisite relation between cards as a `- prereq:
<id>` line, not as prose**. `bash scripts/board-ready.sh` reads those lines and produces the
startable cards along with stale prerequisites and broken references. The detailed rules are at
the top of `docs/board.md`.
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
the square of its length, so cutting late costs more.

**Signals to suggest a handoff at the next natural boundary** — any one of them is enough.

- Two or more design review rounds have run.
- Two or more commits have piled up in this session.
- A context-remaining warning has appeared.
<!-- module:hooks -->
- A `[session length]` line has been injected. That one is measured from the transcript rather
  than remembered, because a compaction drops the commit count from the summary and a
  large-context model never reaches the context-remaining warning at all.
<!-- /module:hooks -->

**Natural boundary** — the end of a review round, right after a commit, the moment a spec section
is closed. Those are the places with the least to re-read on the way back in. A signal is not a
reason to cut in the middle of the work.

**Never judge by the phase alone.** Finishing a spec draft is not itself a reason to hand off —
work that converges in one more round is cheaper carried straight through.

**Keep the handoff note light.** Work location (path, branch), current state, next thing to do.
Never copy file contents into it — the new session reads what it needs for itself. A heavy handoff
starts the new session on that much base context and the split earns nothing.

**Cutting is the user's call** — only suggest, and never act as though the session ended without
the user's answer.

Symptom: one session carries a spec draft, several review rounds, the implementation, and the
merge all together. A handoff note has the body of a spec pasted into it.

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
