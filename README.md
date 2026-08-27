# Workflow Skills

Set up a local PM-Dev-Reviewer development workflow for a project: CLAUDE.md, workflow doc, commands, and selectable modules (autonomous review loop, commit rhythm, board, hooks, design review).

## Skills

| Skill | Use when |
|---|---|
| `/workflow:setup` | Use when initializing a new local project (no CI, no remote MR) with the PM-Dev-Reviewer workflow - CLAUDE.md, docs/workflow.md, commands, and selectable modules (autonomous review loop, commit rhythm, board, progress watch, /just, gate script, hooks, discipline doc, design-review gate). Also use to re-apply or update the workflow in an existing project. Not for GitLab/GitHub MR-based CI workflows. |

## Install

Clone into your skills directory and the plugin loads on the next session:

```
git clone https://github.com/HaJH/workflow-skills.git ~/.claude/skills/workflow
```

To try it without installing: `claude --plugin-dir ./workflow-skills`.

## Licence

MIT. See [LICENSE](LICENSE).
