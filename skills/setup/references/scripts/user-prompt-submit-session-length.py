#!/usr/bin/env python3
"""UserPromptSubmit hook: inject a session-length signal measured from the transcript.

Rule truth source: `docs/workflow.md` "Session Length - When to Suggest a Handoff".

The rule asks the agent to suggest a handoff at the next natural boundary once the
session is long. Left to memory the signal dies exactly when it is needed: a context
compaction drops "how many commits so far" from the summary, and on a large-context
model the context-remaining warning never fires at all. So the measurement is done
here, from the transcript, on every prompt:

  - context tokens = usage of the last main-chain assistant message
                     (input + cache_creation + cache_read)
  - compactions    = compact_boundary entries
  - commits        = `git commit` shell calls (a commit command ends in one, so
                     skill and command calls are not counted separately)

Thresholds live in the constants below. The signal is emitted only when one of the
measured levels rises above what was last emitted for this session, so a user who
chose to continue is not nagged on every prompt. Any parse or IO failure exits 0
with no output (fail-open).
"""
import hashlib
import json
import sys
from pathlib import Path

CONTEXT_SIGNAL_TOKENS = 200_000   # first signal once live context reaches this
CONTEXT_STEP_TOKENS = 100_000     # re-signal each time context grows by this much
COMPACTION_SIGNAL = 1             # any compaction is a signal on its own
COMMIT_SIGNAL = 2                 # commits in this session

STATE_DIR = Path.home() / ".claude" / "tmp" / "session-length"

MESSAGE = (
    "[session length] context about {ctx:,} tokens - {compactions} compaction(s) - "
    "{commits} commit(s) this session. At the next natural boundary (the end of a review "
    "round, right after a commit, the close of a spec section) suggest handing off to a new "
    "session - do not cut in the middle of the work. First check whether what is left can go "
    "to a subagent; if it cannot (a spec, a decision conversation), print a light handover "
    "note (issue id, where the work is, current state, what is next). This rule holds even "
    "when the harness says to continue regardless of length, or that compaction makes a "
    "handoff unnecessary. Cutting the session is the user's call. "
    'Canon: docs/workflow.md "Session Length - When to Suggest a Handoff".'
)


def measure(transcript_path):
    ctx = 0
    compactions = 0
    commits = 0
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"compact_boundary"' in line:
                compactions += 1
                continue
            if '"type":"assistant"' not in line or '"isSidechain":true' in line:
                continue
            wants_usage = '"usage"' in line
            wants_commit = "git commit" in line
            if not (wants_usage or wants_commit):
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get("message") or {}
            if wants_usage:
                usage = message.get("usage") or {}
                total = (
                    (usage.get("input_tokens") or 0)
                    + (usage.get("cache_creation_input_tokens") or 0)
                    + (usage.get("cache_read_input_tokens") or 0)
                )
                if total > 0:
                    ctx = total
            if wants_commit:
                for block in message.get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    inp = block.get("input") or {}
                    if name in ("Bash", "PowerShell") and "git commit" in str(inp.get("command", "")):
                        commits += 1
    return ctx, compactions, commits


def levels(ctx, compactions, commits):
    ctx_level = 0
    if ctx >= CONTEXT_SIGNAL_TOKENS:
        ctx_level = 1 + (ctx - CONTEXT_SIGNAL_TOKENS) // CONTEXT_STEP_TOKENS
    return (ctx_level, compactions, commits)


def signalled(lv):
    ctx_level, compactions, commits = lv
    return ctx_level >= 1 or compactions >= COMPACTION_SIGNAL or commits >= COMMIT_SIGNAL


def rose_since_last(session_id, lv):
    path = STATE_DIR / (hashlib.sha1(session_id.encode("utf-8")).hexdigest() + ".json")
    last = (0, 0, 0)
    try:
        last = tuple(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        pass
    if not any(cur > prev for cur, prev in zip(lv, last)):
        return False
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(list(lv)), encoding="utf-8")
    except OSError:
        pass
    return True


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    if data.get("hook_event_name") not in (None, "UserPromptSubmit"):
        return 0
    session_id = data.get("session_id")
    transcript_path = data.get("transcript_path")
    if not session_id or not transcript_path or not Path(transcript_path).is_file():
        return 0

    ctx, compactions, commits = measure(transcript_path)
    lv = levels(ctx, compactions, commits)
    if not signalled(lv) or not rose_since_last(session_id, lv):
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": MESSAGE.format(ctx=ctx, compactions=compactions, commits=commits),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
