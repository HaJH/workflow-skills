# Claude Code Hooks

## Runtime and Entry Point

Every hook runs on `bash` and Python 3.9 or newer, identically on Windows (Git Bash) and
macOS/Linux. `.claude/settings.json` launches each one as
`bash "$CLAUDE_PROJECT_DIR/.claude/hooks/run-python-hook.sh" <script.py> [args...]`. The launcher
finds the script next to itself and tries `python3` → `python` → `py -3`, taking the first that
actually runs a supported version. The probe does not read stdin; the chosen interpreter is
`exec`ed, so input, arguments, output and exit code pass through untouched. A hook that fails is
never re-run under another interpreter.

With no supported interpreter the launcher prints a diagnostic and exits 1 — a non-blocking hook
error, not a policy block (exit 2). It never installs Python or changes the user's settings.

`hook_common.py` gives the `PreToolUse` and `SessionStart` scripts UTF-8 JSON in and out (a BOM is
tolerated), case-insensitive field access, path normalization, the session state files, and the
one diagnostic channel. It swallows nothing — each script decides what it absorbs, by the policy
below.

### How Far a Failure Is Surfaced

A failure a hook meets falls into one of four branches, each with a fixed treatment. **No branch
blocks the tool call** — only a policy decision does. One environment accident stopping every
edit, commit and push costs more than a gate going missing in that moment.

| Branch | Treatment | Why |
|---|---|---|
| The input is unknown (stdin unreadable, input JSON unparsable) | exit 0, silent | There is nothing to judge, and nothing distinguishes it from an unrelated call |
| A resource the gate decision needs is missing or broken (session state directory, `file-pattern-map.json`, a present-but-broken `command-gate.json`, a rule that guards nothing) | diagnostic + exit 1 | Passed silently, "nothing to gate" and "the gate is off" look the same |
| A read document or a loaded skill could not be recorded | diagnostic + exit 1 | Without the record, edits stay blocked after the document was read, and nothing says why |
| A failure that changes no outcome (the once-per-rule reminder record, a log write, stream encoding setup) | continue, silent | The worst case is the same reminder once more |

Diagnostics go through `hook_common.report_failure(source, detail)` alone, as UTF-8 bytes on
stderr whatever the locale. Do not invent a fifth branch; place a new failure in one of these.

**"Absent" and "broken" differ.** A resource whose absence just means a smaller check —
`content-lint.json`, `command-gate.json` — is reported only when it is **present** and cannot be
read; a broken one is reported and the check it carries runs without it. Reporting absence too
would make every call print the same diagnostic in a project that chose not to have the file.

Symptom: a gate that should fire does not, and the hook prints nothing. Edits stay blocked after
the document was read, and nothing says why.

## SessionStart / SubagentStart — Automatic Project Context Load

`session-start.py` injects context as `additionalContext`. It is layered:

- **Always (main + sub)**: `session-start-header.md` — repeat-violation traps + index of detailed
  documents
- **Main session only — user gates**: `main-session-header.md` — permission to start,
  AskUserQuestion, turn-end reporting, resume condition. A subagent neither sees the user nor
  holds the question tool, so it cannot run these rules. Injected into one, it appends a turn-end
  block after that agent's own output format and corrupts whatever downstream stage parses the
  output
- **On demand (not injected)**: the remaining documents the header index points at. Read them
  when needed. `docs/workflow.md` is one of them: it is too long to arrive whole, so
  `file-pattern-map.json` asks for it right before the actions it governs — the `git-write`
  command rule (commit, worktree add, merge) and the `specs` · `design-docs` edit rules

**Do not inject a long document.** Hook output over the harness's size limit arrives as a preview
with the rest moved to a file, so a document that looks injected is not actually delivered. The
limit follows the harness version and is not written here — the test is "would this document sit
whole next to the two headers?". A document that fails it goes behind the action it governs
instead (below, "Command Read Gate").

To change the document list, edit `COMMON` / `MAIN_ONLY` in `session-start.py`. A missing
document is marked `(missing)`. An invalid event argument, an unreadable document, or an output
error is not hidden: it surfaces as a diagnostic and a non-blocking failure.

### Clearing the Records Right After a Compaction

When `SessionStart` arrives with `source` `compact`, the session's `requires-done-*` and
`fired-rules-*` records are deleted. The compaction took the documents' content out of the
context; left in place, the records keep the gates open with the content gone. Other sources (a new
session, `resume`) clear nothing — deleting what the session has read only makes it read again.
`SubagentStart` never looks at `source` and clears nothing.

**A failed reset is reported** (branch: a resource is broken), but the hook does not exit 1 — it
goes on injecting, since giving up the injection would drop the whole project context. The failure
goes to stderr and to the **head of the injected context**, so the session sees on the spot what to
read again. One record failing does not stop the others being deleted.

