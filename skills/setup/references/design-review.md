# Design Review Gate (module: design-review)

Inspects the code structure design in a spec before implementation, through a clean-context
pipeline (extract → verify → judge). Language-agnostic. Files generated:

| Target | Source | Substitution |
|---|---|---|
| `.claude/skills/design-review/SKILL.md` | `design-review/SKILL.md` | `{PROJECT_PATH}` · `{SOURCE_DIRS}` |
| `.claude/skills/design-review/prompts/round-1.md` | `design-review/prompts/round-1.md` | `{PROJECT_PATH}` |
| `.claude/skills/design-review/prompts/re-review.md` | `design-review/prompts/re-review.md` | `{PROJECT_PATH}` |
| `.claude/agents/design-claim-extractor.md` | `design-review/agents/design-claim-extractor.md` | none |
| `.claude/agents/design-fact-verifier.md` | `design-review/agents/design-fact-verifier.md` | `{SOURCE_DIRS}` |
| `.claude/agents/design-structure-judge.md` | `design-review/agents/design-structure-judge.md` | none |
| `docs/design-principles.md` | `design-review/design-principles.md` | add project-specific axes together with the user |
| `docs/specs/` | empty directory + `.gitkeep` | — |
| `.gitignore` | add `docs/specs/.review-cache/` | — |

The spec file name is `docs/specs/YYYY-MM-DD-<topic>.md`. That differs from the path superpowers'
brainstorming uses (`docs/superpowers/specs/`), so if the project uses superpowers, put one line
in CLAUDE.md: "specs live in `docs/specs/`".

## What to Confirm at Setup

- Project-specific axes for the design principles — the axes in the skeleton are general
  principles. If the project has layer rules (for example, "the core crate is ignorant of the
  UI"), attach them as an axis. A new axis must also pass the skeleton's admission test
- The canon for "Direction of Dependency and Knowledge" — if there is a file declaring module
  dependencies (`Cargo.toml` workspace, `package.json`, `.Build.cs`), write its name

## Maintenance Rules

- Refer to an axis by name. Do not number them — once numbered, the review reports "violation of
  article N" and the spec follows that voice
- The pipeline tiers are set by each agent's frontmatter. Change them there
- Emit a profiling block every round. Never pin a baseline value into the skill
