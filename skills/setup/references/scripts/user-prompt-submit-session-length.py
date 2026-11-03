#!/usr/bin/env python3
"""UserPromptSubmit hook: inject a session-length signal measured from the transcript.

Rule truth source: `docs/workflow.md` "Session Length — When to Suggest a Handoff".

The rule asks the agent to suggest a handoff at the next natural boundary once the
session is long. Left to memory the signal dies exactly when it is needed: how much
context has piled up is not visible inside the conversation, and on a large-context
model the context-remaining warning never fires. So the measurement is done here, from
the transcript, on every prompt:

  - context tokens = usage of the last main-chain assistant message
                     (input + cache_creation + cache_read)
  - compactions    = compact_boundary entries

Context size is the only length proxy measured, because it is what the cost grows with.
Counts of work done are not: a spec session that commits once per review round is the
case the rule says to keep going, so the number of rounds or commits is not a reason to
suggest a handoff. The first threshold also sits well above the context every session
already starts with -- project instructions, the skill list and hook injections cost a
large fixed amount before the first prompt arrives.

Thresholds live in the constants below. The signal is emitted only when one of the
measured levels rises above what was last emitted for this session, so a user who chose
to continue is not nagged on every prompt. Any parse or IO failure exits 0 with no
output (fail-open).
"""
import hashlib
import json
import sys
from pathlib import Path

CONTEXT_SIGNAL_TOKENS = 500_000   # first signal once live context reaches this
CONTEXT_STEP_TOKENS = 250_000     # re-signal each time context grows by this much
COMPACTION_SIGNAL = 1             # any compaction is a signal on its own

STATE_DIR = Path.home() / ".claude" / "tmp" / "session-length"

MESSAGE = (
    "[session length] context about {ctx:,} tokens - {compactions} compaction(s). "
    "At the next natural boundary (the end of a review round, right after a commit, the "
    "close of a spec section) suggest a new session in one line. "
    'Canon: docs/workflow.md "Session Length — When to Suggest a Handoff".'
)


def measure(transcript_path):
    ctx = 0
    compactions = 0
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"compact_boundary"' in line:
                compactions += 1
                continue
            if '"type":"assistant"' not in line or '"isSidechain":true' in line:
                continue
            if '"usage"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            usage = (entry.get("message") or {}).get("usage") or {}
            total = (
                (usage.get("input_tokens") or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
                + (usage.get("cache_read_input_tokens") or 0)
            )
            if total > 0:
                ctx = total
    return ctx, compactions


def levels(ctx, compactions):
    ctx_level = 0
    if ctx >= CONTEXT_SIGNAL_TOKENS:
        ctx_level = 1 + (ctx - CONTEXT_SIGNAL_TOKENS) // CONTEXT_STEP_TOKENS
    return (ctx_level, compactions)


def signalled(lv):
    ctx_level, compactions = lv
    return ctx_level >= 1 or compactions >= COMPACTION_SIGNAL


def rose_since_last(session_id, lv):
    path = STATE_DIR / (hashlib.sha1(session_id.encode("utf-8")).hexdigest() + ".json")
    last = (0, 0)
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

    ctx, compactions = measure(transcript_path)
    lv = levels(ctx, compactions)
    if not signalled(lv) or not rose_since_last(session_id, lv):
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": MESSAGE.format(ctx=ctx, compactions=compactions),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
