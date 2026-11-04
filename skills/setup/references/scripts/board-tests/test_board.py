"""Regression tests for scripts/board.py.

Run from the project root:  python -m unittest discover -s scripts/tests -v

Each test writes its own board into a throwaway repo under a temp directory, so the project's
real board is never read. The CLI tests run board.py with the current interpreter.
"""
from datetime import date, datetime
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


BOARD = Path(__file__).resolve().parents[1] / 'board.py'

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('board', BOARD)
board = importlib.util.module_from_spec(_spec)
sys.modules['board'] = board
_spec.loader.exec_module(board)


BOARD_MD = """# Board

A lightweight kanban board.

## Rules

- A card is one line.

## Format

```markdown
## In Progress

- **`fenced-only`** — an example card inside the format block
  - prereq: `ghost-in-fence`
```

---

## In Progress

- **`scan-pipeline`** — scan the library folder → register in the DB (detail: issues/)
  - branch `feature/scan-pipeline` · report `docs/reports/feature-scan-pipeline.md` · started 2026-11-02

## ToDo

### Main Line (v0)

- **`library-ui`** — implement the v0 screen (detail: issues/)
  - prereq: `scan-pipeline`
- **`playback-queue`** — playback queue
  - prereq: `library-ui`

### Core

- ⚑ **`sleep-timer`** — sleep timer
- **`db-migration`** — DB schema migration tool
  - prereq: `ghost`

### Docs

- **`api-guide`** — internal API guide
  - prereq: `old-done`
  - adjacent: `library-ui`
"""

ARCHIVE_MD = """# Board Archive

## Format

```markdown
## v0

- **`fenced-only`** (YYYY-MM-DD ~ MM-DD) — example entry
```

---

## v0

- **`old-done`** (2026-10-01 ~ 10-03) — finished earlier
"""

READY_TEXT = """board: ToDo 5 / In Progress 1 / archived 1

ready (3)
  sleep-timer
  db-migration
  api-guide

blocked (2)
  library-ui ← scan-pipeline
  playback-queue ← library-ui

stale edges -- prerequisite already merged; delete the line (1)
  api-guide ← old-done

broken edges -- prerequisite matches no card (1)
  db-migration ← ghost
"""


def make_repo(root, board_text=BOARD_MD, archive=ARCHIVE_MD, issues=None):
    docs = root / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    (docs / 'board.md').write_bytes(board_text.encode('utf-8'))
    if archive is not None:
        (docs / 'board-archive.md').write_bytes(archive.encode('utf-8'))
    for card_id, text in (issues or {}).items():
        (docs / 'issues').mkdir(exist_ok=True)
        (docs / 'issues' / f'{card_id}.md').write_bytes(text.encode('utf-8'))
    return root


def run_cli(root, *args, env=None):
    return subprocess.run([sys.executable, str(BOARD), '--repo', str(root), *args],
                          capture_output=True, env=env, check=False)


class BoardTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='board 한글 ')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def cards(self, parsed):
        return {card.id: card for group in parsed.groups for card in group.cards} | \
            {card.id: card for card in parsed.in_progress}


