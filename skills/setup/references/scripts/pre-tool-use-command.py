"""PreToolUse hook for shell commands and MCP tool calls.

  Bash / PowerShell -> read gate: a command matching a file-pattern-map.json
                       "commandRules" entry is denied until its documents are read;
                       flag gate: a command matching a command-gate.json "commands"
                       entry is denied when it omits a required flag.
  mcp__* tools      -> field gate: a call matching a command-gate.json "mcpTools" entry
                       is denied when its input omits a required field.

All three guard the same failure: a call reached through an autonomous flow, where the
document, slash command or skill that carries the rule is not in context, so the rule is
dropped and nothing notices. Which failures are absorbed and which are reported:
.claude/hooks/README.md "How Far a Failure Is Surfaced".
"""
import json
import re
import sys

from hook_common import (done_entries, field, missing_requirements, read_rule_file, read_stdin,
                         report_failure, session_state, text, write_deny)


SOURCE = 'pre-tool-use-command'

# Options that take the next token as their value. Which commands to gate is data; how to
# read option syntax is code. An option missing here that does take a value lets its value
# be read as the next command word, and a read-only command is judged a write.
VALUE_OPTIONS = ('-c', '-C', '-R', '--git-dir', '--work-tree', '--repo')
SEPARATORS = re.compile(r'[;|&\n`]')
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
GROUPING = '(){}'
SUBSTITUTION = re.compile(r'\$\(([^()]*)\)|`([^`]*)`')


# ---- Normalization: the string both shell gates check ----

def keep_bare_word(match):
    """A quoted span with no whitespace still runs ("push"); one with whitespace is text."""
    inner = match.group(0)[1:-1]
    return inner if inner and not re.search(r'\s', inner) else ' '


def flatten(command, executables):
    """The command as the gates see it. Not a shell parser.

    - quoted spans holding whitespace are dropped (echo "git push" runs nothing); quotes
      around a bare word are peeled (git "push" runs push)
    - $(...) and backtick contents are appended, since they run even inside double quotes,
      but not from inside single quotes, where no substitution happens
    - separators outside quotes become spaces, so git status;git push splits; inside
      quotes they stay, so a path like "F:/R&D" does not split into several tokens
    - a path prefix and .exe are peeled off a gated executable (/usr/bin/git, git.exe)
    """
    outside_literals = re.sub(r"'[^']*'", ' ', command)
    substituted = ' '.join(part for match in SUBSTITUTION.finditer(outside_literals)
                           for part in match.groups() if part)
    pieces = []
    position = 0
    for match in QUOTED.finditer(command):
        pieces.append(SEPARATORS.sub(' ', command[position:match.start()]))
        pieces.append(keep_bare_word(match))
        position = match.end()
    pieces.append(SEPARATORS.sub(' ', command[position:]))
    pieces.append(' ' + SEPARATORS.sub(' ', substituted))
    flat = re.sub(r'\s+', ' ', ''.join(pieces)).strip()
    if not executables:
        return flat
    names = '|'.join(sorted((re.escape(name) for name in executables), key=len, reverse=True))
    executable = re.compile(r'(?<![\w-])(?:\S*[/\\])?(' + names + r')(?:\.exe)?(?=\s|$)', re.I)
    return executable.sub(lambda match: match.group(1), flat)


def tokens_of(flat):
    return [token.strip(GROUPING) for token in flat.split()]


def skip_options(tokens, index, expected):
    while index < len(tokens) and tokens[index].startswith('-'):
        option = tokens[index]
        index += 1
        if option in VALUE_OPTIONS and index < len(tokens) and tokens[index].lower() != expected:
            index += 1
    return index


def sequence_matches(wanted, tokens):
    """The token sequence appears in order, with only options (and their values) between."""
    for start in range(len(tokens)):
        if tokens[start].lower() != wanted[0]:
            continue
        index = start + 1
        for expected in wanted[1:]:
            index = skip_options(tokens, index, expected)
            if index >= len(tokens) or tokens[index].lower() != expected:
                break
            index += 1
        else:
            return True
    return False


def sequences(rule):
    return [[token.lower() for token in text(command).split()] for command in field(rule, 'commands', []) or []
            if text(command).split()]


def rule_matches(rule, tokens):
    return any(sequence_matches(wanted, tokens) for wanted in sequences(rule))


def usable_command_rules(rules, file_name):
    """Rules with at least one command sequence. Any other rule is reported, not silently skipped."""
    usable = []
    broken = False
    for rule in rules:
        if sequences(rule):
            usable.append(rule)
            continue
        broken = True
        hint = ' (a "match" regex is not read -- list the command as "commands": ["word word"])' \
            if field(rule, 'match') is not None else ''
        report_failure(SOURCE, '{0} rule {1} has no "commands", it guards nothing{2}'.format(
            file_name, text(field(rule, 'id')) or '<no id>', hint))
    return usable, broken


# ---- Shell gates ----

