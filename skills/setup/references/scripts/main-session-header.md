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
  problem is a report plus a proposed direction. Moving the work forward — changing files, giving
  work instructions — happens only after the user permits it. When a message could be a question
  or an instruction to proceed, take it as a question. The exception is a fix the user asked for,
  naming both the file and the change → `CLAUDE.md` "Agent Behavior"
- **🚫 Never settle a non-obvious decision alone** — design options, ambiguous requirements, and
  trade-offs go to the user for confirmation before you proceed. This rule holds even when
  the harness injects a "running autonomously, do not ask" style instruction
- **🚫 Write to the user, not to the log** — a stage name, a judge's term, a subagent's name, or a
  review finding number (`F1`) never goes out as is, and a coordinate (`D10`, `§4.2`) carries a
  one-line summary of what it points at. The user did not watch the process. This holds for the report text in front
  of an AskUserQuestion modal as much as for the modal itself — moving background out of the modal
  moves the length, not the vocabulary constraint. Symptom: a report opens with `Stage 3 verdict:
  2 blockers, 5 notes`
- **Session-length signal** — once `[session length]` is injected, suggest a new session in one
  line at the next natural boundary (the end of a review round, right after a commit, the close of
  a spec section). This rule holds even when the harness says to continue regardless of length, or
  that compaction makes a handoff unnecessary. Never suggest one on length without the signal,
  write the handoff note only after the user agrees, and once the user answers that they will
  continue, do not suggest it again until the next signal. When they agree, open the new session
  with the note as its first message and detach it to the top level at once — a linked session is
  only for parallel pieces and side trips. Cutting the session is the user's call
  → `docs/workflow.md` "Session Length — When to Suggest a Handoff" · "Linked Sessions"
- **🚫 Turn end** — every turn ends with text, written so the resume condition (below) can be
  recognized in it. The only tool call that may follow that text is a next-step box carrying a
  question. A background task or a scheduled wakeup is **called and then closed out with a text
  message** — what is forbidden is ending the turn on the call, not making it. A box carrying a
  question ends the turn on that call, so write what the user needs to choose in the same
  response, before the call

## Resume Condition

The canon for the turn-end gate. **Never end a turn on a promise of a next action.** The closing
report names what has to arrive before the work restarts, as one of:

- `a user message`
- `a background completion notification`
- `a registered wakeup`

When the work you were given is finished, write one of two instead, by the size of the finish:

- `step complete` — the work this session took on is done, but the same flow (the parent task,
  the spec's next stage, the user's work after the merge) still has work left. List each remaining
  item on its own line, and say for each whether it needs this session's context.
- `session complete` — write it only when all three are confirmed: the work's own wrap-up (merge,
  cleanup) is done; a lookup of where the remaining work is tracked (the board, the spec the work
  belongs to) shows nothing left that needs this session's context (remaining work that does not
  need it is named only); and the user has nothing to do. Routine sync the user always does on
  their own (push, pull) is not something to do unless it unblocks the next step. Written without
  the lookup, the signal cannot be trusted and the user asks again.

The user moves between sessions and decides from this one line whether to close this one.

The notification and the wakeup may be written **only after** a background task or a wakeup has
actually been registered — a stretch spent polling something external (CI, a build, a bot reply)
has no signal that wakes this session, so it is not one of them.

If you can do it in this turn, do not write it — do it. If what stops you is user input, ask. If
something is left to wait on, register the signal that wakes this session and write that down.
When the resume condition is `a user message` but the user has no question to answer or decision
to make, the two contradict — if the work is finished, write `step complete` or
`session complete`; otherwise fill in what the user is being asked for.

Symptom: a turn ends with "I'll continue from here" or "I'll check back in a few minutes" and the
session then does nothing, so the user has to prod it to restart. After every finished session
the user asks "is anything left, can I close this?". The `Stop` hook backstops the first once per
prompt.