class ParseTests(BoardTestCase):
    def test_parse_sections_groups_and_status_line(self):
        parsed = board.parse_board(BOARD_MD, ARCHIVE_MD)
        self.assertEqual([card.id for card in parsed.in_progress], ['scan-pipeline'])
        scan = parsed.in_progress[0]
        self.assertEqual(scan.branch, 'feature/scan-pipeline')
        self.assertEqual(scan.report, 'docs/reports/feature-scan-pipeline.md')
        self.assertEqual(scan.started, date(2026, 11, 2))
        self.assertEqual([group.name for group in parsed.groups], ['Main Line (v0)', 'Core', 'Docs'])
        self.assertEqual([[card.id for card in group.cards] for group in parsed.groups],
                         [['library-ui', 'playback-queue'], ['sleep-timer', 'db-migration'], ['api-guide']])
        cards = self.cards(parsed)
        self.assertTrue(cards['sleep-timer'].flag)
        self.assertFalse(cards['db-migration'].flag)
        self.assertEqual(cards['library-ui'].summary, 'implement the v0 screen')
        self.assertEqual(cards['library-ui'].prereqs, ['scan-pipeline'])
        self.assertEqual(cards['api-guide'].adjacent, ['library-ui'])
        self.assertEqual(parsed.archived, {'old-done'})

    def test_fenced_example_cards_are_ignored(self):
        parsed = board.parse_board(BOARD_MD, ARCHIVE_MD)
        self.assertNotIn('fenced-only', self.cards(parsed))
        self.assertNotIn('fenced-only', parsed.archived)

    def test_judge_matches_board_ready_semantics(self):
        verdict = board.judge(board.parse_board(BOARD_MD, ARCHIVE_MD))
        self.assertEqual(verdict.ready, ['sleep-timer', 'db-migration', 'api-guide'])
        self.assertEqual(verdict.blocked, [('library-ui', 'scan-pipeline'), ('playback-queue', 'library-ui')])
        self.assertEqual(verdict.stale, [('api-guide', 'old-done')])
        self.assertEqual(verdict.broken, [('db-migration', 'ghost')])

    def test_crlf_and_bom_parse_identically(self):
        windows = '﻿' + BOARD_MD.replace('\n', '\r\n')
        archive = '﻿' + ARCHIVE_MD.replace('\n', '\r\n')
        self.assertEqual(board.parse_board(windows, archive), board.parse_board(BOARD_MD, ARCHIVE_MD))


class ReadyCliTests(BoardTestCase):
    def test_ready_output_and_exit_code(self):
        root = make_repo(self.tmp / 'repo')
        result = run_cli(root, 'ready')
        self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
        self.assertEqual(result.stdout, READY_TEXT.encode('utf-8'))

        clean = BOARD_MD.replace('  - prereq: `ghost`\n', '').replace('  - prereq: `old-done`\n', '')
        root = make_repo(self.tmp / 'clean', board_text=clean)
        result = run_cli(root, 'ready')
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertNotIn(b'stale edges', result.stdout)
        self.assertNotIn(b'broken edges', result.stdout)

    def test_ready_missing_archive_exits_2(self):
        root = make_repo(self.tmp / 'repo', archive=None)
        result = run_cli(root, 'ready')
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'board-archive.md', result.stderr)
        self.assertEqual(result.stdout, b'')

    def test_non_utf8_board_exits_2_naming_the_file(self):
        root = make_repo(self.tmp / 'repo')
        legacy = BOARD_MD.replace('sleep timer', '수면 타이머').encode('cp949', errors='replace')
        (root / 'docs' / 'board.md').write_bytes(legacy)
        for command in (('ready',), ('view', '--no-open', '--out', str(self.tmp / 'out.html'))):
            with self.subTest(command=command[0]):
                result = run_cli(root, *command)
                self.assertEqual(result.returncode, 2, result.stderr.decode('utf-8', 'replace'))
                self.assertIn(b'board.md', result.stderr)
                self.assertIn(b'not UTF-8', result.stderr)
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_ready_in_unicode_path_under_ascii_locale(self):
        root = make_repo(self.tmp / '작업 폴더 space')
        env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONDONTWRITEBYTECODE='1')
        result = run_cli(root, 'ready', env=env)
        self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
        self.assertIn('library-ui ← scan-pipeline'.encode('utf-8'), result.stdout)


NOW = datetime(2026, 11, 4, 9, 12)


def article(page, card_id):
    """(classes, body) of the board card for card_id."""
    match = re.search(r'<article class="([^"]+)" data-card="%s">(.*?)</article>' % re.escape(card_id), page, re.S)
    assert match, f'no card article for {card_id}'
    return match.group(1).split(), match.group(2)


def detail(page, card_id):
    match = re.search(r'<template id="detail-%s">(.*?)</template>' % re.escape(card_id), page, re.S)
    assert match, f'no detail template for {card_id}'
    return match.group(1)