**Why SubagentStart is registered too**: a subagent does not inherit the parent session's
CLAUDE.md, settings hooks, or SessionStart context. Registering the same script is what makes
main and sub behave alike. `additionalContext` goes into the user context, so it can be dropped
when the context is compacted.

## PreToolUse — Edit/Write Gate + Reminder

`pre-tool-use.py`, matcher `Edit|Write|Read|Skill`. It has two roles.

- **Observation (Read/Skill)**: records which documents were Read and which skills were loaded in
  the session state file, and passes. A plugin skill (`plugin:skill`) is recorded under both names
- **Gate + reminder (Edit/Write)**: matches the file path against the `file-pattern-map.json`
  `rules`. If a matched rule has `requires` and they are unfulfilled, **blocks the edit with
  `permissionDecision: deny`** and says what to do. If they are fulfilled, injects the rule
  message as `additionalContext`

**Reading through the shell does not count** — opening it with `cat` or `sed` is invisible to the
hook. Only the `Read` tool and the `Skill` tool.

### Content Lint — Blocking What Needs No Judgment

An edit whose path matches a `content-lint.json` rule has its payload checked (`new_string` for
`Edit`, `content` for `Write`) and is **denied** on a hit. Two kinds of check per rule:

- `bannedChars` — a character that breaks a build or a toolchain. Declared as a hex code point,
  never as a literal, so the rule file stays readable whatever editor or codepage opens it
- `bannedLines` — a Python `re` regex searched in each line (case-sensitive; prefix `(?i)` for
  case-insensitive). `scope: "line"` reads the whole line, `scope: "comment"` reads only the
  comment span — from the earliest of the rule's `commentPrefixes` to the end of the line. A
  block-comment continuation line (` * ...`) has no prefix; catch it with a `line` entry such as
  `^\s*\*.*<pattern>`

```json
{
  "id": "unique ID",
  "patterns": ["*.h", "*.cpp"],
  "scopePath": ["src/"],
  "commentPrefixes": ["//", "/*"],
  "bannedChars": [
    { "codePoint": "2014", "name": "em dash (U+2014)", "replacement": "--" }
  ],
  "bannedLines": [
    { "regex": "^\\s*///", "scope": "line", "message": "Triple-slash comment" }
  ]
}
```

`patterns` · `scopePath` · `excludePath` behave exactly as they do in `file-pattern-map.json`, but
the two files are matched independently and the lint runs first: a banned character is banned
whether or not the file also has a guide to read first.

An entry that cannot be used (a bad code point, a regex that does not compile) is reported on
stderr and dropped; the rest of the rule keeps running. A `content-lint.json` that cannot be read
at all is reported and the lint is off for that edit.

**Only a violation that is never a judgment call belongs here** — one false positive permanently
blocks a legitimate edit. Anything that has to be read and weighed (a comment restating what the
name says, non-local information, a duplicated contract) is the commit-time comment audit's job.
The reverse promotion also holds: **a mechanical rule the reviewer keeps reporting round after
round belongs here**, where it costs nothing to enforce.

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
| `patterns` | File name or project-relative path wildcards, case-insensitive: `*` any run of characters (directory separators included), `?` one character, `[ab]` a set. `**` has no recursive meaning — constrain directories with `scopePath` |
| `scopePath` | (optional) The relative path must start with one of these prefixes to match |
| `excludePath` | (optional) Excluded when the relative path contains one of these substrings |
| `requires` | (optional) What must be fulfilled before editing. `reads` are project-relative paths, `skills` are skill names. Unfulfilled, the edit is **blocked** |
| `message` | The reminder injected once past the gate. **Never duplicate a rule summary** — it goes stale when the canon changes |

### Matching Behavior

- Several rules can match one file at once → all of them notify. `requires` are unioned
- The notification is **once per rule id per session**. The gate checks **on every edit** until it
  is fulfilled
- State files: `claude-code-hook-state/fired-rules-{session_id}.txt` ·
  `requires-done-{session_id}.txt` under the system temp directory (Python `tempfile`)
- Failures follow "How Far a Failure Is Surfaced" above — none of them blocks the edit

### requires Promotion Criteria

A new rule starts as a `message`, and is promoted to `requires` only when the instructions
declare that document "required / read fully before proceeding". **A requirement that does not
belong at edit time** (a pre-commit or pre-merge gate) is never hooked as `requires` — it blocks
the writing itself. A document required before an action goes into `commandRules` instead (below).

**Every `reads` path and `skills` name must exist.** With a typo, that entry can never be
satisfied and **nobody can edit that file.** After adding a rule, always confirm with
"Verification".

### Verification

Run the regression tests ("Tests" below), then check a real rule from `bash` (Git Bash on
Windows) with a `session_id` no real session has:

