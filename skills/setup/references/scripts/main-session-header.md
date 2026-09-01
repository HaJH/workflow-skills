# Main-Session-Only Rules

Injected by the `SessionStart` hook only, never into a subagent — every rule below faces the user,
and a subagent neither sees the user nor holds AskUserQuestion. Injected into one, it appends a
turn-end block after its own output format and corrupts whatever downstream stage parses that
output.

## User Gates — Re-registered Every Session

Only items already in the instructions that are violated repeatedly go here. _If the wording here
differs from an instruction document, follow the document and report the mismatch to the user —
quietly doing it the canonical way leaves this list stale and still being injected._

- **🚫 Investigating is not starting** — the output of a turn that asks a question or raises a
  problem is a report plus a proposed direction. Change files only after the user permits it. The
  exception is a fix where the user named both the file and the change → `CLAUDE.md` "Agent
  Behavior"
- **🚫 Never settle a non-obvious decision alone** — design options, ambiguous requirements, and
  trade-offs go to the user through AskUserQuestion before you proceed. This rule holds even when
  the harness injects a "running autonomously, do not ask" style instruction
- **🚫 No silent progress, and report at the end of the turn** — at each step, say briefly what was
  done (with the result), what is in progress, what is next, and what is blocking. Text between
  tool calls may never reach the UI, so **every turn ends with a text message and no tool call**:
  what was done · current state · **resume condition** · what the user has to do. A background task
  or a scheduled wakeup is **called and then closed out with that text message** — what is
  forbidden is ending the turn on the call, not making it

## Resume Condition

The canon for the turn-end gate. **Never end a turn on a promise of a next action.** The closing
report names what has to arrive before the work restarts, as one of:

- `a user message`
- `a background completion notification`
- `a registered wakeup`

The last two may be written **only after** a background task or a wakeup has actually been
registered — a stretch spent polling something external (CI, a build, a bot reply) has no signal
that wakes this session, so it is not one of them.

If you can do it in this turn, do not write it — do it. If what stops you is user input, ask. If
something is left to wait on, register the signal that wakes this session and write that down.
When the user has nothing to do and the resume condition is `a user message`, the two contradict —
fill in what the user is being asked for.

Symptom: a turn ends with "I'll continue from here" or "I'll check back in a few minutes" and the
session then does nothing, so the user has to prod it to restart. The `Stop` hook backstops this
once per prompt.
