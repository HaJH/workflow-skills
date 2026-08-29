# Hooks (module: hooks)

Two devices bundled as one module. They share the same state files (the record of documents read
and skills loaded).

| Device | Hook | What it does |
|---|---|---|
| Session context injection | `SessionStart` · `SubagentStart` | Injects `session-start-header.md` (repeat-violation traps + index of detailed documents) as `additionalContext`. For the main session, `docs/workflow.md` as well |
| File pattern gate | `PreToolUse` (`Edit\|Write\|Read\|Skill`) | Before a file matching a `file-pattern-map.json` rule is edited, forces the canonical Read and skill load (deny when unfulfilled). Once past, injects the reminder message once per session |

**Why `SubagentStart` is registered too**: a subagent does not inherit the parent session's
CLAUDE.md or SessionStart context. This is the only official path by which a reviewer agent comes
to know the project rules. `additionalContext` goes into the user context, so it can be dropped
when the context is compacted.

**Why a file pattern gate**: even with "read X before editing" in the instructions, editing
without reading is a repeated violation. The gate blocks that edit and says what must be read.
Reading through the shell (`cat`) does not count — only the `Read` tool and the `Skill` tool are
recorded.

## Files Created

| Target | Source | Substitution |
|---|---|---|
| `.claude/settings.json` | `scripts/settings.json` | none (merge the `hooks` key if a settings.json already exists) |
| `.claude/hooks/session-start.ps1` | `scripts/session-start.ps1` | none |
| `.claude/hooks/session-start-header.md` | `scripts/session-start-header.md` | `{PROJECT_NAME}` · module blocks |
| `.claude/hooks/pre-tool-use.ps1` | `scripts/pre-tool-use.ps1` | none |
| `.claude/hooks/file-pattern-map.json` | `scripts/file-pattern-map.json` | `{SOURCE_GLOB_LIST}` · `{SOURCE_DIRS}` · module blocks (it is JSON, so handle them through the table below instead of comments) |
| `.claude/hooks/README.md` | `scripts/hooks-README.md` | none |

Default rules in `file-pattern-map.json`:

| id | Target | requires | Kept when |
|---|---|---|---|
| `source` | `{SOURCE_GLOB_LIST}` in `{SOURCE_DIRS}` | reads: `CLAUDE.md` (+ `docs/discipline.md`) | always. Without the `discipline` module, drop that path |
| `instructions` | `CLAUDE.md`, `docs/workflow.md`, `docs/discipline.md`, `.claude/hooks/session-start-header.md`, `.claude/skills/*`, `.claude/agents/*`, `.claude/commands/*` | none (message only) | always |
| `hook-config` | `.claude/hooks/*` | reads: `.claude/hooks/README.md` | always |
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

# Session injection -- additionalContext must carry the header contents
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1 -HookEventName SubagentStart

# Reset the state
Remove-Item "$env:TEMP\claude-code-hook-state\*-test.txt" -ErrorAction SilentlyContinue
```

Confirm with `Test-Path` that every path in `requires.reads` exists. A typo means nobody can edit
the files that rule matches.

## Worktree Paths

The hook recognizes `<parent>/<Repo>-worktrees/<folder>/<rel>` first and normalizes it to a
project-relative path. The worktree convention must be in this shape for the rules to match from
inside a worktree.

## Rule Authoring

`authoring-policy.md` "Writing Hook Rules" and "session-start-header Promotion Criteria". After
generation, `.claude/hooks/README.md` is that project's canon.
