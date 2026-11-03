# Hooks (module: hooks)

Bundled as one module because they share machinery: the `PreToolUse` devices share the session
state files (the record of documents read and skills loaded), the rule-file loader and
`hook_common.py`, and the two header files feed both the injection and the turn-end gate.

| Device | Hook | What it does |
|---|---|---|
| Session context injection | `SessionStart` · `SubagentStart` | Injects `session-start-header.md` (repeat-violation traps + index of detailed documents) as `additionalContext`. For the main session, `main-session-header.md` as well. `docs/workflow.md` is not injected — the read gates ask for it before the actions it governs. Right after a compaction it clears the session's gate records |
| File pattern gate | `PreToolUse` (`Edit\|Write\|Read\|Skill`) | Before a file matching a `file-pattern-map.json` rule is edited, forces the canonical Read and skill load (deny when unfulfilled). Once past, injects the reminder message once per session |
| Content lint | the same hook | Denies a write whose payload carries a `content-lint.json` violation — a banned character, a banned line shape |
| Command read gate | `PreToolUse` (`Bash\|PowerShell`) | Denies a command matching a `file-pattern-map.json` `commandRules` entry until the document that governs it has been Read this session |
| Command flag gate | the same hook | Denies a command matching a `command-gate.json` rule that omits a required flag |
| MCP tool gate | `PreToolUse` (`mcp__<server>__<tool>`) | Denies a call to that tool that omits a required field |
| Session-length signal | `UserPromptSubmit` | Measures the transcript and injects `[session length]` once the context is large enough to suggest a handoff |
| Turn-end gate | `Stop` | Blocks a turn whose last message promises a next action but names no resume condition, and says in stderr what to write instead. At most one block per prompt |

**Why `SubagentStart` is registered too**: a subagent does not inherit the parent session's
CLAUDE.md or SessionStart context. This is the only official path by which a reviewer agent comes
to know the project rules. `additionalContext` goes into the user context, so it can be dropped
when the context is compacted.

**Why a file pattern gate**: even with "read X before editing" in the instructions, editing
without reading is a repeated violation. The gate blocks that edit and says what must be read.
Reading through the shell (`cat`) does not count — only the `Read` tool and the `Skill` tool are
recorded. A compaction drops the documents' content but not the record, so the injection hook
clears the record when the session resumes from one, and the gates ask again.

**Why the user-gate header is split out**: every rule in `main-session-header.md` faces the user,
and a subagent neither sees the user nor holds AskUserQuestion. Injected into one, it appends a
turn-end block after that agent's own output format, and whatever downstream stage parses the
output gets it corrupted.

**Why a content lint next to the read gate**: reading the rule does not stop the violation from
being typed. The lint carries only what is never a judgment call, so one false positive cannot
permanently block a legitimate edit; everything that has to be read and weighed goes to the
`comment-audit` module instead. The two split the same rule document between them — mechanical
here, judgment there — so neither grows into the other.

**Why a command read gate**: a process document that is not injected reaches the agent only if
something asks for it at the moment it applies. Injecting it instead is not free: hook output over
the harness's size limit arrives as a preview with the rest moved to a file, so a long document
that looks injected is not actually delivered. A document governing one action (a release guide
before `git tag`, a deploy guide before the deploy command) goes behind the command it governs.

**Why a command flag gate and an MCP tool gate**: both guard a call reached through an autonomous
flow, where the slash-command or skill file that carries the required arguments is not in context.
The argument is dropped silently and the wrong artifact exists before anyone looks. Documentation
alone does not reach that moment; the hook does.

**Why the session-length signal is measured, not remembered**: the handoff rule
(`docs/workflow.md` "Session Length") dies exactly when it is needed — how much context has piled
up is not visible inside the conversation, and on a large-context model the context-remaining
warning never fires. The hook measures the transcript instead and only injects when a threshold
rises, so a user who chose to continue is not asked again on every prompt. It measures context
size alone: counts of work done (commits, review rounds) are not what the cost grows with, and a
session that commits once per review round is the case the rule says to keep going.

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

**Prerequisite**: every hook runs on `bash` and Python 3.9 or newer, the same on Windows (Git
Bash) and macOS/Linux. `settings.json` launches each one through `run-python-hook.sh`, which picks
the first of `python3` · `python` · `py -3` that actually runs a supported version. If `bash` or a
supported Python is missing, say so at setup and leave the `hooks` module off — a registered hook
whose command cannot run reports an error on every call.

