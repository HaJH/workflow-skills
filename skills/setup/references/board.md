# Work Board (module: board)

For a local project with no external issue tracker. Files generated:

| File | Contents |
|---|---|
| `docs/board.md` | Rules + In Progress / Done / ToDo |
| `docs/roadmap.md` | Milestone ladder + candidates |
| `docs/backlog.md` | Dropped and deferred |
| `docs/board-archive.md` | Finished and confirmed (by milestone) |
| `docs/issues/` | Empty directory (`.gitkeep`) |
| `scripts/board` | Copy of `scripts/board` — the short entry point (macOS/Linux/Git Bash). Keep it executable: `chmod +x`, and record the bit with `git update-index --chmod=+x scripts/board` |
| `scripts/board.cmd` | Copy of `scripts/board.cmd` — the same entry point for Windows cmd. CRLF line endings, ASCII only |
| `scripts/board.py` | Copy of `scripts/board.py`, with the `{PROJECT_PATH}` default substituted |
| `scripts/board-view.html` | Copy of `scripts/board-view.html` — the page template `board.py view` fills |
| `scripts/tests/test_board.py` | Copy of `scripts/board-tests/test_board.py` |
| `scripts/run-python.sh` | Copy of `scripts/run-python.sh`. Shared with the `hooks` module — generate it once when either module is on |
| `.claude/commands/board.md` | `commands.md` "/board" |

**Prerequisite**: `scripts/board.py` runs on `bash` and Python 3.9 or newer, through the shared
`scripts/run-python.sh` launcher; on Windows, `scripts\board.cmd` takes `bash` from Git for
Windows. If either is missing, say so at setup and leave the `board` module off — `/pm` and
`/merge-branch` would call a script that cannot run.

**A board in the project's language**: the words `board.py` reads — the prerequisite and adjacent
labels, the status line's branch/report/started/done words, the `(detail: issues/)` suffix — come from
its `VOCABULARY` table, one row per language, and every row is read on every board. When the
project writes its documents in another language, write those words from that language's row. A
language with no row gets one in the same change that writes the board in it; never edit an
existing row. Symptom: `scripts/board ready` reports no blocked cards on a board whose cards carry
prerequisite lines.

## Re-Applying to a Project That Already Has a Board

The board documents are the project's progress — cards, archive entries, milestones, issue
files. Re-applying the workflow never regenerates them.

1. **Make a restore point.** Commit any uncommitted change under `docs/` and tell the user that
   commit — it is where to go back to. Record the first line the current board script prints
   (`board: ToDo … / In Progress … / archived …`): `bash scripts/board ready`, or
   `bash scripts/board-ready.sh` in a project set up before it
2. **Generate only what is missing.** An existing `docs/board.md`, `docs/roadmap.md`,
   `docs/backlog.md`, `docs/board-archive.md`, or file under `docs/issues/` stays as it is. The
   scripts and the `/board` command are replaced from the templates
3. **Migrate rule text line by line**, through the migrations below and only those lines. Never
   copy a template block over a board document — the cards, archive entries, milestones, and the
   project's area table live in the same files
4. **Verify.** `bash scripts/board ready` prints the ToDo, In Progress, and archived counts of the
   recorded line again, and `git diff -- docs/` changes only the lines a migration names. Symptom
   of a regenerated board: the ToDo or archived count drops, or the diff deletes card lines

Migrations — apply each one whose condition holds:

- **The project has `scripts/board-ready.sh`**: delete it. In `docs/board.md`, rewrite the
  sentences that name it to this template's wording — the prerequisite bullet under "Rules" and
  the paragraph after the "Prerequisite Line" example
- **`docs/board.md` has no `## Done` section**: add `## Done` holding `(none)` between
  `## In Progress` and `## ToDo`. Rewrite to this template's wording: the opening paragraph; under
  "Rules", the card bullet and the status-line bullet; the "Who moves a card" rows from
  In Progress → Done down, and the paragraph after the table; the first bullet under the
  "Prerequisite Line" example and the paragraph closing that section; the "Format" example. In
  `docs/board-archive.md`, rewrite the paragraph under the title that sends the report's
  conclusion here. Existing cards keep their text — a card without a title still reads

