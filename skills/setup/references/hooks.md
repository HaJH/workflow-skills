# Hooks (module: hooks)

Bundled as one module because they share machinery: the `PreToolUse` devices share the session
state files (the record of documents read and skills loaded) or the same script, and the two
header files feed both the injection and the turn-end gate.

| Device | Hook | What it does |
|---|---|---|
| Session context injection | `SessionStart` · `SubagentStart` | Injects `session-start-header.md` (repeat-violation traps + index of detailed documents) as `additionalContext`. For the main session, `main-session-header.md` and `docs/workflow.md` as well |
| File pattern gate | `PreToolUse` (`Edit\|Write\|Read\|Skill`) | Before a file matching a `file-pattern-map.json` rule is edited, forces the canonical Read and skill load (deny when unfulfilled). Once past, injects the reminder message once per session |
| Content lint | the same hook | Denies a write whose payload carries a `content-lint.json` violation — a banned character, a banned line shape |
| Command gate | `PreToolUse` (`Bash\|PowerShell`) | Denies a command matching a `command-gate.json` rule that omits a required flag |
| MCP tool gate | `PreToolUse` (`mcp__<server>__<tool>`) | Denies a call to that tool that omits a required field |
| Session-length signal | `UserPromptSubmit` | Measures the transcript and injects `[session length]` once the session is long enough to suggest a handoff |
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

**Why a content lint next to the read gate**: reading the rule does not stop the violation from
being typed. The lint carries only what is never a judgment call, so one false positive cannot
permanently block a legitimate edit; everything that has to be read and weighed goes to the
`comment-audit` module instead. The two split the same rule document between them — mechanical
here, judgment there — so neither grows into the other.

**Why a command gate and an MCP tool gate**: both guard a call reached through an autonomous flow,
where the slash-command or skill file that carries the required arguments is not in context. The
argument is dropped silently and the wrong artifact exists before anyone looks. Documentation
alone does not reach that moment; the hook does.

**Why the session-length signal is measured, not remembered**: the handoff rule
(`docs/workflow.md` "Session Length") dies exactly when it is needed — a compaction drops "how
many commits so far" from the summary, and on a large-context model the context-remaining warning
never fires. The hook measures the transcript instead and only injects when a threshold rises, so
a user who chose to continue is not asked again on every prompt.

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

**Prerequisite**: the injection and the three `PreToolUse` devices run on PowerShell; the
session-length signal and the turn-end gate run on `python`. If `python` is not on PATH, say so at
setup and leave the `UserPromptSubmit` and `Stop` blocks out of `settings.json` — a hook whose
command cannot run reports an error on every turn.

## Files Created

| Target | Source | Substitution |
|---|---|---|
| `.claude/settings.json` | `scripts/settings.json` | none (merge the `hooks` key if a settings.json already exists) |
| `.claude/hooks/session-start.ps1` | `scripts/session-start.ps1` | none |
| `.claude/hooks/session-start-header.md` | `scripts/session-start-header.md` | `{PROJECT_NAME}` · module blocks |
| `.claude/hooks/main-session-header.md` | `scripts/main-session-header.md` | none |
| `.claude/hooks/stop-turn-end-gate.py` | `scripts/stop-turn-end-gate.py` | none |
| `.claude/hooks/user-prompt-submit-session-length.py` | `scripts/user-prompt-submit-session-length.py` | none |
| `.claude/hooks/pre-tool-use.ps1` | `scripts/pre-tool-use.ps1` | none |
| `.claude/hooks/pre-tool-use-command.ps1` | `scripts/pre-tool-use-command.ps1` | none. Skip with `command-gate.json` |
| `.claude/hooks/file-pattern-map.json` | `scripts/file-pattern-map.json` | `{SOURCE_GLOB_LIST}` · `{SOURCE_DIRS}` · module blocks (it is JSON, so handle them through the table below instead of comments) |
| `.claude/hooks/content-lint.json` | `scripts/content-lint.json` | replace the example rule (below) |
| `.claude/hooks/command-gate.json` | `scripts/command-gate.json` | replace the example rules (below) |
| `.claude/hooks/README.md` | `scripts/hooks-README.md` | none |