def read_gate(data, tokens, rules):
    """Deny a command whose commandRules documents have not been read. True when denied."""
    matched = [rule for rule in rules if rule_matches(rule, tokens)]
    if not matched:
        return False
    try:
        done_file, _ = session_state(field(data, 'session_id'))
        done = done_entries(done_file)
    except Exception as error:
        report_failure(SOURCE, 'session state unavailable, the command read gate did NOT run: {0}'.format(error))
        sys.exit(1)
    missing = []
    for rule in matched:
        missing += missing_requirements(done, field(rule, 'requires'))
    if not missing:
        return False
    write_deny('PreToolUse', '\n'.join([
        'This command is gated: the process document that governs it has not been read in this session.',
        'Do these first, then retry the command:',
        *('  - ' + item for item in dict.fromkeys(missing)),
        *('  ' + text(field(rule, 'message')) for rule in matched if text(field(rule, 'message')).strip()),
        'Use the Read tool -- reading a doc through a shell command does not count.',
    ]))
    return True


def has_flag(tokens, flag):
    flag = flag.lower()
    return any(token.lower() == flag or token.lower().startswith(flag + '=') for token in tokens)


def flag_gate(tokens, rules):
    """Deny a command that omits a required flag. True when denied."""
    for rule in rules:
        if not rule_matches(rule, tokens):
            continue
        missing = ['  {0} - {1}'.format(text(field(item, 'flag')), text(field(item, 'why')))
                   for item in field(rule, 'requiredFlags', []) or []
                   if text(field(item, 'flag')).strip() and not has_flag(tokens, text(field(item, 'flag')))]
        if not missing:
            continue
        reason = ['Blocked: this command is missing arguments the project requires.', '', *missing]
        if text(field(rule, 'message')).strip():
            reason += ['', text(field(rule, 'message'))]
        write_deny('PreToolUse', '\n'.join(reason))
        return True
    return False


def shell(data, gate_root):
    """(denied, a rule was unusable)."""
    command = text(field(field(data, 'tool_input'), 'command'))
    if not command.strip():
        return False, False
    try:
        map_root = read_rule_file('file-pattern-map.json', required=True)
    except Exception as error:
        report_failure(SOURCE, 'file-pattern-map.json unavailable, the command read gate did NOT run: '
                               '{0}'.format(error))
        sys.exit(1)
    read_rules, read_broken = usable_command_rules(field(map_root, 'commandRules', []) or [],
                                                   'file-pattern-map.json commandRules')
    flag_rules, flag_broken = usable_command_rules(field(gate_root, 'commands', []) or [],
                                                   'command-gate.json commands')
    executables = {wanted[0] for rule in read_rules + flag_rules for wanted in sequences(rule)}
    tokens = tokens_of(flatten(command, executables))
    denied = read_gate(data, tokens, read_rules) or flag_gate(tokens, flag_rules)
    return denied, read_broken or flag_broken


# ---- MCP field gate ----

def value_at(root, path):
    """Follow a dotted path into the tool input.

    A JSON string on the way is parsed (clients send nested objects either way). A list
    is searched for an item holding the segment as a key, or for a {"name", "value"} pair
    whose name is the segment. A missing link returns None, which reads as "missing".
    """
    node = root
    for segment in path.split('.'):
        if isinstance(node, str):
            try:
                node = json.loads(node)
            except ValueError:
                return None
        if isinstance(node, dict):
            node = field(node, segment)
        elif isinstance(node, list):
            found = None
            for item in node:
                if field(item, segment) is not None:
                    found = field(item, segment)
                    break
                if text(field(item, 'name')).lower() == segment.lower():
                    found = field(item, 'value')
                    break
            node = found
        else:
            return None
    return node


def has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def mcp(data, tool, gate_root):
    tool_input = field(data, 'tool_input')
    for rule in field(gate_root, 'mcpTools', []) or []:
        if text(field(rule, 'tool')).lower() != tool or tool_input is None:
            continue
        missing = ['  {0} - {1}'.format(text(field(item, 'field')), text(field(item, 'why')))
                   for item in field(rule, 'requiredFields', []) or []
                   if text(field(item, 'field')).strip()
                   and not has_value(value_at(tool_input, text(field(item, 'field'))))]
        if not missing:
            continue
        reason = ['Blocked: this tool call is missing fields the project requires.', '', *missing]
        if text(field(rule, 'message')).strip():
            reason += ['', text(field(rule, 'message'))]
        write_deny('PreToolUse', '\n'.join(reason))
        return


def main():
    try:
        data = json.loads(read_stdin())
    except Exception:
        return
    tool = text(field(data, 'tool_name')).lower()
    if not tool:
        return
    is_shell = tool in ('bash', 'powershell')
    if not is_shell and not tool.startswith('mcp__'):
        return
    broken_gate = False
    try:
        gate_root = read_rule_file('command-gate.json')
    except Exception as error:
        report_failure(SOURCE, 'command-gate.json is present but unusable, the flag and field gates did '
                               'NOT run: {0}'.format(error))
        if not is_shell:
            sys.exit(1)
        gate_root, broken_gate = None, True
    if not is_shell:
        mcp(data, tool, gate_root)
        return
    # The read gate still runs on a broken command-gate.json. Exit 1 only without a deny:
    # Claude Code reads the deny JSON on exit 0 alone.
    denied, broken = shell(data, gate_root)
    if not denied and (broken or broken_gate):
        sys.exit(1)


if __name__ == '__main__':
    main()
