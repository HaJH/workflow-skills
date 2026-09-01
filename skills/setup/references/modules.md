# Module Catalog

A setup is **core + optional modules**. Generate only the modules the user selected, and keep a
`<!-- module:<id> -->` … `<!-- /module:<id> -->` block only when that module was selected (if it
was not, delete the whole block. The marker lines themselves are always deleted).

## Core (always)

| Generated | Template |
|---|---|
| `CLAUDE.md` | `claude-md.md` |
| `docs/workflow.md` | `workflow-md.md` |
| `.claude/commands/pm.md` · `commit.md` · `report.md` · `merge-branch.md` | `commands.md` |
| `docs/reports/` · `.claude/settings.local.json` added to `.gitignore` | — |

## Modules

| id | Name | Default | Generates | Depends on |
|---|---|---|---|---|
| `review-loop` | Autonomous review-fix loop | on | `/review` command, plus the skills and agents for the chosen review mode (`review-loop.md`) | — |
| `commit-rhythm` | Commit rhythm (`wip:`) | on | — (blocks inside CLAUDE.md, workflow.md, commands) | — |
| `board` | Work board | on | `docs/board.md` · `roadmap.md` · `backlog.md` · `board-archive.md` · `docs/issues/` · `scripts/board-ready.sh` (`board.md`) | — |
| `watch` | PM progress watch | on | `scripts/watch-commits.sh` | `commit-rhythm` |
| `just` | `/just` procedure-skip command | on | `.claude/commands/just.md` | — |
| `gate-script` | Gate script | on | `scripts/check.ps1` (Windows) or `scripts/check.sh` | — |
| `hooks` | Hooks (session injection + file-pattern gate + turn-end gate) | on | `.claude/settings.json` · `.claude/hooks/*` (`hooks.md`). The turn-end gate needs `python` on PATH | — |
| `discipline` | Development discipline document | on | `docs/discipline.md` (`discipline-md.md`) | — |
| `design-review` | Design review gate | off | `.claude/skills/design-review/*` · 3 agents · `docs/design-principles.md` · `docs/specs/` (`design-review.md`) | — |

If a dependency module is off while a module that depends on it is on, announce that the
dependency is being turned on as well, and turn it on.

### Review mode for `review-loop` (sub-choice)

| Value | Rule-conformance and correctness lens | Structural judgment lens | Generates |
|---|---|---|---|
| `mixed` (default) | built-in `/code-review <effort>` | custom `{PREFIX}-refactor-reviewer` (opus/xhigh) | `refactor-review` skill + agent |
| `official` | built-in `/code-review <effort>` | none (the same review also produces simplification suggestions) | — |
| `custom` | custom `{PREFIX}-code-reviewer` (sonnet/medium) + language rules file | custom `{PREFIX}-refactor-reviewer` (opus/xhigh) | two skills + two agents + `review-rules-*.md` |

If the project has further lenses (a frontend, say), build one more skill-and-agent pair from the
`custom` skeleton. Tier it by "mixed lens = middle (sonnet/high)".

## Placeholders

| Name | Meaning | Example |
|---|---|---|
| `{PROJECT_NAME}` | Project name | `MyApp` |
| `{PROJECT_PATH}` | Absolute path of the main tree, forward slashes | `F:/Repo/MyApp` |
| `{WORKTREES_PATH}` | Worktree parent path | `F:/Repo/MyApp-worktrees` |
| `{PREFIX}` | Agent name prefix | `myapp` |
| `{LANG}` | Primary language | `Rust` |
| `{SOURCE_GLOB}` | Source pattern under review | `**/*.rs` |
| `{SOURCE_DIRS}` | Source directories (hook scopePath, review targets) | `crates/`, `ui/src/` |
| `{EXCLUDE_DIRS}` | Excluded from review (vendor, generated) | `vendor/`, `node_modules/` |
| `{GATE_CMD}` | One-line gate command | `.\scripts\check.ps1` |
| `{ROUND_BUDGET}` | Round budget | `3` |
| `{REVIEW_EFFORT}` | effort passed to `/code-review` | `high` |
| `{HOSTING}` | Hosting | `GitHub (private, gh)` / `fully local` |

Write every path with forward slashes. A path that must stay identical inside a worktree — a
report path, for instance — is always absolute.

### Template-Local Placeholders

Used inside a single template, with its meaning fixed by that file's "Substitution Notes". They
are subject to the leftover check after generation.

| Name | File | Meaning |
|---|---|---|
| `{ONE_LINE_DESCRIPTION}` · `{LANG_CONVENTIONS}` · `{SKILL_LIST}` | `claude-md.md` | One-line description · language conventions section · skill list |
| `{DISPATCH_TABLE}` · `{AUTHORING_POLICY}` · `{RUN_NOTES}` · `{FORMAT_CMD}` | `workflow-md.md` | Dispatch table · instruction authoring policy section · run info · format command |
| `{SCOPE_OWNER}` · `{LANG_FENCE}` · `{DEP_PROJECT_RULES}` · `{ARCH_DOC}` · `{WHERE_THE_VALUE_IS}` · `{WHERE_THE_VALUE_IS_CONFORMANCE}` | `review-loop.md` | Out-of-scope owner · code fence tag · layer rules · architecture canon · highest-value category |
| `{AREA_1}` · `{AREA_1_SCOPE}` · `{V0_TITLE}` · `{V0_DEFINITION}` | `board.md` | First area group · first milestone |
| `{SOURCE_GLOB_LIST}` · `{SOURCE_SAMPLE}` | `hooks.md` · `scripts/file-pattern-map.json` | Hook rule patterns array (per extension, as `"*.rs"`, `"*.ts"`) · one source file for verification |
| `{DEP_MANIFEST}` | `design-review/design-principles.md` | The file that declares module dependencies |
