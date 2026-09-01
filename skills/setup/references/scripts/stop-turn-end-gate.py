#!/usr/bin/env python3
"""Stop hook: block a turn that promises a next action but names no resume condition.

Rule truth source: `.claude/hooks/main-session-header.md` "Resume Condition".

The gate is two-sided on purpose. A promise phrase alone never blocks - it blocks
only when the ending also fails to name what would restart the work. Writing the
"Resume condition:" line, or asking the user something, always passes, so a
legitimate ending escapes with one line instead of fighting the hook.

Patterns cover English and Korean because generated documents are English while
agent responses follow the user's language. Add a language by appending to
PROMISE_PATTERNS, RESUME_RE and ASK_PATTERNS together - a promise pattern with no
matching escape hatch blocks every turn in that language.

False-positive containment:
  - reads `last_assistant_message` only; the transcript file lags the live turn
  - quoted / fenced / table / blockquote regions are stripped before matching
    (a turn that documents this very rule must not trip it)
  - only the tail of the message is scanned - a mid-message "let me check"
    followed by the check itself is not the failure this gate is after
  - at most one block per `prompt_id`, so a false positive costs one turn
  - any parse or IO failure exits 0 (fail-open)
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

TAIL_CHARS = 900
STATE_DIR = Path.home() / ".claude" / "tmp" / "stop-turn-end-gate"
LOG_PATH = Path.home() / ".claude" / "logs" / "stop-turn-end-gate.jsonl"

FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
DQUOTE_RE = re.compile(r"[\"“「『][^\"”」』\n]{0,300}[\"”」』]")
DROP_LINE_RE = re.compile(r"^[ \t]*(\||>|#{1,6}[ \t]).*$", re.M)

_NEXT_VERB = (
    r"check|verify|review|report|continue|proceed|start|begin|run|fix|update|"
    r"commit|push|create|add|remove|delete|test|build|merge|wait|monitor|watch|"
    r"poll|investigate|confirm|resume|dispatch|follow\s+up|look\s+into|kick\s+off"
)

# Sentence-final first-person promises of a NEXT action. English past tense uses
# different words, so it needs no exclusion; the Korean lookaheads drop the
# past-tense endings so a report of work already done passes.
PROMISE_PATTERNS = [
    ("en-i-will", r"\b(?:I['’]?ll|I\s+will|I['’]?m\s+going\s+to)\s+"
                  r"(?:\w+\s+){0,3}(?:" + _NEXT_VERB + r")\b"),
    ("en-let-me", r"\bLet\s+me\s+(?:\w+\s+){0,3}(?:" + _NEXT_VERB + r")\b"),
    ("en-continuing", r"\b(?:Continuing|Proceeding|Moving)\s+(?:with|to|on\s+to|onto)\b"),
    ("en-next-i", r"\bNext,?\s+(?:I['’]?ll|I\s+will)\b"),
    ("en-in-n-minutes", r"\bin\s+(?:a\s+few|another|\d+)\s+(?:seconds|minutes|hours)\b"
                        r"[\s\S]{0,40}?\b(?:I['’]?ll|check|report|confirm)\b"),
    ("en-shortly", r"\b(?:shortly|in\s+a\s+moment|momentarily)\b"
                   r"[\s\S]{0,40}?\b(?:I['’]?ll|check|report)\b"),
    ("ko-이어서-진행", r"이어서\s*진행(?!했|한|하여|해서|하고|함)"),
    ("ko-바로-이어", r"바로\s*이어(?!받|서\s*진행했)"),
    ("ko-계속-진행", r"계속\s*(해서\s*)?진행(?!했|한|하여|해서|하고|함)"),
    ("ko-겠습니다", r"(확인|점검|조회|검토|보고|정리|반영|처리|수정|작성|실행|시작|재개|진입|전환"
                    r"|호출|등록|커밋|푸시|생성|추가|삭제|테스트|빌드|리뷰|머지|대기|감시|추적)"
                    r"\s*(해\s*두?|하)?겠습니다"),
    ("ko-하겠다", r"(확인|점검|조회|검토|처리|반영|진행|작업|정리|보고)하겠(다|음)"),
    ("ko-다음-하겠", r"다음\s*\S{0,15}(하|진행하|넘어가|착수하)겠"),
    ("ko-곧-하겠", r"곧\s*\S{0,15}겠습니다"),
    ("ko-잠시-후", r"(잠시\s*후|이따가?|조금\s*(뒤|후))\s*\S{0,15}(확인|보고|진행|점검|조회)"),
    ("ko-N분-뒤", r"\d+\s*(분|초|시간)\s*(뒤|후)에?\s*\S{0,15}(확인|보고|점검|조회|재개)"),
]

# The escape hatch has to name what would restart the work, or the words "resume
# condition" alone become a phrase that passes the gate while promising nothing.
RESUME_RE = re.compile(
    r"(resume\s*condition|resumes?\s+when|resuming\s+on|재개\s*조건)"
    r"[\s\S]{0,120}?"
    r"(user|background|notification|wakeup|Monitor|Cron|사용자|백그라운드)",
    re.I,
)

ASK_PATTERNS = [
    r"\bplease\s+\w+", r"\blet\s+me\s+know\b", r"\b(?:could|can|would|will)\s+you\b",
    r"\btell\s+me\b", r"\byour\s+call\b", r"\bwhich\s+(?:one|of|would)\b",
    r"\bwaiting\s+for\s+(?:your|the\s+user)\b",
    r"해\s*주세요", r"해주세요", r"주시면", r"주십시오", r"알려\s*주", r"알려주",
    r"확인\s*부탁", r"말씀해\s*주", r"골라\s*주", r"선택해\s*주", r"결정해\s*주",
]
ASK_RE = re.compile("|".join(ASK_PATTERNS), re.I)
QUESTION_TAIL_RE = re.compile(r"[?？]\s*$")

REASON = """[turn-end gate] The last message promised a next action (pattern: {pattern}) \
but named no resume condition.

