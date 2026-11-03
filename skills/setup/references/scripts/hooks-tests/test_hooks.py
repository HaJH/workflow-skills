"""Regression tests for the hooks in .claude/hooks.

Run from the project root:  python -m unittest discover -s .claude/hooks/tests -v

Each test copies the hook scripts into a throwaway project under a temp directory whose
path holds spaces, non-ASCII and the worktree shape, writes its own rule files there,
and points HOME / TEMP at the same place -- the project's real rule files, session
records and logs are never read or touched. Hooks run through run-python-hook.sh the way
settings.json runs them, so bash is required.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[1]
SETTINGS = HOOKS.parent / 'settings.json'
BASH = shutil.which('bash')

MAP = {
    'commandRules': [
        {'id': 'git-write', 'commands': ['git commit', 'git push', 'git worktree add'],
         'requires': {'reads': ['docs/git.md']}, 'message': 'git pointer'},
    ],
    'rules': [
        {'id': 'src', 'patterns': ['*.cpp', '*.h'], 'scopePath': ['src/'], 'excludePath': ['vendor/'],
         'requires': {'reads': ['guide.md'], 'skills': ['lang-guide']}, 'message': '한글 안내'},
        {'id': 'docs', 'patterns': ['*.md'], 'scopePath': ['docs/'], 'message': 'docs reminder'},
    ],
}
LINT = {
    'rules': [
        {'id': 'cpp', 'patterns': ['*.cpp', '*.h'], 'scopePath': ['src/'], 'commentPrefixes': ['//', '/*'],
         'bannedChars': [{'codePoint': '2014', 'name': 'em dash (U+2014)', 'replacement': '--'}],
         'bannedLines': [{'regex': '^\\s*///', 'scope': 'line', 'message': 'Triple-slash comment'},
                         {'regex': '[A-Z]+-[0-9]+', 'scope': 'comment', 'message': 'Issue ID in a comment'}]},
    ],
}
GATE = {
    'commands': [
        {'id': 'pr', 'commands': ['gh pr create'],
         'requiredFlags': [{'flag': '--base', 'why': 'base why'}, {'flag': '--repo', 'why': 'repo why'}],
         'message': 'use /merge-branch'},
    ],
    'mcpTools': [
        {'id': 'issue', 'tool': 'mcp__tracker__issue_create',
         'requiredFields': [{'field': 'sprint', 'why': 'sprint why'},
                            {'field': 'customFields.stage', 'why': 'stage why'}],
         'message': 'board rules'},
    ],
}


@unittest.skipUnless(BASH, 'bash is required to run the hooks the way settings.json does')
class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hook 한글 space ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'Proj-worktrees' / 'feature 한글'
        self.hooks = self.root / '.claude' / 'hooks'
        self.hooks.mkdir(parents=True)
        for source in HOOKS.iterdir():
            if source.is_file():
                shutil.copy2(source, self.hooks / source.name)
        self.write_rules('file-pattern-map.json', MAP)
        self.write_rules('content-lint.json', LINT)
        self.write_rules('command-gate.json', GATE)
        self.home = self.base / 'home'
        self.home.mkdir()
        self.temp = self.base / 'temp'
        self.temp.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        TMPDIR=str(self.temp), TEMP=str(self.temp), TMP=str(self.temp),
                        PYTHONIOENCODING='ascii', PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('PYTHONHOME', None)
        self.env.pop('PYTHONPATH', None)
        self.session = 'case/한글:1'

    # ---- helpers ----

    def write_rules(self, name, data):
        (self.hooks / name).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8-sig')

    def invoke(self, script, payload=None, raw=None, args=(), env=None):
        if raw is None:
            raw = json.dumps(payload or {}, ensure_ascii=False).encode('utf-8')
        return subprocess.run([BASH, (self.hooks / 'run-python-hook.sh').as_posix(), script, *args],
                              input=raw, capture_output=True, cwd=self.base,
                              env=env or self.env, check=False)

    def event(self, tool, **data):
        return {'session_id': self.session, 'tool_name': tool, 'tool_input': data}

    def output(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        return json.loads(result.stdout)['hookSpecificOutput']

    def silent(self, result):
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'', b''))

    def deny(self, result):
        output = self.output(result)
        self.assertEqual(output['permissionDecision'], 'deny')
        return output['permissionDecisionReason']

    def failed(self, result, message):
        self.assertEqual((result.returncode, result.stdout), (1, b''))
        self.assertIn(message.encode('utf-8'), result.stderr)

    def read(self, relative):
        path = str(self.root / relative).replace('/', '\\')
        self.silent(self.invoke('pre-tool-use.py', self.event('Read', file_path=path)))

    def load_guides(self):
        self.read('GUIDE.md')
        self.silent(self.invoke('pre-tool-use.py', self.event('Skill', skill='plugin:lang-guide')))

    def state_files(self):
        state = self.temp / 'claude-code-hook-state'
        return state / 'requires-done-case____1.txt', state / 'fired-rules-case____1.txt'

    def edit(self, relative, text='// safe'):
        return self.event('Edit', file_path=str(self.root / relative), new_string=text)

    def bash(self, command):
        return self.invoke('pre-tool-use-command.py', self.event('Bash', command=command))

    # ---- input handling ----

    def test_empty_malformed_and_irrelevant_input(self):
        for script in ('pre-tool-use.py', 'pre-tool-use-command.py'):
            for raw in (b'', b'  \n', b'{broken', b'\xef\xbb\xbf{broken', b'null', b'{}', b'[' * 2000 + b']' * 2000):
                with self.subTest(script=script, raw=raw):
                    self.silent(self.invoke(script, raw=raw))
            self.silent(self.invoke(script, self.event('Unrelated')))

    # ---- SessionStart / SubagentStart ----

    def test_session_layers(self):
        (self.hooks / 'session-start-header.md').write_text('공통 문서', encoding='utf-8-sig')
        (self.hooks / 'main-session-header.md').write_text('메인 문서', encoding='utf-8')
        main = self.output(self.invoke('session-start.py', args=('--hook-event-name', 'SessionStart')))
        self.assertEqual(main['hookEventName'], 'SessionStart')
        common = '=== .claude/hooks/session-start-header.md ===\n공통 문서\n\n'
        self.assertEqual(main['additionalContext'],
                         common + '=== .claude/hooks/main-session-header.md ===\n메인 문서\n\n')
        sub = self.output(self.invoke('session-start.py', args=('--hook-event-name', 'SubagentStart')))
        self.assertEqual((sub['hookEventName'], sub['additionalContext']), ('SubagentStart', common))

    def test_session_invalid_event_and_unreadable_document_fail_visibly(self):
        result = self.invoke('session-start.py', args=('--hook-event-name', 'Invalid'))
        self.assertEqual((result.returncode, result.stdout), (1, b''))
        self.assertTrue(result.stderr)
        header = self.hooks / 'session-start-header.md'
        header.unlink(missing_ok=True)
        header.mkdir()
        result = self.invoke('session-start.py')
        self.assertEqual((result.returncode, result.stdout), (1, b''))
        self.assertTrue(result.stderr)

    def test_compact_clears_the_session_records(self):
        done, fired = self.state_files()
        for source, cleared, event in (('startup', False, 'SessionStart'), (None, False, 'SessionStart'),
                                       ('compact', False, 'SubagentStart'), ('compact', True, 'SessionStart')):
            with self.subTest(source=source, event=event):
                self.load_guides()
                self.assertEqual(self.invoke('pre-tool-use.py', self.edit('src/a.cpp')).returncode, 0)
                self.assertTrue(done.is_file() and fired.is_file())
                payload = {'session_id': self.session}
                if source is not None:
                    payload['source'] = source
                self.output(self.invoke('session-start.py', payload, args=('--hook-event-name', event)))
                self.assertEqual((done.exists(), fired.exists()), (not cleared, not cleared))

    def test_compact_reset_failure_is_reported_and_keeps_injecting(self):
        done, fired = self.state_files()
        self.load_guides()
        self.output(self.invoke('pre-tool-use.py', self.edit('src/a.cpp')))
        done.unlink()
        done.mkdir()
        result = self.invoke('session-start.py', {'session_id': self.session, 'source': 'compact'})
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'compact state reset failed', result.stderr)
        context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        self.assertIn('compact state reset FAILED', context)
        self.assertIn('session-start-header.md', context)
        self.assertFalse(fired.exists())

    # ---- PreToolUse: file pattern gate ----

    def test_gate_observation_and_reminder_sequence(self):
        edit = self.event('Edit', file_path=str(self.root / 'SRC' / '한글.cpp').replace('/', '\\'), new_string='// ok')
        reason = self.deny(self.invoke('pre-tool-use.py', edit))
        self.assertIn('Read: guide.md', reason)
        self.assertIn('Skill: lang-guide', reason)
        self.load_guides()
        self.load_guides()
        done, fired = self.state_files()
        self.assertEqual(done.read_text(encoding='utf-8-sig').splitlines(),
                         ['read:guide.md', 'skill:plugin:lang-guide', 'skill:lang-guide'])
        context = self.output(self.invoke('pre-tool-use.py', edit))['additionalContext']
        self.assertEqual(context, 'Project guide reminders (first match this session):\n[src] 한글 안내')
        self.silent(self.invoke('pre-tool-use.py', edit))
        self.assertEqual(fired.read_text(encoding='utf-8-sig').splitlines(), ['src'])

    def test_scope_exclusion_filename_and_wildcard(self):
        for path in ('other/a.cpp', 'src/vendor/a.cpp', 'src/a.txt'):
            with self.subTest(path=path):
                self.silent(self.invoke('pre-tool-use.py', self.edit(path)))
        self.assertIn('[docs]', self.output(self.invoke(
            'pre-tool-use.py', self.event('Write', file_path='docs/x.md', content='x')))['additionalContext'])
        self.write_rules('file-pattern-map.json', {'rules': [{'id': 'wild', 'patterns': ['src/?[ab].cpp'], 'message': 'w'}]})
        self.assertIn('[wild]', self.output(self.invoke(
            'pre-tool-use.py', self.event('Write', file_path='SRC/XA.CPP')))['additionalContext'])
        self.silent(self.invoke('pre-tool-use.py', self.event('Write', file_path='src/Xz.cpp')))

    # ---- PreToolUse: content lint ----

    def test_lint_runs_before_the_gate_and_reports_each_hit(self):
        reason = self.deny(self.invoke('pre-tool-use.py', self.event(
            'Write', file_path=str(self.root / 'src' / 'a.cpp'), content='/// note —\nint x; // ABC-12')))
        self.assertIn('forbids outright', reason)
        self.assertIn("Banned character: em dash (U+2014) -> '--'", reason)
        self.assertIn('Triple-slash comment: /// note', reason)
        self.assertIn('Issue ID in a comment: // ABC-12', reason)
        self.assertNotIn('Read: guide.md', reason)
        self.load_guides()
        for text in ('int ABC = 1 - 2; // fine', 'auto s = "ABC-12";', '/* plain */'):
            with self.subTest(text=text):
                self.assertNotIn('permissionDecision',
                                 self.invoke('pre-tool-use.py', self.edit('src/a.cpp', text)).stdout.decode('utf-8'))

    def test_lint_broken_file_or_entry_is_reported_and_the_rest_runs(self):
        self.load_guides()
        (self.hooks / 'content-lint.json').write_text('{broken', encoding='utf-8')
        result = self.invoke('pre-tool-use.py', self.edit('src/a.cpp', '/// —'))
        self.assertIn(b'content-lint.json is present but unusable', result.stderr)
        self.assertIn('additionalContext', self.output(result))
        lint = json.loads(json.dumps(LINT))
        lint['rules'][0]['bannedChars'].append({'codePoint': 'zz', 'name': 'bad'})
        lint['rules'][0]['bannedLines'].append({'regex': '([', 'message': 'bad'})
        self.write_rules('content-lint.json', lint)
        result = self.invoke('pre-tool-use.py', self.edit('src/a.cpp', '/// —'))
        self.assertIn(b'unusable bannedChars entry', result.stderr)
        self.assertIn(b'unusable bannedLines entry', result.stderr)
        reason = json.loads(result.stdout)['hookSpecificOutput']['permissionDecisionReason']
        self.assertIn('Banned character', reason)
        self.assertIn('Triple-slash', reason)
        (self.hooks / 'content-lint.json').unlink()
        self.silent(self.invoke('pre-tool-use.py', self.edit('src/b.cpp', '/// —')))

    # ---- PreToolUse: failures that switch a gate off are reported ----

    def test_broken_map_and_unwritable_state_are_reported_without_blocking(self):
        (self.hooks / 'file-pattern-map.json').write_text('{bad', encoding='utf-8')
        self.failed(self.invoke('pre-tool-use.py', self.edit('src/a.cpp')), 'file-pattern-map.json unavailable')
        self.failed(self.bash('git push'), 'file-pattern-map.json unavailable')
        (self.hooks / 'file-pattern-map.json').unlink()
        self.failed(self.invoke('pre-tool-use.py', self.edit('src/a.cpp')), 'file-pattern-map.json unavailable')
        self.write_rules('file-pattern-map.json', MAP)
        state = self.temp / 'claude-code-hook-state'
        shutil.rmtree(state, ignore_errors=True)
        state.write_text('not a directory', encoding='utf-8')
        self.failed(self.invoke('pre-tool-use.py', self.event('Read', file_path='guide.md')), 'session state unavailable')
        self.failed(self.bash('git push'), 'session state unavailable')

    def test_unrecordable_read_and_skill_are_reported(self):
        done, _ = self.state_files()
        done.parent.mkdir(parents=True)
        done.mkdir()
        self.failed(self.invoke('pre-tool-use.py', self.event('Read', file_path='guide.md')), 'could not record the read of')
        self.failed(self.invoke('pre-tool-use.py', self.event('Skill', skill='x')), 'could not record the load of skill')

    # ---- PreToolUse: shell command read gate ----

    def test_command_read_gate_blocks_until_the_document_is_read(self):
        for command in ('git commit -m x', 'git -C "F:/워크트리 경로" commit --amend', 'git push origin f',
                        'git worktree add ../x f'):
            with self.subTest(command=command):
                reason = self.deny(self.bash(command))
                self.assertIn('Read: docs/git.md', reason)
                self.assertIn('git pointer', reason)
        self.read('docs/git.md')
        self.silent(self.bash('git commit -m x'))

    def test_command_read_gate_ignores_read_only_and_quoted_commands(self):
        for command in ('git status', 'git log --oneline', 'git worktree list', 'git log --grep commit',
                        'git --no-pager log --grep push', 'git config --get remote.origin.push',
                        'git commit-graph write', 'echo "git commit"', "echo 'git push'",
                        "echo '$(git push)'", "echo '`git push origin f`'"):
            with self.subTest(command=command):
                self.silent(self.bash(command))

    def test_command_read_gate_sees_through_quoting_spelling_and_separators(self):
        for command in ('git "push" origin f', "git 'push' origin f", 'Write-Output "$(git push origin f)"',
                        'echo `git push origin f`', 'git.exe push', '/usr/bin/git push', '"C:\\tools\\git.exe" push',
                        'git status;git push', '(git push)', 'git status && git push', 'cd x | git push',
                        'git -C "F:/R&D" commit', "git -C 'F:/a;b' push", 'GIT PUSH'):
            with self.subTest(command=command):
                self.assertIn('Read: docs/git.md', self.deny(self.bash(command)))

    # ---- PreToolUse: flag gate ----

    def test_flag_gate(self):
        reason = self.deny(self.bash('gh --repo o/r pr create --title x'))
        self.assertIn('  --base - base why', reason)
        self.assertNotIn('  --repo -', reason)
        self.assertIn('use /merge-branch', reason)
        for command in ('gh pr create --base main --repo o/r', 'gh pr create --base=main --repo=o/r',
                        'gh pr list', 'echo "gh pr create"', 'gh pr view --base-branch x'):
            with self.subTest(command=command):
                self.silent(self.invoke('pre-tool-use-command.py', self.event('PowerShell', command=command)))
        self.assertIn('  --base -', self.deny(self.bash('gh pr create --base-branch main --repo o/r')))

    def test_command_rule_without_commands_is_reported(self):
        self.write_rules('command-gate.json', {'commands': [{'id': 'old', 'match': 'gh\\s+pr\\s+create'}]})
        result = self.bash('ls')
        self.failed(result, 'rule old has no "commands"')
        self.assertIn(b'"match" regex is not read', result.stderr)

    def test_broken_command_gate_keeps_the_read_gate(self):
        (self.hooks / 'command-gate.json').write_text('{bad', encoding='utf-8')
        result = self.bash('git push')
        self.assertIn(b'command-gate.json is present but unusable', result.stderr)
        self.assertIn('Read: docs/git.md', self.deny(result))
        self.failed(self.bash('ls'), 'command-gate.json is present but unusable')
        self.failed(self.invoke('pre-tool-use-command.py', self.event('mcp__tracker__issue_create')),
                    'command-gate.json is present but unusable')

    # ---- PreToolUse: MCP field gate ----

    def test_mcp_field_gate(self):
        tool = 'mcp__tracker__issue_create'
        reason = self.deny(self.invoke('pre-tool-use-command.py', self.event(tool, title='x')))
        self.assertIn('  sprint - sprint why', reason)
        self.assertIn('  customFields.stage - stage why', reason)
        self.assertIn('board rules', reason)
        for custom in ({'stage': '구현'}, json.dumps({'stage': '구현'}, ensure_ascii=False),
                       [{'name': 'stage', 'value': '구현'}], [{'stage': 'x'}]):
            with self.subTest(custom=custom):
                payload = self.event(tool, sprint='S1', customFields=custom)
                self.silent(self.invoke('pre-tool-use-command.py',
                                        raw=b'\xef\xbb\xbf' + json.dumps(payload, ensure_ascii=False).encode('utf-8')))
        for custom in (None, [], '{broken', {'stage': '  '}, [{'name': 'stage', 'value': ''}]):
            with self.subTest(custom=custom):
                reason = self.deny(self.invoke('pre-tool-use-command.py', self.event(tool, sprint='S1', customFields=custom)))
                self.assertIn('customFields.stage', reason)
                self.assertNotIn('  sprint -', reason)
        self.silent(self.invoke('pre-tool-use-command.py', self.event('mcp__tracker__issue_update')))

    # ---- UserPromptSubmit: session length ----

    def transcript(self, *entries):
        path = self.base / 'transcript.jsonl'
        lines = []
        for entry in entries:
            if entry == 'compact':
                lines.append(json.dumps({'type': 'system', 'subtype': 'compact_boundary'}))
            else:
                lines.append(json.dumps({'type': 'assistant', 'isSidechain': False,
                                         'message': {'usage': {'input_tokens': entry}}}, separators=(',', ':')))
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return {'hook_event_name': 'UserPromptSubmit', 'session_id': 'len', 'transcript_path': str(path)}

    def test_session_length_signal_rises_by_level(self):
        script = 'user-prompt-submit-session-length.py'
        self.silent(self.invoke(script, self.transcript(10_000)))
        self.assertIn('[session length]', self.output(self.invoke(script, self.transcript(600_000)))['additionalContext'])
        self.silent(self.invoke(script, self.transcript(600_000)))
        self.silent(self.invoke(script, self.transcript(700_000)))
        self.output(self.invoke(script, self.transcript(760_000)))
        self.assertIn('1 compaction', self.output(self.invoke(script, self.transcript(760_000, 'compact')))['additionalContext'])

    # ---- Stop: turn-end gate ----

    def test_stop_gate_blocks_once_per_prompt(self):
        payload = {'hook_event_name': 'Stop', 'session_id': 'stop', 'prompt_id': 'p1',
                   'last_assistant_message': 'Committed the fix. I will check the build output next.'}
        self.assertEqual(self.invoke('stop-turn-end-gate.py', payload).returncode, 2)
        self.silent(self.invoke('stop-turn-end-gate.py', payload))
        self.assertTrue((self.home / '.claude' / 'logs' / 'stop-turn-end-gate.jsonl').is_file())

    # ---- run-python-hook.sh ----

    def candidate(self, name, body):
        path = self.bin / name
        path.write_bytes(('#!/bin/bash\n' + body).encode('utf-8'))
        path.chmod(0o755)

    def runner_env(self):
        self.bin = self.base / 'candidate bin'
        self.bin.mkdir()
        (self.hooks / 'probe.py').write_text(
            'import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n'
            'sys.stderr.buffer.write(sys.argv[1].encode("utf-8"))\nsys.exit(int(sys.argv[2]))\n', encoding='utf-8')
        return dict(self.env, PATH=str(self.bin), REAL_PYTHON=Path(sys.executable).as_posix(),
                    PROBE_LOG=str(self.base / 'probes'))

    def test_runner_falls_back_and_preserves_stdin_arguments_and_exit(self):
        env = self.runner_env()
        self.candidate('python3', 'echo failed >> "$PROBE_LOG"\nread ignored\nexit 9\n')
        self.candidate('python', 'exec "$REAL_PYTHON" "$@"\n')
        raw = b'\xef\xbb\xbf' + '한글 input'.encode('utf-8')
        result = self.invoke('probe.py', raw=raw, args=('한글 arg space', '7'), env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, raw, '한글 arg space'.encode('utf-8')))
        self.assertEqual((self.base / 'probes').read_text().splitlines(), ['failed'])

    def test_runner_py_launcher_old_version_and_no_candidate(self):
        env = self.runner_env()
        self.candidate('python3', 'if [[ "$1" == -c ]]; then\n'
                       'exec "$REAL_PYTHON" -c "import sys; sys.version_info = (3, 8); $2"\nfi\nexit 92\n')
        self.candidate('python', 'exit 1\n')
        self.candidate('py', '[ "$1" = "-3" ] || exit 91\nshift\nexec "$REAL_PYTHON" "$@"\n')
        result = self.invoke('probe.py', raw=b'payload', args=('ok', '0'), env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'payload', b'ok'))
        self.candidate('py', 'exit 1\n')
        result = self.invoke('probe.py', env=env)
        self.assertEqual((result.returncode, result.stdout), (1, b''))
        self.assertIn(b'Python 3.9', result.stderr)

    # ---- settings.json ----

    @unittest.skipUnless(SETTINGS.is_file(), 'no .claude/settings.json next to the hooks')
    def test_settings_commands_dispatch_existing_hooks(self):
        settings = json.loads(SETTINGS.read_text(encoding='utf-8-sig'))
        for event, registrations in settings.get('hooks', {}).items():
            for registration in registrations:
                for hook in registration.get('hooks', []):
                    if 'run-python-hook.sh' not in hook.get('command', ''):
                        continue
                    with self.subTest(event=event, command=hook['command']):
                        self.assertEqual(hook.get('shell'), 'bash')
                        result = subprocess.run([BASH, '-c', hook['command']], input=b'{}', capture_output=True,
                                                cwd=self.base, check=False,
                                                env=dict(self.env, CLAUDE_PROJECT_DIR=self.root.as_posix()))
                        if event in ('SessionStart', 'SubagentStart'):
                            self.assertEqual(self.output(result)['hookEventName'], event)
                        else:
                            self.silent(result)


if __name__ == '__main__':
    unittest.main()
