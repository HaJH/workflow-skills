"""Shared plumbing for the PreToolUse and SessionStart hooks.

UTF-8 JSON in and out (a BOM is tolerated on every read), case-insensitive field access,
project-relative paths, the per-session state files, and the one diagnostic channel.
Nothing here swallows an exception: each hook decides which failures it absorbs, per
.claude/hooks/README.md "How Far a Failure Is Surfaced".
"""
import json
from pathlib import Path
import re
import sys
import tempfile


HOOKS = Path(__file__).resolve().parent
ROOT = HOOKS.parents[1]


def read_stdin():
    return sys.stdin.buffer.read().decode('utf-8-sig', errors='replace')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig', errors='replace'))


def read_rule_file(name, required=False):
    """A rule file next to the hooks.

    Absent: None, unless the file is required, which raises. Present but unreadable or
    not a JSON object: raises. "Absent" and "broken" stay distinct so an optional rule
    file can be left out without every call reporting it.
    """
    path = HOOKS / name
    if not path.exists() and not required:
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError('{0} is not a JSON object'.format(name))
    return data


def field(value, name, default=None):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() == name.lower():
                return item
    return default


def text(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return ' '.join(text(item) for item in value)
    return str(value)


def relative_path(value):
    """Project-relative path, forward slashes.

    The worktree convention <parent>/<Repo>-worktrees/<folder>/<rel> is recognized first:
    those paths share a string prefix with the main tree and would otherwise be cut into
    "-worktrees/...", and every rule would miss.
    """
    path = text(value)
    if not path.strip():
        return ''
    path = path.replace('\\', '/')
    worktree = re.search(r'/[^/]+-worktrees/[^/]+/(.+)$', path, re.I)
    if worktree:
        return worktree[1]
    root = str(ROOT).replace('\\', '/').rstrip('/')
    if path.lower().startswith((root + '/').lower()):
        return path[len(root) + 1:]
    return path


def read_lines(path):
    try:
        return path.read_text(encoding='utf-8-sig', errors='replace').splitlines()
    except OSError:
        return []


def add_line(path, value):
    existing = read_lines(path)
    if value.lower() in [item.lower() for item in existing]:
        return
    path.write_text('\n'.join(dict.fromkeys(existing + [value])) + '\n', encoding='utf-8')


def session_state(session_id):
    """(requires-done file, fired-rules file) for the session. Raises if unavailable."""
    session = text(session_id)
    if not session.strip():
        session = 'noid'
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', session)
    state = Path(tempfile.gettempdir()) / 'claude-code-hook-state'
    state.mkdir(parents=True, exist_ok=True)
    return state / f'requires-done-{safe}.txt', state / f'fired-rules-{safe}.txt'


def done_entries(done_file):
    return [item.lower() for item in read_lines(done_file)]


def missing_requirements(done, requires):
    missing = []
    for doc in field(requires, 'reads', []) or []:
        if 'read:' + text(doc).lower() not in done:
            missing.append('Read: ' + text(doc))
    for skill in field(requires, 'skills', []) or []:
        if 'skill:' + text(skill).lower() not in done:
            missing.append('Skill: ' + text(skill))
    return missing


def report_failure(source, detail):
    """The one diagnostic channel: UTF-8 bytes on stderr, whatever the locale."""
    sys.stderr.buffer.write('{0}: {1}\n'.format(source, detail).encode('utf-8', 'replace'))
    sys.stderr.buffer.flush()


def write_output(event, **values):
    payload = {'hookSpecificOutput': {'hookEventName': event, **values}}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    sys.stdout.buffer.flush()


def write_deny(event, reason):
    write_output(event, permissionDecision='deny', permissionDecisionReason=reason)
