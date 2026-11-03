"""PreToolUse hook (Edit|Write|Read|Skill).

  Read / Skill  -> record that a document was read or a skill loaded this session.
  Edit / Write  -> lint the text being written (content-lint.json), gate the edit on the
                   "requires" of every matched file-pattern-map.json rule, then remind.

Reminders fire at most once per rule per session; the gate is checked on every edit
until it is satisfied. Which failures are absorbed and which are reported:
.claude/hooks/README.md "How Far a Failure Is Surfaced".
"""
import fnmatch
import json
import re
import sys

from hook_common import (add_line, done_entries, field, missing_requirements, read_rule_file,
                         read_stdin, relative_path, report_failure, session_state, text,
                         write_deny, write_output)


SOURCE = 'pre-tool-use'


def like(value, pattern):
    return fnmatch.fnmatchcase(value.lower(), text(pattern).lower())


def matches(rule, relative):
    """Shared by both rule files. A rule with no patterns never matches."""
    patterns = field(rule, 'patterns') or []
    if not patterns:
        return False
    scopes = field(rule, 'scopePath')
    if scopes and not any(like(relative, text(scope) + '*') for scope in scopes):
        return False
    excludes = field(rule, 'excludePath')
    if excludes and any(like(relative, '*' + text(excluded) + '*') for excluded in excludes):
        return False
    name = relative.rsplit('/', 1)[-1]
    return any(like(name, pattern) or like(relative, pattern) for pattern in patterns)


def comment_span(line, prefixes):
    """From the earliest comment prefix to the end of the line, or ''."""
    starts = [line.find(prefix) for prefix in prefixes if prefix]
    starts = [start for start in starts if start >= 0]
    return line[min(starts):] if starts else ''


def compile_rule(rule):
    """(banned characters, banned line checks, comment prefixes) of one lint rule.

    A malformed entry is reported and dropped; the rest of the rule keeps running.
    """
    rule_id = text(field(rule, 'id')) or '<no id>'
    characters = []
    for item in field(rule, 'bannedChars') or []:
        try:
            point = int(text(field(item, 'codePoint')), 16)
            character = chr(point)
        except (TypeError, ValueError, OverflowError) as error:
            report_failure(SOURCE, 'content-lint rule {0}: unusable bannedChars entry {1}, that '
                                   'check is OFF: {2}'.format(rule_id, json.dumps(item), error))
            continue
        fix = text(field(item, 'name')) or 'U+{0:04X}'.format(point)
        if text(field(item, 'replacement')).strip():
            fix += " -> '" + text(field(item, 'replacement')) + "'"
        characters.append((character, fix))
    lines = []
    for item in field(rule, 'bannedLines') or []:
        try:
            pattern = re.compile(text(field(item, 'regex')))
            if not pattern.pattern:
                raise ValueError('empty regex')
        except (re.error, ValueError) as error:
            report_failure(SOURCE, 'content-lint rule {0}: unusable bannedLines entry {1}, that '
                                   'check is OFF: {2}'.format(rule_id, json.dumps(item), error))
            continue
        lines.append((pattern, text(field(item, 'scope')).lower() == 'comment', text(field(item, 'message'))))
    prefixes = [text(prefix) for prefix in field(rule, 'commentPrefixes') or []]
    return characters, lines, prefixes


def lint(relative, payload):
    """Violations in the payload. A broken content-lint.json turns the lint off, loudly."""
    try:
        root = read_rule_file('content-lint.json')
    except Exception as error:
        report_failure(SOURCE, 'content-lint.json is present but unusable, the content lint is '
                               'OFF for this edit: {0}'.format(error))
        return []
    rules = [rule for rule in field(root, 'rules', []) or [] if matches(rule, relative)]
    if not rules or not payload:
        return []
    found = []
    for rule in rules:
        characters, checks, prefixes = compile_rule(rule)
        found += ['Banned character: ' + fix for character, fix in characters if character in payload]
        if not checks:
            continue
        for raw_line in payload.split('\n'):
            line = raw_line.rstrip('\r')
            comment = comment_span(line, prefixes)
            for pattern, comment_only, message in checks:
                subject = comment if comment_only else line
                if subject and pattern.search(subject):
                    found.append(message + ': ' + subject.strip())
    return list(dict.fromkeys(found))


def record(done_file, entries, what):
    try:
        for entry in entries:
            add_line(done_file, entry)
    except Exception as error:
        report_failure(SOURCE, 'could not record {0}, gates that require it will keep blocking: '
                               '{1}'.format(what, error))
        sys.exit(1)


def main():
    try:
        data = json.loads(read_stdin())
    except Exception:
        return
    tool = text(field(data, 'tool_name')).lower()
    if tool not in ('edit', 'write', 'read', 'skill'):
        return
    tool_input = field(data, 'tool_input')
    try:
        done_file, fired_file = session_state(field(data, 'session_id'))
    except Exception as error:
        report_failure(SOURCE, 'session state unavailable, the edit gate did NOT run: {0}'.format(error))
        sys.exit(1)

    # ---- Observation: record consumed documents and skills, never block ----
    if tool == 'read':
        relative = relative_path(field(tool_input, 'file_path'))
        if relative.strip():
            record(done_file, ['read:' + relative.lower()], 'the read of ' + relative)
        return
    if tool == 'skill':
        skill = text(field(tool_input, 'skill'))
        if skill.strip():
            # Plugin skills arrive as "plugin:skill"; record the bare name too.
            record(done_file, ['skill:' + skill.lower(), 'skill:' + skill.split(':')[-1].lower()],
                   'the load of skill ' + skill)
        return

    # ---- Edit / Write ----
    relative = relative_path(field(tool_input, 'file_path'))
    if not relative.strip():
        return

    # Content lint first and independently of the rule map: a banned character is banned
    # whether or not the file also has a guide to read first.
    violations = lint(relative, text(field(tool_input, 'new_string' if tool == 'edit' else 'content')))
    if violations:
        write_deny('PreToolUse', '\n'.join([
            'This edit is blocked: it writes something the project forbids outright.',
            *('  - ' + item for item in violations),
            'Rewrite the edit without it, then retry.',
            'These are not judgment calls and have no exception to argue for.',
        ]))
        return

    try:
        rules = field(read_rule_file('file-pattern-map.json', required=True), 'rules') or []
    except Exception as error:
        report_failure(SOURCE, 'file-pattern-map.json unavailable, the edit gate did NOT run: {0}'.format(error))
        sys.exit(1)
    matched = [rule for rule in rules if matches(rule, relative)]
    if not matched:
        return

    done = done_entries(done_file)
    missing = []
    for rule in matched:
        missing += missing_requirements(done, field(rule, 'requires'))
    if missing:
        write_deny('PreToolUse', '\n'.join([
            'This edit is gated: required project guides have not been loaded in this session.',
            'Do these first, then retry the edit:',
            *('  - ' + item for item in dict.fromkeys(missing)),
            'They carry the rules this edit must follow.',
            'Use the Read tool and the Skill tool -- reading a doc through a shell command does not count.',
        ]))
        return

    fired = done_entries(fired_file)
    fresh = [rule for rule in matched if text(field(rule, 'id')).lower() not in fired]
    if not fresh:
        return
    try:
        for rule in fresh:
            add_line(fired_file, text(field(rule, 'id')))
    except Exception:
        pass  # Costs one repeated reminder at most.
    write_output('PreToolUse', additionalContext='\n'.join([
        'Project guide reminders (first match this session):',
        *('[{0}] {1}'.format(text(field(rule, 'id')), text(field(rule, 'message'))) for rule in fresh),
    ]))


if __name__ == '__main__':
    main()
