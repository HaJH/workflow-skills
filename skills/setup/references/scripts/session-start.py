"""SessionStart / SubagentStart hook: inject project context as additionalContext.

The same script is registered for both events so a subagent sees the project context
the main session sees -- a subagent inherits neither CLAUDE.md nor the parent's
SessionStart context, and this hook is the official path that reaches it.

Layers (token efficiency):
  - always (main + sub): session-start-header.md -- repeat-violation traps + the index
    of documents to read on demand
  - main session only: main-session-header.md -- every rule there faces the user, and a
    subagent neither sees the user nor holds the question tool; injected into one, it
    appends a turn-end block to that agent's own output format and corrupts whatever
    downstream stage parses it
  - on demand (not injected): everything the header index points at. docs/workflow.md is
    one of them -- it is too long to arrive whole, so the read gates ask for it right
    before the commands and edits it governs

Right after a compaction (SessionStart with source "compact") the session's gate records
are cleared: the compaction dropped the documents' content, so the gates must ask again.
"""
import argparse
import json

from hook_common import ROOT, field, read_stdin, report_failure, session_state, text, write_output


COMMON = ['.claude/hooks/session-start-header.md']
MAIN_ONLY = ['.claude/hooks/main-session-header.md']


def clear_compacted_state():
    """Failures of the reset, one line each. Every record is attempted."""
    try:
        data = json.loads(read_stdin())
    except Exception:
        return []
    if text(field(data, 'source')).lower() != 'compact':
        return []
    try:
        paths = session_state(field(data, 'session_id'))
    except Exception as error:
        return ['session state directory unavailable: {0}'.format(error)]
    failures = []
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as error:
            failures.append('{0}: {1}'.format(path.name, error))
    return failures


def failure_section(failures):
    return ('=== compact state reset FAILED ===\n'
            'These session records could not be removed, so the read gates may still count '
            'documents whose content this session has lost. Read the documents you need again.\n'
            + ''.join('  - ' + item + '\n' for item in failures) + '\n\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hook-event-name', choices=('SessionStart', 'SubagentStart'), default='SessionStart')
    try:
        event = parser.parse_args().hook_event_name
    except SystemExit as error:
        raise SystemExit(1 if error.code else 0) from None
    files = list(COMMON)
    failures = []
    if event != 'SubagentStart':
        failures = clear_compacted_state()
        files += MAIN_ONLY
    sections = []
    if failures:
        # Reported, but the injection goes on: dropping it would lose the whole context.
        sections.append(failure_section(failures))
        report_failure('session-start', 'compact state reset failed: ' + '; '.join(failures))
    for relative in files:
        path = ROOT / relative
        if path.exists():
            sections.append('=== {0} ===\n{1}\n\n'.format(
                relative, path.read_text(encoding='utf-8-sig', errors='replace')))
        else:
            sections.append('=== {0} (missing) ===\n\n'.format(relative))
    write_output(event, additionalContext=''.join(sections))


if __name__ == '__main__':
    main()