If it is something you can do in this turn, do not write it - do it now.
If you cannot, put one "Resume condition:" line in the closing report and name one of:
  - a user message
  - a background completion notification
  - a registered wakeup
The last two may be written only after a background task or a wakeup/monitor has
actually been registered. If you need user input, write that request as one sentence
and stop.

Canon: `.claude/hooks/main-session-header.md` "Resume Condition".
This gate blocks at most once per prompt."""


def strip_quoted(text):
    text = FENCE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = DQUOTE_RE.sub(" ", text)
    return DROP_LINE_RE.sub(lambda m: "\x00", text)


def find_promise(text):
    for name, pattern in PROMISE_PATTERNS:
        if re.search(pattern, text):
            return name
    return None


def asks_user(text):
    if ASK_RE.search(text):
        return True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return bool(lines) and bool(QUESTION_TAIL_RE.search(lines[-1]))


def already_blocked(session_id, prompt_id):
    path = STATE_DIR / (hashlib.sha1(session_id.encode("utf-8")).hexdigest() + ".txt")
    try:
        if path.read_text(encoding="utf-8").strip() == prompt_id:
            return True
    except OSError:
        pass
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt_id, encoding="utf-8")
    except OSError:
        pass
    return False


def log_block(session_id, prompt_id, pattern, excerpt):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "session_id": session_id,
            "prompt_id": prompt_id,
            "pattern": pattern,
            "excerpt": excerpt,
        }
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main():
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0

    if data.get("hook_event_name") not in (None, "Stop"):
        return 0

    message = data.get("last_assistant_message")
    if not isinstance(message, str) or not message.strip():
        return 0

    # No prompt_id means no loop guard, so the gate stands down entirely.
    prompt_id = data.get("prompt_id")
    session_id = data.get("session_id")
    if not prompt_id or not session_id:
        return 0

    if RESUME_RE.search(message):
        return 0

    tail = strip_quoted(message)[-TAIL_CHARS:]
    pattern = find_promise(tail)
    if not pattern:
        return 0
    if asks_user(tail):
        return 0

    if already_blocked(session_id, prompt_id):
        return 0

    log_block(session_id, prompt_id, pattern, message[-300:])
    sys.stderr.write(REASON.format(pattern=pattern) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