## Files Created

| Target | Source | Substitution |
|---|---|---|
| `.claude/settings.json` | `scripts/settings.json` | none (merge the `hooks` key if a settings.json already exists) |
| `.claude/hooks/run-python-hook.sh` | `scripts/run-python-hook.sh` | none |
| `.claude/hooks/hook_common.py` | `scripts/hook_common.py` | none |
| `.claude/hooks/session-start.py` | `scripts/session-start.py` | none |
| `.claude/hooks/session-start-header.md` | `scripts/session-start-header.md` | `{PROJECT_NAME}` · module blocks |
| `.claude/hooks/main-session-header.md` | `scripts/main-session-header.md` | none |
| `.claude/hooks/stop-turn-end-gate.py` | `scripts/stop-turn-end-gate.py` | none |
| `.claude/hooks/user-prompt-submit-session-length.py` | `scripts/user-prompt-submit-session-length.py` | none |
| `.claude/hooks/pre-tool-use.py` | `scripts/pre-tool-use.py` | none |
| `.claude/hooks/pre-tool-use-command.py` | `scripts/pre-tool-use-command.py` | none. Skip when neither `commandRules` nor `command-gate.json` carries a rule (below) |
| `.claude/hooks/file-pattern-map.json` | `scripts/file-pattern-map.json` | `{SOURCE_GLOB_LIST}` · `{SOURCE_DIRS}` · `{EXCLUDE_DIRS}` · `{AUTHORING_POLICY_DOC}` · module blocks (it is JSON, so handle them through the table below instead of comments) |
| `.claude/hooks/content-lint.json` | `scripts/content-lint.json` | replace the example rule (below) |
| `.claude/hooks/command-gate.json` | `scripts/command-gate.json` | replace the example rules (below) |
| `.claude/hooks/README.md` | `scripts/hooks-README.md` | none |
| `.claude/hooks/tests/test_hooks.py` | `scripts/hooks-tests/test_hooks.py` | none |

Default rules in `file-pattern-map.json`:

| id | Target | requires | Kept when |
|---|---|---|---|
| `source` | `{SOURCE_GLOB_LIST}` in `{SOURCE_DIRS}` | reads: `CLAUDE.md` (+ `docs/discipline.md`) | always. Without the `discipline` module, drop that path |
| `instructions` | `CLAUDE.md`, `docs/workflow.md`, `docs/discipline.md`, the two header files, `.claude/skills/*`, `.claude/agents/*`, `.claude/commands/*` | reads: `{AUTHORING_POLICY_DOC}` — `docs/authoring-policy.md` with the `doc-review` module, else `docs/workflow.md` | always. Without the `doc-review` module, drop the `/doc-review` sentence from the message |
| `hook-config` | `.claude/hooks/*.sh` · `*.py` (the tests included) · the three rule files | reads: `.claude/hooks/README.md` | always |
| `specs` | `docs/specs/*.md` | reads: `docs/workflow.md` | `design-review` module |
| `design-docs` | `docs/design/*.md` | reads: `docs/workflow.md` | always |
| `board` | `docs/board.md`, `docs/board-archive.md` | none (message: prereq lines, `board-ready.sh`) | `board` module |

`commandRules` ships with one rule, `git-write`: `git commit` · `git worktree add` · `git merge`
require a `Read` of `docs/workflow.md`, which is not injected at session start. Domain rules (a
specific subsystem's files → that guide) and further command rules (a command → the process
document that governs it) are added by the project. A document injected at session start needs no command rule — the gate counts only
`Read` tool calls, so gating a command on an injected document makes the agent read again what it
already holds.

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
  typed raw, or a tool call that must carry a field?" With no answer, do not generate
  `command-gate.json` or the `mcp__` entry in `settings.json` — a registered hook with no rules is a
  hook that reports nothing and hides the fact that nothing is guarded. With `commandRules` empty
  as well, leave out `pre-tool-use-command.py` and its `Bash|PowerShell` entry too

A `commands` rule names the command as a token sequence (`"commands": ["gh pr create"]`), not a
regex: options may sit between the tokens (`gh --repo o/r pr create` still matches), and the first
token is what the hook peels a path prefix and `.exe` off. An `mcpTools` rule needs its own
`PreToolUse` entry in `settings.json` naming that exact tool; the shipped
`mcp__tracker__issue_create` entry is part of the example and goes with it.