Default rules in `file-pattern-map.json`:

| id | Target | requires | Kept when |
|---|---|---|---|
| `source` | `{SOURCE_GLOB_LIST}` in `{SOURCE_DIRS}` | reads: `CLAUDE.md` (+ `docs/discipline.md`) | always. Without the `discipline` module, drop that path |
| `instructions` | `CLAUDE.md`, `docs/workflow.md`, `docs/discipline.md`, the two header files, `.claude/skills/*`, `.claude/agents/*`, `.claude/commands/*` | none (message only) | always. Without the `doc-review` module, drop the `/doc-review` sentence from the message |
| `hook-config` | `.claude/hooks/*.ps1` · `*.sh` · `*.py` · the three rule files | reads: `.claude/hooks/README.md` | always |
| `specs` | `docs/specs/*.md` | none (message: `/design-review`) | `design-review` module |
| `board` | `docs/board.md`, `docs/board-archive.md` | none (message: prereq lines, `board-ready.sh`) | `board` module |

Domain rules (a specific subsystem's files → that guide) are added by the project. The skill only
makes the slot.

### The Two Rule Files That Ship With an Example

`content-lint.json` and `command-gate.json` have no useful defaults — what is mechanically banned,
and which command must not be typed raw, are facts about one project. Both therefore ship with a
worked example whose ids begin with `example-`, and setup asks for the real thing:

- **Content lint**: "Is there anything that is *always* wrong to write into a source file here —
  a character the toolchain misreads, a comment form the project bans?" The shipped example is the
  C++ case (a decorative character read in the local codepage breaks the compile; `///`; an issue
  ID in a comment). With no answer, do not generate `content-lint.json` — the hook treats a missing
  file as "no lint" and everything else keeps working
- **Command gate**: "Is there a command that must go through a slash command instead of being
  typed raw, or a tool call that must carry a field?" With no answer, generate neither
  `command-gate.json`, `pre-tool-use-command.ps1`, nor their `settings.json` entries — a registered
  hook with no rules is a hook that reports nothing and hides the fact that nothing is guarded

An `mcpTools` rule needs its own `PreToolUse` entry in `settings.json` naming that exact tool; the
shipped `mcp__tracker__issue_create` entry is part of the example and goes with it.

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

# Content lint -- a payload carrying one banned item must produce deny JSON.
# Never pipe this case: a PowerShell-to-PowerShell pipe re-encodes the payload and a
# banned character comes back as a pass. Write BOM-less UTF-8 and redirect through cmd.
$json = '{"session_id":"test","tool_name":"Write","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}","content":"<a line carrying one banned item>"}}'
[System.IO.File]::WriteAllText('case.json', $json, [System.Text.UTF8Encoding]::new($false))
cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File .claude\hooks\pre-tool-use.ps1 < case.json"

# Command gate -- one required flag removed must produce deny JSON, the complete command empty
$json = '{"session_id":"test","tool_name":"Bash","tool_input":{"command":"<the guarded command, one flag removed>"}}'
$json | powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/pre-tool-use-command.ps1

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

# Session-length signal -- against a long session's transcript, additionalContext JSON;
# the same session_id again, empty output
echo '{"hook_event_name":"UserPromptSubmit","session_id":"t","transcript_path":"<a long session jsonl>"}' | python .claude/hooks/user-prompt-submit-session-length.py
```

Confirm with `Test-Path` that every path in `requires.reads` exists. A typo means nobody can edit
the files that rule matches. Confirm that no rule id starting with `example-` is left in
`content-lint.json` or `command-gate.json`.

## Worktree Paths

The hook recognizes `<parent>/<Repo>-worktrees/<folder>/<rel>` first and normalizes it to a
project-relative path. The worktree convention must be in this shape for the rules to match from
inside a worktree.

## Rule Authoring

`authoring-policy.md` "Writing Hook Rules" and "Header Promotion Criteria". After
generation, `.claude/hooks/README.md` is that project's canon.