```bash
echo '{"session_id":"verify-1","tool_name":"Edit","tool_input":{"file_path":"<project absolute path>/<a file the rule matches>","new_string":"x"}}' | bash .claude/hooks/run-python-hook.sh pre-tool-use.py
```

On a match with requirements unfulfilled, `permissionDecision: deny` JSON, listing the `Read:` /
`Skill:` entries — compare each against a real file and skill. Send the matching `Read` / `Skill`
calls with the same `session_id` and re-run: `additionalContext` JSON. With no match, empty
output. An exit 1 with a stderr message means the gate did not run.

**Do not verify the content lint through a PowerShell pipe.** It re-encodes the payload and a
banned-character case comes back as a pass. A `bash` pipe passes the bytes through, which is how
Claude Code feeds the hook.

## PreToolUse — Command and MCP Tool Gate

`pre-tool-use-command.py` handles both matchers:

| Matcher | Rules read | Denies |
|---|---|---|
| `Bash\|PowerShell` | `file-pattern-map.json` `commandRules[]`, then `command-gate.json` `commands[]` | a command whose governing document has not been Read this session; then a command that omits one of its `requiredFlags` |
| `mcp__<server>__<tool>` | `command-gate.json` `mcpTools[]` | a call to `tool` whose input omits one of its `requiredFields` |

**Why these are hooks and not just documentation**: all three are reached through an autonomous
flow, where the document, slash-command or skill file that carries the rule is not in context. The
rule gets dropped and nothing notices until the artifact is already wrong. When a gate denies, use
the command the message points at rather than working around the flag; if a legitimate exception
appears, fix the rule.

### Command Matching

A command rule names its commands as **token sequences** (`"commands": ["git commit", "git worktree
add"]`). The whole sequence must match token for token; between its tokens only options (tokens
starting with `-`) and the values of **options registered as taking a value** may sit. So
`git -C <path> commit` matches `git commit`, while `git log --grep commit` and
`git --no-pager log --grep commit` do not — another subcommand sits in between.

**The list of value-taking options (`VALUE_OPTIONS`) lives in the hook code** — which commands to
gate is data, how to read option syntax is code. An option missing from the list that does take a
value lets its value be read as the next command word, and a read-only command is judged a write.
Gating a tool whose global options take values means extending that list.

Both shell gates check a normalized string, not the raw command. It is not a shell parser:

- A quoted span holding whitespace is **dropped** — a command written in output text
  (`echo "git push"`) runs nothing
- A quoted span with no whitespace has its quotes **peeled** — `git "push"` still runs `push`
- The contents of `$(...)` and backticks are **appended** — they run even inside double quotes.
  Not from inside single quotes, where no substitution happens: `echo '$(git push)'` only prints
- A gated executable (the first token of any rule) loses its path prefix and `.exe` —
  `git.exe`, `/usr/bin/git`, `"C:\tools\git.exe"` all match `git`
- Shell separators (`;` `|` `&` newline backtick) **outside quotes** become spaces, and grouping
  characters (`(` `)` `{` `}`) are stripped from both **ends** of a token — `git status;git push`
  and `(git push ...)` do not hide inside one token

  Splitting inside quotes too, or cutting brackets inside a token, would break a path holding that
  character (`git -C "F:/R&D" commit`) into several tokens and **let that command slip through** —
  closing one bypass by opening another.

Symptom: in a session that has not read the required document, one of these forms passes with no
deny.

A rule with no usable `commands` guards nothing, and is reported on every shell call instead of
being skipped. A `match` regex is the old rule format and is not read — rewrite it as `commands`.

### Command Read Gate

A command matching a `commandRules` entry whose documents have not been Read this session is
**denied**, and the reason lists what to read. It reads **the same session state file**
(`requires-done-*`) as the Edit/Write gate, so one Read opens both.

```json
{
  "id": "release",
  "commands": ["git tag", "npm publish"],
  "requires": { "reads": ["docs/release.md"] },
  "message": "pointer appended to the deny reason"
}
```

`requires` means what it means in the Edit/Write gate — `reads` and `skills` both work, and a typo
blocks that command forever. The read gate runs first: once the document is read, the flag gate
still denies a command that lacks its flags.

A document already injected at session start needs no entry — the gate counts only `Read` tool
calls, so it would make the agent read again what it already holds.

### Command Flag Gate

```json
{
  "id": "pr-create",
  "commands": ["gh pr create"],
  "requiredFlags": [{ "flag": "--base", "why": "shown in the deny reason" }],
  "message": "pointer appended to the deny reason"
}
```

A flag counts when a token equals it or starts with it plus `=` (`--base main`, `--base=main`);
`--base-branch` does not count as `--base`. A flag inside a quoted span that holds whitespace does
not count either.

### MCP Field Gate

