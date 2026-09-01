# Hooks (module: hooks)

Three devices bundled as one module. The first two share the same state files (the record of
documents read and skills loaded).

| Device | Hook | What it does |
|---|---|---|
| Session context injection | `SessionStart` · `SubagentStart` | Injects `session-start-header.md` (repeat-violation traps + index of detailed documents) as `additionalContext`. For the main session, `main-session-header.md` and `docs/workflow.md` as well |
| File pattern gate | `PreToolUse` (`Edit\|Write\|Read\|Skill`) | Before a file matching a `file-pattern-map.json` rule is edited, forces the canonical Read and skill load (deny when unfulfilled). Once past, injects the reminder message once per session |
| Turn-end gate | `Stop` | Blocks a turn whose last message promises a next action but names no resume condition, and says in stderr what to write instead. At most one block per prompt |

**Why `SubagentStart` is registered too**: a subagent does not inherit the parent session's
CLAUDE.md or SessionStart context. This is the only official path by which a reviewer agent comes
to know the project rules. `additionalContext` goes into the user context, so it can be dropped
when the context is compacted.

**Why a file pattern gate**: even with "read X before editing" in the instructions, editing
without reading is a repeated violation. The gate blocks that edit and says what must be read.
Reading through the shell (`cat`) does not count — only the `Read` tool and the `Skill` tool are
recorded.

**Why the user-gate header is split out**: every rule in `main-session-header.md` faces the user,
and a subagent neither sees the user nor holds AskUserQuestion. Injected into one, it appends a
turn-end block after that agent's own output format, and whatever downstream stage parses the
output gets it corrupted.

**Why a turn-end gate**: a turn that ends on "I'll continue from here" with no resume condition
kills autonomous progress silently — the session sits there until the user prods it. The gate is
two-sided on purpose: a promise phrase alone never blocks, only a promise with no resume condition
does, so a legitimate ending escapes with one line. `main-session-header.md` "Resume Condition" is
its canon. Every block writes one line to `~/.claude/logs/stop-turn-end-gate.jsonl`; if false
positives get frequent, **report the `pattern` distribution in that log to the user** rather than
editing `PROMISE_PATTERNS` on your own.

Its patterns cover English and Korean. Adding a language means appending to `PROMISE_PATTERNS`,
`RESUME_RE`, and `ASK_PATTERNS` **together** — a promise pattern with no matching escape hatch
blocks every turn written in that language.

**Prerequisite**: the session injection and file-pattern gate run on PowerShell; the turn-end gate
runs on `python`. If `python` is not on PATH, say so at setup and leave the `Stop` block out of
`settings.json` — a hook whose command cannot run reports an error on every turn.

## Files Created

| Target | Source | Substitution |
|---|---|---|
| `.claude/settings.json` | `scripts/settings.json` | none (merge the `hooks` key if a settings.json already exists) |
| `.claude/hooks/session-start.ps1` | `scripts/session-start.ps1` | none |
| `.claude/hooks/session-start-header.md` | `scripts/session-start-header.md` | `{PROJECT_NAME}` · module blocks |
| `.claude/hooks/main-session-header.md` | `scripts/main-session-header.md` | none |
| `.claude/hooks/stop-turn-end-gate.py` | `scripts/stop-turn-end-gate.py` | none |
| `.claude/hooks/pre-tool-use.ps1` | `scripts/pre-tool-use.ps1` | none |
| `.claude/hooks/file-pattern-map.json` | `scripts/file-pattern-map.json` | `{SOURCE_GLOB_LIST}` · `{SOURCE_DIRS}` · module blocks (it is JSON, so handle them through the table below instead of comments) |
| `.claude/hooks/README.md` | `scripts/hooks-README.md` | none |

Default rules in `file-pattern-map.json`:

| id | Target | requires | Kept when |
|---|---|---|---|
| `source` | `{SOURCE_GLOB_LIST}` in `{SOURCE_DIRS}` | reads: `CLAUDE.md` (+ `docs/discipline.md`) | always. Without the `discipline` module, drop that path |
| `instructions` | `CLAUDE.md`, `docs/workflow.md`, `docs/discipline.md`, the two header files, `.claude/skills/*`, `.claude/agents/*`, `.claude/commands/*` | none (message only) | always. Without the `doc-review` module, drop the `/doc-review` sentence from the message |
| `hook-config` | `.claude/hooks/*.ps1` · `*.sh` · `*.py` · `file-pattern-map.json` | reads: `.claude/hooks/README.md` | always |
| `specs` | `docs/specs/*.md` | none (message: `/design-review`) | `design-review` module |
| `board` | `docs/board.md`, `docs/board-archive.md` | none (message: prereq lines, `board-ready.sh`) | `board` module |

Domain rules (a specific subsystem's files → that guide) are added by the project. The skill only
makes the slot.

## Verification (Required Right After Generation)

```powershell
# File pattern gate -- with a path that matches the source rule. Must produce deny JSON
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1

# Again after recording a Read -- must produce additionalContext JSON (the reminder)
$json = '{"session_id":"test","tool_name":"Read","tool_input":{"file_path":"{PROJECT_PATH}/CLAUDE.md"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1
# (with the discipline module, one Read of docs/discipline.md as well)
$json = '{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use.ps1

# Session injection -- additionalContext must carry the header contents.
# SubagentStart carries session-start-header only; SessionStart also carries
# main-session-header and docs/workflow.md
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1 -HookEventName SubagentStart
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1 -HookEventName SessionStart

# Reset the state
Remove-Item "$env:TEMP\claude-code-hook-state\*-test.txt" -ErrorAction SilentlyContinue
```

```bash
# Turn-end gate -- a promise with no resume condition must exit 2
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"

# The same prompt_id again must exit 0 (one block per prompt)
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"

# Escape hatches -- all three must exit 0
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p2","last_assistant_message":"I will check the build. Resume condition: background completion notification."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p3","last_assistant_message":"I will need the token. Please run the login command and paste the output."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p4","last_assistant_message":"I checked the build and it passed. Nothing left to do."}' | python .claude/hooks/stop-turn-end-gate.py; echo "exit=$?"
```

Confirm with `Test-Path` that every path in `requires.reads` exists. A typo means nobody can edit
the files that rule matches.

## Worktree Paths

The hook recognizes `<parent>/<Repo>-worktrees/<folder>/<rel>` first and normalizes it to a
project-relative path. The worktree convention must be in this shape for the rules to match from
inside a worktree.

## Rule Authoring

`authoring-policy.md` "Writing Hook Rules" and "Header Promotion Criteria". After
generation, `.claude/hooks/README.md` is that project's canon.