When a template change alters text inside the board documents, add its migration here in the same
change. Symptom: a re-applied project's board rules name a script or step that no longer exists.

## docs/board.md

```markdown
# Board

A lightweight kanban board holding what comes next (ToDo), what is being done now (In Progress),
and what is merged (or, for a card without a branch, finished) but not yet confirmed by the user in
real use (Done). Confirmed items go to `board-archive.md`.

## Issues Come First

The flow is `issue → design → implementation → done`. A design document (`docs/design/*`) is an
**artifact** produced while carrying out an issue, not the source of one.

A ToDo item comes into being like this:

- **User and PM judgment** — what you want done, what must be done. The main source
- **Follow-up work split off a prerequisite issue** — what implementation revealed was left
- **`docs/roadmap.md`** — candidates for the next milestone. Promoted when started (remove what
  was promoted from roadmap.md)
- **`docs/backlog.md`** — the pile of dropped and deferred items. Promote only when reviving
  something, and remove what was promoted from backlog.md

## Rules

- An item ID is a kebab-case slug and is **fixed once chosen**. The branch `feature/<id>` and the
  report `docs/reports/feature-<id>.md` are tied together by that string
- **A card is one line** — `` **`<id>`** · title — summary ``: a short name, then one clause.
  Only the ` · ` right after the id marks a title, because summaries already contain ` — `. A new
  card gets a title; an existing card written `` **`<id>`** — summary `` still reads.
  Background, provenance, decisions, and constraints go in `docs/issues/<id>.md`. Create that file
  only once there is detail, and when it exists put `(detail: issues/)` at the end of the card.
  Pass this file to Dev when the work starts. When the card moves to Done, the file takes the
  one-line conclusion and the report's "For the User to Check by Eye" list (creating the file if
  there is none) — the report is deleted at the merge. When the card goes to the archive, move the
  key conclusions into the archive entry and the design document, then delete the file
- **Write a prerequisite as a line, not as prose** — one sub-bullet, only on a blocked card:
  `` - prereq: `<id>` `` (comma-separated if several). The format must be the single one for
  `scripts/board.py` to read it
- Attach the status line (branch, report, start date) only when promoting to In Progress, as one
  sub-bullet under the card (its shape is in "Format"). On the move to Done it becomes
  `started <date> · done <date>` — the branch and the report are gone after the merge, and the
  archive entry is dated from these two
- Never rewrite an item's text when moving it. Update only the status fields
- Group headers carry the fixed category name only — never hang a per-issue comment or an
  ordering instruction on a header
- Documents are committed directly on main. **Once you fix one, commit it right there** — the
  file is shared by several sessions, and leaving the change uncommitted collides with another
  session's edits

Who moves a card:

| Move | Who | When |
|---|---|---|
| (new) → ToDo | PM or the user | when something to do comes up |
| roadmap → ToDo | PM | when starting the next milestone |
| backlog → ToDo | PM | when reviving a dropped item |
| ToDo → In Progress | PM | when directing Dev to the work |
| In Progress → Done | PM | when the work is finished — for a branch, the `/merge-branch` board step |
| Done → archive | PM | when the user says the work holds up in real use, or when a fix card is filed for it |

A card waits in Done without anyone asking: the user's check happens in real use, never as a
request (`docs/workflow.md` "User Verification Happens After Merge"). When a problem shows up, the
fix card goes to ToDo and the original goes to the archive, its archive entry naming the fix card
— the fix card carries on from there, and its issue file takes what is still unchecked. Symptom: a
PM summary asks the user to go through the Done column.

## Tracks — Fixed Groups Within ToDo

ToDo is split into groups. **A group is a classification, not a plan and not a lock** — do not
write out an empty group.

- **Main line (v\<n\>)** — the axis toward the current milestone's definition of done, in order
  from the top. **The reason it is sequential is a prerequisite relation between cards, not that
  they touch the same area**
- **\<area\>** — the remaining cards. Areas are a fixed list based on code domains, and additions
  or changes go through this table only:

| Area | Scope |
|---|---|
| {AREA_1} | {AREA_1_SCOPE} |
| Docs | `docs/` only — no code change |

Placement: a new card goes by **which code area it touches**. Within a group, higher is higher
priority. If a card is urgent across groups, put a `⚑` on that one card alone.

Starting work — **never hold a card because it is in the same area**:

- Two branches touching the same file is normal. On conflict, resolve in the merge commit
- There are only two reasons to serialize: a **prerequisite relation** (B uses A's output — write
  it as a prereq line) · **duplicated design** (two cards raise new structure in the same
  subsystem — send one first or split the scope)
- If neither holds, start it even where they overlap

## Prerequisite Line

```markdown
- **`feature-b`** — feature B (detail: issues/)
  - prereq: `feature-a`
```

- **Write only unresolved blocking.** The PM who moves the target to Done deletes that line — for
  a merged card, in the `/merge-branch` board step. Left in place, the card reads as blocked
  forever
- A provenance note ("split out of `x`") is not a prerequisite — it is history and blocks nothing
- An "order check" is not one either — to mark it at all, use `` - adjacent: `<id>` ``

`bash scripts/board ready` reads these lines and produces three things — **startable cards** ·
**stale prerequisites** (the target is already in Done or the archive) · **broken references** (the
target matches no card anywhere).

## Format

```markdown
## In Progress

- **`scan-pipeline`** · Library scan — scan the library folder → register in the DB (detail: issues/)
  - branch `feature/scan-pipeline` · report `docs/reports/feature-scan-pipeline.md` · started YYYY-MM-DD

## Done

- **`tag-editor`** · Tag editor — edit a work's tags in place (detail: issues/)
  - started YYYY-MM-DD · done YYYY-MM-DD

## ToDo

### Main Line (v0)

- **`library-ui`** · Library screen — implement the v0 screen

### {AREA_1}

- ⚑ **`sleep-timer`** — sleep timer
```

---

## In Progress

(none)

## Done

(none)

## ToDo

### Main Line (v0)

(none)
```

## docs/roadmap.md

```markdown
# Roadmap

Development direction by milestone. How the roles divide:

- `board.md` — what is being done now and what comes next. **The truth at card level is always
  the board**
- This document — the milestone ladder (definition of done, order) and each milestone's candidate
  items. Once a candidate is promoted to the board's ToDo, remove it here
- `backlog.md` — the record of what was dropped in design review or deferred. Not a roadmap

## Milestones

### v0 — {V0_TITLE}

Definition of done: {V0_DEFINITION}

Candidates:

- (none)
```

## docs/backlog.md

```markdown
# Backlog

A single list of **items dropped in design review or pushed to a lower priority**. The date is
the date of the decision.

This is a record of what was left out, not a work list. Promote a dropped item to ToDo in
`board.md` only when reviving it, and remove a promoted item from this document. `roadmap.md`
owns the direction of the next milestone.

## Deferred Features

- (none)
```

## docs/board-archive.md

```markdown
# Board Archive

A record of completed board items. Grouped by milestone, with the newest milestone at the top.

`/merge-branch` deletes the report after the merge, so **before deleting it** the one-line
conclusion moves into the card's issue file, and from there into the entry here when the card
leaves Done. Otherwise "what did this work conclude?" disappears along with the merge.

## Format

```markdown
## v0

- **`scan-pipeline`** (YYYY-MM-DD ~ MM-DD) — scan the library folder → register in the DB
  - WalkDir-based, settled on regex matching over the code
```

---

## v0

(none)
```

## docs/issues/<id>.md Format (Not Generated — Referenced From board.md)

```markdown
# <id>

<one-line background>

## User Request (Verbatim)

> …

## What Is Missing Now

## What Must Be Decided

1. …

## Adjacent

- **`<other-id>`** — why it is related

## Conclusion

<one line, written when the card moves to Done>

## For the User to Check by Eye

- <copied from the report when the card moves to Done>
```
