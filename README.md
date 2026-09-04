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
| `PreToolUse` (`Bash\|PowerShell`) | Command gate — denies a raw command that omits a required flag |
| `PreToolUse` (`mcp__<server>__<tool>`) | MCP tool gate — denies a call that omits a required field |
| `UserPromptSubmit` | Session-length signal, measured from the transcript |
| `Stop` | Turn-end gate — blocks a turn that promises a next action but names no resume condition |

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