```json
{
  "id": "issue-create",
  "tool": "mcp__tracker__issue_create",
  "requiredFields": [{ "field": "customFields.stage", "why": "shown in the deny reason" }],
  "message": "pointer appended to the deny reason"
}
```

A `field` may name a nested value with a dotted path. On the way, a JSON string is parsed (clients
send nested objects either way), and a list is searched for an item holding the segment as a key or
for a `{"name": ..., "value": ...}` pair whose name is the segment. A missing link, an empty string,
an empty list or object reads as missing.

A matcher for an MCP tool is the tool name itself, so **adding an `mcpTools` rule also means adding
a `PreToolUse` entry for that tool name in `settings.json`** — the rule alone never fires.

Verification — a call missing one required argument (or a gated command before its Read) must
produce deny JSON, a complete one empty output:

```bash
echo '{"session_id":"verify-1","tool_name":"Bash","tool_input":{"command":"<the guarded command, one flag removed>"}}' | bash .claude/hooks/run-python-hook.sh pre-tool-use-command.py
```

## UserPromptSubmit — Session-Length Signal

`user-prompt-submit-session-length.py` measures the transcript on every user prompt and injects
`[session length]` as `additionalContext` once the session is long. The canon for the rule is
`docs/workflow.md` "Session Length — When to Suggest a Handoff" — the hook only supplies the
signal, the agent decides whether to suggest the handoff.

**Why the hook measures it.** How much context has piled up is not visible inside the
conversation, and on a large-context model the context-remaining warning never fires. Left to the
agent's memory, the signal is gone in exactly the long session the rule is for.

| Measured | Source |
|---|---|
| Current context tokens | `usage` of the last main-chain (not `isSidechain`) assistant entry — input + cache_creation + cache_read |
| Compactions | `compact_boundary` entries |

**Counts of work done are not measured.** The cost grows with context size, not with review rounds
or commits, and the number of rounds is no reason to suggest a handoff.

Thresholds are the constants at the head of the script (`CONTEXT_SIGNAL_TOKENS` and the rest). The
first sits **well above the fixed context every session starts with** — project instructions, the
skill list and hook injections take a large share before the first prompt, and without headroom
the signal fires as soon as work begins. **Within one threshold it is injected once** — the levels
last emitted (which context step, how many compactions) are kept in
`~/.claude/tmp/session-length/<sha1(session_id)>.json`, and a new injection needs one of them to
rise to a higher level. That is what stops the same suggestion repeating on every prompt after the
user has chosen to continue. Parse and IO failures exit 0 (fail-open).

Verification — the transcript path is `~/.claude/projects/<project slug>/<session_id>.jsonl`:

```bash
echo '{"hook_event_name":"UserPromptSubmit","session_id":"test","transcript_path":"<a long session jsonl>"}' | bash .claude/hooks/run-python-hook.sh user-prompt-submit-session-length.py
```

Over the threshold, `additionalContext` JSON; called again with the same `session_id`, empty
output. Deleting the state file resets it.

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
echo '{"hook_event_name":"Stop","session_id":"t","prompt_id":"p1","last_assistant_message":"Committed the fix. I will check the build output next."}' | bash .claude/hooks/run-python-hook.sh stop-turn-end-gate.py; echo "exit=$?"
```

`exit=2` plus the reason. Called again with the same `prompt_id`, `exit=0`.

## Tests

```bash
python -m unittest discover -s .claude/hooks/tests -v
```

Run from the project root (with `python3` or `py -3` if that is the interpreter here). Each test
copies the hooks into a throwaway project under a temp directory — a path with spaces, non-ASCII
and the worktree shape — writes **its own** rule files there, and points `HOME` and the temp
directory at the same place. The project's real rules, session records and logs are not touched,
so the tests check the scripts; this project's rules are checked with the "Verification" commands.
The tests run each hook through `run-python-hook.sh`, including the launcher's fallback, version
probe, stdin passing and exit codes, so `bash` is required.

After changing a hook's behavior, add or adjust the test for it in the same change.

## File Encoding

- `*.py` hooks, `*.json` rule files, `*.md` headers: UTF-8. A BOM is tolerated on every file the
  hooks read; the JSON they write is UTF-8 bytes whatever the locale
- `run-python-hook.sh`: LF line endings — bash on Windows fails on a CRLF script

## Registering in settings

They are registered in `.claude/settings.json` (shared with the team), each with
`"shell": "bash"` and a command that goes through `run-python-hook.sh`. Right after editing
settings, open the `/hooks` menu once or restart for it to take effect.

Each event holds a **list** of entries, and each entry a list of commands, so several scripts can
run on one event — a second `Stop` script is appended next to the turn-end gate rather than folded
into it. A `PreToolUse` entry carries a `matcher`; the other events do not. `statusMessage` is what
the user sees in the terminal while that command runs; without one a slow hook looks like a hang.