class ViewTests(BoardTestCase):
    def render(self, board_text=BOARD_MD, issues=None):
        parsed = board.parse_board(board_text, ARCHIVE_MD)
        return board.render_view(parsed, board.judge(parsed), issues or {}, 'MyApp', NOW)

    def test_render_issue_subset_and_escaping(self):
        rendered = board.render_issue('# T\n\n> q\n\n- a\n- b\n\n1. x\n\nuse `c` and **d** <script>')
        for fragment in ('<h3>T</h3>', '<blockquote>q</blockquote>', '<ul><li>a</li><li>b</li></ul>',
                         '<ol><li>x</li></ol>', '<code>c</code>', '<strong>d</strong>', '&lt;script&gt;'):
            self.assertIn(fragment, rendered)
        self.assertNotIn('<script>', rendered)

    def test_view_layout_order_badges_and_dimming(self):
        page = self.render()
        positions = [page.index(f'<h3>{name}</h3>') for name in ('Main Line (v0)', 'Core', 'Docs')]
        self.assertEqual(positions, sorted(positions))
        classes, body = article(page, 'library-ui')
        self.assertIn('blocked', classes)
        self.assertIn('<span class="badge blocked">blocked ← scan-pipeline</span>', body)
        classes, body = article(page, 'sleep-timer')
        self.assertNotIn('blocked', classes)
        for fragment in ('<span class="flag">⚑</span>', '<span class="rank">1</span>',
                         '<span class="badge ready">ready</span>'):
            self.assertIn(fragment, body)
        for card_id in ('api-guide', 'db-migration'):
            self.assertIn('<span class="badge cleanup">needs cleanup</span>', article(page, card_id)[1])
        self.assertNotIn('needs cleanup', article(page, 'sleep-timer')[1])
        self.assertIn('feature/scan-pipeline · started 11-02 · day 3', article(page, 'scan-pipeline')[1])
        self.assertIn('ready 3 · blocked 2 · in progress 1', page)
        self.assertIn('generated 2026-11-04 09:12', page)

    def test_view_escapes_summaries_and_issue_text(self):
        text = BOARD_MD.replace('— sleep timer', '— a <b> & "c"')
        page = self.render(text, issues={'sleep-timer': '<img src=x>'})
        self.assertNotIn('a <b> & "c"', page)
        self.assertIn('a &lt;b&gt; &amp; &quot;c&quot;', page)
        self.assertNotIn('<img src=x>', page)
        self.assertIn('&lt;img src=x&gt;', detail(page, 'sleep-timer'))

    def test_view_detail_templates(self):
        issue = '# library-ui\n\nv0 first screen.\n\n## What Must Be Decided\n\n1. cache location\n'
        page = self.render(issues={'library-ui': issue})
        self.assertIn('<span class="badge detail">detail</span>', article(page, 'library-ui')[1])
        self.assertNotIn('badge detail', article(page, 'sleep-timer')[1])
        rendered = detail(page, 'library-ui')
        self.assertIn('<h4>What Must Be Decided</h4>', rendered)
        self.assertIn('<ol><li>cache location</li></ol>', rendered)
        self.assertIn('scan-pipeline', rendered)
        self.assertIn('sleep timer', detail(page, 'sleep-timer'))

    def test_view_without_issues_dir_and_bad_date(self):
        root = make_repo(self.tmp / 'repo', board_text=BOARD_MD.replace('started 2026-11-02', 'started 2026-13-40'))
        out = self.tmp / 'out.html'
        result = run_cli(root, 'view', '--no-open', '--out', str(out))
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertNotIn('day ', article(out.read_text(encoding='utf-8'), 'scan-pipeline')[1])

    def test_view_cli_writes_file_and_prints_summary(self):
        root = make_repo(self.tmp / 'repo')
        out = self.tmp / 'out.html'
        result = run_cli(root, 'view', '--no-open', '--out', str(out))
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertEqual(result.stdout.decode('utf-8').splitlines(), [
            f'board view: {out}',
            'board: ToDo 5 / In Progress 1 / archived 1 -- ready 3, blocked 2',
            'needs cleanup: 1 stale, 1 broken edges -- run board.py ready for the list',
        ])
        self.assertTrue(out.is_file())

    def test_view_default_output_name_is_sanitized(self):
        root = make_repo(self.tmp / 'My App 한글')
        temp = self.tmp / 't'
        temp.mkdir()
        env = dict(os.environ, TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp), PYTHONDONTWRITEBYTECODE='1')
        result = run_cli(root, 'view', '--no-open', env=env)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertTrue((temp / 'board-view-My_App___.html').is_file())


if __name__ == '__main__':
    unittest.main()
