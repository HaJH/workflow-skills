# Workflow Skills

Set up a local PM-Dev-Reviewer development workflow for a project: CLAUDE.md, workflow doc, commands, and selectable modules (autonomous review loop, commit rhythm, board, hooks, comment audit, design review, instruction doc review).

## Skills

| Skill | Use when |
|---|---|
| `/workflow:setup` | Use when initializing a new local project (no CI, no remote MR) with the PM-Dev-Reviewer workflow - CLAUDE.md, docs/workflow.md, commands, and selectable modules (autonomous review loop, commit rhythm, board, progress watch, /just, gate script, hooks, discipline doc, comment audit, design-review gate, instruction doc review). Also use to re-apply or update the workflow in an existing project. Not for GitLab/GitHub MR-based CI workflows. |

## Hooks the setup can install

| Event | Device |
|---|---|
| `SessionStart` · `SubagentStart` | Project context injection, layered so a subagent gets the header a subagent can act on |
| `PreToolUse` (`Edit\|Write\|Read\|Skill`) | File-pattern gate (forces the canonical Read before an edit) + content lint (denies a write carrying a mechanical violation) |
| `PreToolUse` (`Bash\|PowerShell`) | Command gate — denies a command run before the process document that governs it was read, or a raw command that omits a required flag |
| `PreToolUse` (`mcp__<server>__<tool>`) | MCP tool gate — denies a call that omits a required field |
| `UserPromptSubmit` | Session-length signal, measured from the transcript |
| `Stop` | Turn-end gate — blocks a turn that promises a next action but names no resume condition |

The hooks are Python, launched through bash, so they run the same on Windows (Git Bash) and macOS/Linux. They need Python 3.9 or newer.

## Board Page From a Terminal

With the `board` module, `scripts/board` (`scripts\board` in Windows cmd) opens the project's
board as a read-only kanban page, and `scripts/board ready` prints which cards can start. To type
just `board` anywhere inside a project, add a per-user shortcut:

- macOS/Linux — in `~/.zshrc` or `~/.bashrc`:
  `board() { bash "$(git rev-parse --show-toplevel)/scripts/board" "$@"; }`
- Windows cmd — save this as `board.cmd` in a folder on `PATH`:

  ```bat
  @echo off
  setlocal
  set "ROOT="
  for /f "delims=" %%R in ('git rev-parse --show-toplevel 2^>nul') do set "ROOT=%%R"
  if not defined ROOT (>&2 echo board: not inside a git project& exit /b 2)
  if not exist "%ROOT:/=\%\scripts\board.cmd" (>&2 echo board: %ROOT% has no scripts\board.cmd& exit /b 2)
  call "%ROOT:/=\%\scripts\board.cmd" %*
  ```

## Install

Clone into your skills directory and the plugin loads on the next session:

```
git clone https://github.com/HaJH/workflow-skills.git ~/.claude/skills/workflow
```

To try it without installing: `claude --plugin-dir ./workflow-skills`.

## Language

The skill and everything it generates are written in English. The generated `CLAUDE.md` tells the agent to respond and plan in the user's language.

## Licence

MIT. See [LICENSE](LICENSE).