## Verification (Required Right After Generation)

Run the regression tests first. They copy the hooks into a throwaway project with their own rule
files, so they check the scripts, not this project's rules:

```bash
python -m unittest discover -s .claude/hooks/tests -v
```

Then check this project's rules with the real files. Run these from `bash` (Git Bash on Windows) —
a PowerShell pipe re-encodes the payload, and a banned non-ASCII character comes back as a pass.
Use a `session_id` no real session has; a new one starts with nothing recorded. Write
`file_path` the way Claude Code sends it (`{PROJECT_PATH}/...`); a Git Bash path (`/c/...`) is not
under the project root as Python sees it, matches no rule, and every case comes back empty.

```bash
H=".claude/hooks/run-python-hook.sh"

# File pattern gate -- a path the source rule matches must produce deny JSON
echo '{"session_id":"verify-1","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}","new_string":"x"}}' | bash "$H" pre-tool-use.py

# After recording the Read (and with the discipline module, a Read of docs/discipline.md too),
# the same edit must produce additionalContext JSON (the reminder)
echo '{"session_id":"verify-1","tool_name":"Read","tool_input":{"file_path":"{PROJECT_PATH}/CLAUDE.md"}}' | bash "$H" pre-tool-use.py
echo '{"session_id":"verify-1","tool_name":"Edit","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}","new_string":"x"}}' | bash "$H" pre-tool-use.py

# Content lint -- a payload carrying one banned item must produce deny JSON
echo '{"session_id":"verify-2","tool_name":"Write","tool_input":{"file_path":"{PROJECT_PATH}/{SOURCE_SAMPLE}","content":"<a line carrying one banned item>"}}' | bash "$H" pre-tool-use.py

# Command gates -- one required flag removed (or a commandRules command before its Read)
# must produce deny JSON; the complete command empty output
echo '{"session_id":"verify-3","tool_name":"Bash","tool_input":{"command":"<the guarded command, one flag removed>"}}' | bash "$H" pre-tool-use-command.py

# MCP tool gate -- a call missing one required field must produce deny JSON
echo '{"session_id":"verify-3","tool_name":"<the guarded tool>","tool_input":{}}' | bash "$H" pre-tool-use-command.py

# Session injection -- SubagentStart carries session-start-header only; SessionStart also
# carries main-session-header (docs/workflow.md is never injected)
echo '{}' | bash "$H" session-start.py --hook-event-name SubagentStart
echo '{}' | bash "$H" session-start.py --hook-event-name SessionStart

# Turn-end gate -- a promise with no resume condition must exit 2
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | bash "$H" stop-turn-end-gate.py; echo "exit=$?"

# The same prompt_id again must exit 0 (one block per prompt)
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | bash "$H" stop-turn-end-gate.py; echo "exit=$?"

# Escape hatches -- all three must exit 0
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p2","last_assistant_message":"I will check the build. Resume condition: background completion notification."}' | bash "$H" stop-turn-end-gate.py; echo "exit=$?"
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p3","last_assistant_message":"I will need the token. Please run the login command and paste the output."}' | bash "$H" stop-turn-end-gate.py; echo "exit=$?"
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p4","last_assistant_message":"I checked the build and it passed. Nothing left to do."}' | bash "$H" stop-turn-end-gate.py; echo "exit=$?"

# Session-length signal -- against a long session's transcript, additionalContext JSON;
# the same session_id again, empty output
echo '{"hook_event_name":"UserPromptSubmit","session_id":"t","transcript_path":"<a long session jsonl>"}' | bash "$H" user-prompt-submit-session-length.py
```

A gate hook that exits 1 with a message on stderr did **not** run its check (a broken rule file,
an unwritable state directory) — fix that before reading anything into an empty output.

Confirm that every path in `requires.reads` exists (`ls <path>`). A typo means nobody can edit
the files that rule matches, or run the command it gates. Confirm that no rule id starting with
`example-` is left in `content-lint.json` or `command-gate.json`.

## Worktree Paths

The hook recognizes `<parent>/<Repo>-worktrees/<folder>/<rel>` first and normalizes it to a
project-relative path. The worktree convention must be in this shape for the rules to match from
inside a worktree.

## Rule Authoring

`authoring-policy.md` "Writing Hook Rules" and "Header Promotion Criteria". After
generation, `.claude/hooks/README.md` is that project's canon.
