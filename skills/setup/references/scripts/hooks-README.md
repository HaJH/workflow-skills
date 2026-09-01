# Claude Code Hooks

## SessionStart / SubagentStart — Automatic Project Context Load

`session-start.ps1` injects context as `additionalContext`. It is layered:

- **Always (main + sub)**: `session-start-header.md` — repeat-violation traps + index of detailed
  documents
- **Main session only — user gates**: `main-session-header.md` — permission to start,
  AskUserQuestion, turn-end reporting, resume condition. A subagent neither sees the user nor
  holds the question tool, so it cannot run these rules. Injected into one, it appends a turn-end
  block after that agent's own output format and corrupts whatever downstream stage parses the
  output
- **Main session only, additionally**: `docs/workflow.md` — excluded for subagents, which do no
  git or report workflow
- **On demand (not injected)**: the remaining documents the header index points at. Read them
  when needed

To change the document list, edit `$files` in `session-start.ps1`.

**Why SubagentStart is registered too**: a subagent does not inherit the parent session's
CLAUDE.md, settings hooks, or SessionStart context. Registering the same script is what makes
main and sub behave alike. `additionalContext` goes into the user context, so it can be dropped
when the context is compacted.

## PreToolUse — Edit/Write Gate + Reminder

The matcher is `Edit|Write|Read|Skill`. It has two roles.

- **Observation (Read/Skill)**: records which documents were Read and which skills were loaded in
  the session state file, and passes
- **Gate + reminder (Edit/Write)**: matches the file path against the `file-pattern-map.json`
  rules. If a matched rule has `requires` and they are unfulfilled, **blocks the edit with
  `permissionDecision: deny`** and says what to do. If they are fulfilled, injects the rule
  message as `additionalContext`

**Reading through the shell does not count** — opening it with `cat` or `sed` is invisible to the
hook. Only the `Read` tool and the `Skill` tool.

### Path Normalization — Worktrees

A file path is normalized to a project-relative path before matching. The worktree convention
(`<parent>/<Repo>-worktrees/<folder>/`) is recognized first, so an edit from inside a worktree
matches exactly as it does in the main tree. With plain prefix matching,
`<Repo>-worktrees/...` would match `<Repo>`, the relative path would be cut, and every rule would
miss.

### Rule Schema

```json
{
  "id": "unique ID",
  "patterns": ["*.rs", "Source/Foo/*.cpp"],
  "scopePath": ["crates/"],
  "excludePath": ["vendor/"],
  "requires": {
    "reads": ["CLAUDE.md"],
    "skills": ["rust-guide"]
  },
  "message": "reminder message -- a pointer to the canonical path"
}
```

| Field | Meaning |
|---|---|
| `id` | The rule's unique identifier. Used to track the once-per-session notification |
| `patterns` | File name or relative path wildcards (PowerShell `-like`). `**` unsupported — constrain directories with `scopePath` |
| `scopePath` | (optional) The relative path must start with one of these prefixes to match |
| `excludePath` | (optional) Excluded when the relative path contains one of these substrings |
| `requires` | (optional) What must be fulfilled before editing. `reads` are project-relative paths, `skills` are skill names. Unfulfilled, the edit is **blocked** |
| `message` | The reminder injected once past the gate. **Never duplicate a rule summary** — it goes stale when the canon changes |

### Matching Behavior

- Several rules can match one file at once → all of them notify. `requires` are unioned
- The notification is **once per rule id per session**. The gate checks **on every edit** until it
  is fulfilled
- State files: `$env:TEMP\claude-code-hook-state\fired-rules-{session_id}.txt` ·
  `requires-done-{session_id}.txt`
- exit 0 on exceptions — a broken hook does not block the work

### requires Promotion Criteria

A new rule starts as a `message`, and is promoted to `requires` only when the instructions
declare that document "required / read fully before proceeding". **A requirement that does not
belong at edit time** (a pre-commit or pre-merge gate) is never hooked as `requires` — it blocks
the writing itself.

**Every `reads` path and `skills` name must exist.** With a typo, that entry can never be
satisfied and **nobody can edit that file.** After adding a rule, always confirm with
"Verification".

### Verification

```powershell
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"<project absolute path>/<a file the rule matches>"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1
```

On a match with requirements unfulfilled, `permissionDecision: deny` JSON. Re-run once fulfilled,
`additionalContext` JSON. With no match, empty output. Reset the state:

```powershell
Remove-Item "$env:TEMP\claude-code-hook-state\*-test.txt" -ErrorAction SilentlyContinue
```

## Stop — Turn-End Gate

`stop-turn-end-gate.py` runs on every turn end, with no matcher. When the last assistant message
**promises a next action but writes no resume condition**, it exits 2 to hold the turn open and
returns in stderr what to write instead. The canon for the rule is
`main-session-header.md` "Resume Condition".

**It catches only a promise phrase together with a missing resume condition.** A line naming one
of `a user message` / `a background completion notification` / `a registered wakeup` (the last two
only after actually registering one), or a sentence asking the user something, passes. A turn that
legitimately ends escapes with one line.

**The words "resume condition" alone do not pass** — that line has to name `user` / `background` /
`wakeup` / `Monitor` / `Cron`. A line that names nothing and promises again ("Resume condition:
I'll check next turn") still trips.

| False-positive containment | What it prevents |
|---|---|
| Reads `last_assistant_message` only, never the transcript | The transcript is written asynchronously and may not hold the current turn yet |
| Code fences, backticks, double quotes, table rows, and blockquote lines are stripped before matching | A turn that quotes this very rule tripping it |
| Only the tail of the message is scanned | A mid-message promise the turn then immediately carries out |
| English past tense uses different words; Korean past-tense endings are excluded by lookahead | A turn reporting work already done |
| One block per `prompt_id` | An infinite loop. A false positive costs exactly one turn |
| A missing `prompt_id`, a parse failure, or any exception exits 0 | A broken hook blocking the work |

Every block appends one line to `~/.claude/logs/stop-turn-end-gate.jsonl`. If false positives get
frequent, **report that log's `pattern` distribution to the user** — change `PROMISE_PATTERNS`
only when the user says to.

Patterns cover English and Korean. Adding a language means appending to `PROMISE_PATTERNS`,
`RESUME_RE`, and `ASK_PATTERNS` **together** — a promise pattern with no matching escape hatch
blocks every turn written in that language.

Verification:

```bash
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"
```

`exit=2` plus the reason. Called again with the same `prompt_id`, `exit=0`.

## File Encoding

- `*.ps1`: **ASCII characters only** (PowerShell 5.1 defaults to cp949 — a non-ASCII literal
  without a BOM is corrupted)
- `*.json` rule files, `*.md` headers, `*.py` hooks: UTF-8 (the PowerShell scripts load them with
  an explicit `-Encoding UTF8`; the Python hook decodes stdin as UTF-8 itself)

## Registering in settings

They are registered in `.claude/settings.json` (shared with the team). Right after editing
settings, open the `/hooks` menu once or restart for it to take effect.
