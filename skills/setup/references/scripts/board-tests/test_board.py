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
import shutil
import subprocess
import sys
import tempfile
import unittest


BOARD = Path(__file__).resolve().parents[1] / 'board.py'
SCRIPTS = BOARD.parent
BASH = shutil.which('bash')

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

## Done

- **`tag-editor`** · Tag editor — edit tags in place (detail: issues/)
  - started 2026-10-28 · done 2026-11-01

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
- **`tag-bulk`** · Bulk tagging — tag many works at once
  - prereq: `tag-editor`

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

READY_TEXT = """board: ToDo 6 / In Progress 1 / Done 1 / archived 1

ready (4)
  sleep-timer
  db-migration
  tag-bulk
  api-guide

blocked (2)
  library-ui ← scan-pipeline
  playback-queue ← library-ui

stale edges -- prerequisite already done; delete the line (2)
  tag-bulk ← tag-editor
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
            {card.id: card for card in parsed.in_progress + parsed.done}


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
                         [['library-ui', 'playback-queue'], ['sleep-timer', 'db-migration', 'tag-bulk'],
                          ['api-guide']])
        self.assertEqual([card.id for card in parsed.done], ['tag-editor'])
        done = parsed.done[0]
        self.assertEqual((done.title, done.summary), ('Tag editor', 'edit tags in place'))
        self.assertEqual((done.started, done.finished), (date(2026, 10, 28), date(2026, 11, 1)))
        self.assertIsNone(done.branch)
        self.assertIsNone(scan.finished)
        cards = self.cards(parsed)
        self.assertTrue(cards['sleep-timer'].flag)
        self.assertFalse(cards['db-migration'].flag)
        self.assertEqual(cards['library-ui'].summary, 'implement the v0 screen')
        self.assertIsNone(cards['library-ui'].title)
        self.assertEqual((cards['tag-bulk'].title, cards['tag-bulk'].summary),
                         ('Bulk tagging', 'tag many works at once'))
        self.assertEqual(cards['library-ui'].prereqs, ['scan-pipeline'])
        self.assertEqual(cards['api-guide'].adjacent, ['library-ui'])
        self.assertEqual(parsed.archived, {'old-done'})

    def test_fenced_example_cards_are_ignored(self):
        parsed = board.parse_board(BOARD_MD, ARCHIVE_MD)
        self.assertNotIn('fenced-only', self.cards(parsed))
        self.assertNotIn('fenced-only', parsed.archived)

    def test_title_is_marked_only_by_the_dot_after_the_id(self):
        text = ('## ToDo\n\n'
                '- **`plain`** — scan · then register — later\n'
                '- **`titled`** · Scan — walk · then register — later (detail: issues/)\n'
                '- **`title-only`** · Just a title\n')
        cards = self.cards(board.parse_board(text, ARCHIVE_MD))
        self.assertEqual((cards['plain'].title, cards['plain'].summary), (None, 'scan · then register — later'))
        self.assertEqual((cards['titled'].title, cards['titled'].summary), ('Scan', 'walk · then register — later'))
        self.assertEqual((cards['title-only'].title, cards['title-only'].summary), ('Just a title', ''))

    def test_judge_matches_board_ready_semantics(self):
        verdict = board.judge(board.parse_board(BOARD_MD, ARCHIVE_MD))
        self.assertEqual(verdict.ready, ['sleep-timer', 'db-migration', 'tag-bulk', 'api-guide'])
        self.assertEqual(verdict.blocked, [('library-ui', 'scan-pipeline'), ('playback-queue', 'library-ui')])
        self.assertEqual(verdict.stale, [('tag-bulk', 'tag-editor'), ('api-guide', 'old-done')])
        self.assertEqual(verdict.broken, [('db-migration', 'ghost')])

    def test_korean_vocabulary_parses_like_english(self):
        korean = (BOARD_MD
                  .replace('  - prereq:', '  - 선행:')
                  .replace('  - adjacent:', '  - 인접:')
                  .replace('(detail: issues/)', '(상세: issues/)')
                  .replace('  - branch `feature/scan-pipeline` · report `docs/reports/feature-scan-pipeline.md` · '
                           'started 2026-11-02',
                           '  - 브랜치 `feature/scan-pipeline` · 보고서 `docs/reports/feature-scan-pipeline.md` · '
                           '시작 2026-11-02')
                  .replace('  - started 2026-10-28 · done 2026-11-01', '  - 시작 2026-10-28 · 완료 2026-11-01'))
        self.assertNotEqual(korean, BOARD_MD)
        self.assertEqual(board.parse_board(korean, ARCHIVE_MD), board.parse_board(BOARD_MD, ARCHIVE_MD))

    def test_status_line_without_a_branch_keeps_the_start_date(self):
        text = '## In Progress\n\n- **`signoff`** — review\n  - 브랜치 없음(사용자 검토) · 시작 2026-11-03\n\n## ToDo\n'
        parsed = board.parse_board(text, ARCHIVE_MD)
        card = parsed.in_progress[0]
        self.assertIsNone(card.branch)
        self.assertEqual(card.started, date(2026, 11, 3))
        self.assertEqual(parsed.done, [])

    def test_every_vocabulary_row_names_every_word(self):
        keys = set(board.VOCABULARY[0])
        self.assertTrue(all(set(row) == keys for row in board.VOCABULARY))

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

        clean = (BOARD_MD.replace('  - prereq: `ghost`\n', '').replace('  - prereq: `old-done`\n', '')
                 .replace('  - prereq: `tag-editor`\n', ''))
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
        columns = [page.index(f'<section class="column {name}">') for name in ('todo', 'in-progress', 'done')]
        self.assertEqual(columns, sorted(columns))
        positions = [page.index(f'<section class="group" data-group="{name}">')
                     for name in ('Main Line (v0)', 'Core', 'Docs')]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('<span class="group-name">Core</span><span class="count">3</span>', page)
        classes, body = article(page, 'library-ui')
        self.assertIn('blocked', classes)
        self.assertIn('<p class="meta">blocked ← scan-pipeline</p>', body)
        classes, body = article(page, 'sleep-timer')
        self.assertNotIn('blocked', classes)
        for fragment in ('<span class="flag">⚑</span>', '<span class="rank">1</span>'):
            self.assertIn(fragment, body)
        self.assertNotIn('class="badge', body)
        for card_id in ('api-guide', 'db-migration'):
            self.assertIn('<span class="badge cleanup">needs cleanup</span>', article(page, card_id)[1])
        self.assertNotIn('needs cleanup', article(page, 'sleep-timer')[1])
        self.assertIn('feature/scan-pipeline · started 11-02 · day 3', article(page, 'scan-pipeline')[1])
        self.assertIn('ready 4 · blocked 2 · in progress 1 · done 1 · archived 1', page)
        self.assertIn('generated 2026-11-04 09:12', page)

    def test_view_card_lines_title_and_done_column(self):
        page = self.render()
        body = article(page, 'tag-bulk')[1]
        self.assertIn('<p class="title">Bulk tagging</p>', body)
        self.assertIn('<p class="summary">tag many works at once</p>', body)
        self.assertNotIn('class="title"', article(page, 'library-ui')[1])
        done_column = page[page.index('<section class="column done">'):page.index('</main>')]
        self.assertIn('data-card="tag-editor"', done_column)
        self.assertIn('<p class="meta">done 11-01</p>', article(page, 'tag-editor')[1])
        self.assertIn('<p class="meta">done 11-01</p>', detail(page, 'tag-editor'))

    def test_view_renders_inline_code_and_bold_in_card_text(self):
        page = self.render(BOARD_MD.replace('— DB schema migration tool', '— **DB** schema `migrate` tool'))
        expected = '<p class="summary"><strong>DB</strong> schema <code>migrate</code> tool</p>'
        self.assertIn(expected, article(page, 'db-migration')[1])
        self.assertIn(expected, detail(page, 'db-migration'))

    def test_view_escapes_summaries_and_issue_text(self):
        text = BOARD_MD.replace('— sleep timer', '— a <b> & "c"').replace('· Bulk tagging', '· Bulk <i>')
        page = self.render(text, issues={'sleep-timer': '<img src=x>'})
        self.assertNotIn('a <b> & "c"', page)
        self.assertIn('a &lt;b&gt; &amp; &quot;c&quot;', page)
        self.assertNotIn('Bulk <i>', page)
        self.assertIn('Bulk &lt;i&gt;', page)
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
            'board: ToDo 6 / In Progress 1 / Done 1 / archived 1 -- ready 4, blocked 2',
            'needs cleanup: 2 stale, 1 broken edges -- run scripts/board ready for the list',
        ])
        self.assertTrue(out.is_file())

    def test_view_cli_reads_the_issue_files_of_done_cards(self):
        issue = '# tag-editor\n\n## For the User to Check by Eye\n\n- the tag field keeps focus\n'
        root = make_repo(self.tmp / 'repo', issues={'tag-editor': issue})
        out = self.tmp / 'out.html'
        result = run_cli(root, 'view', '--no-open', '--out', str(out))
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        page = out.read_text(encoding='utf-8')
        self.assertIn('<span class="badge detail">detail</span>', article(page, 'tag-editor')[1])
        self.assertIn('<li>the tag field keeps focus</li>', detail(page, 'tag-editor'))

    def test_view_default_output_name_is_sanitized(self):
        root = make_repo(self.tmp / 'My App 한글')
        temp = self.tmp / 't'
        temp.mkdir()
        env = dict(os.environ, TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp), PYTHONDONTWRITEBYTECODE='1')
        result = run_cli(root, 'view', '--no-open', env=env)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertTrue((temp / 'board-view-My_App___.html').is_file())


def make_project(root):
    """A project laid out the way setup generates it: docs/ plus scripts/, with board.py's
    default repo pointing at this project."""
    make_repo(root)
    scripts = root / 'scripts'
    scripts.mkdir()
    source = re.sub(r"^DEFAULT_REPO = .*$", f'DEFAULT_REPO = {root.as_posix()!r}',
                    BOARD.read_text(encoding='utf-8'), count=1, flags=re.M)
    (scripts / 'board.py').write_bytes(source.encode('utf-8'))
    for name in ('board-view.html', 'run-python.sh', 'board', 'board.cmd'):
        shutil.copy2(SCRIPTS / name, scripts / name)
    return root


@unittest.skipUnless(BASH, 'bash is required to run scripts/board')
class ShortcutTests(BoardTestCase):
    def setUp(self):
        super().setUp()
        self.root = make_project(self.tmp / 'My Project')
        self.temp = self.tmp / 'temp'
        self.temp.mkdir()
        self.env = dict(os.environ, TMP=str(self.temp), TEMP=str(self.temp), TMPDIR=str(self.temp),
                        PYTHONDONTWRITEBYTECODE='1')

    def browser_recorder(self):
        """Point Python's BROWSER variable at a program that logs the URL it is asked to open."""
        folder = Path(tempfile.mkdtemp(prefix='board-rec-'))
        self.addCleanup(shutil.rmtree, folder, True)
        log = folder / 'opened.txt'
        if os.name == 'nt':
            program = folder / 'record.cmd'
            program.write_bytes(f'@echo %~1>>"{log}"\r\n'.encode('ascii'))
        else:
            program = folder / 'record'
            program.write_text(f'#!/bin/sh\necho "$1" >> "{log}"\n', encoding='utf-8')
            program.chmod(0o755)
        return log, dict(self.env, BROWSER=str(program))

    def test_board_without_arguments_opens_the_view(self):
        log, env = self.browser_recorder()
        result = subprocess.run([BASH, (self.root / 'scripts' / 'board').as_posix()],
                                capture_output=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertTrue(result.stdout.startswith(b'board view: '), result.stdout)
        page = self.temp / 'board-view-My_Project.html'
        self.assertTrue(page.is_file())
        self.assertEqual(log.read_text(encoding='ascii').split(), [page.resolve().as_uri()])

    def test_board_passes_arguments_through(self):
        result = subprocess.run([BASH, (self.root / 'scripts' / 'board').as_posix(), 'ready'],
                                capture_output=True, env=self.env, check=False)
        self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
        self.assertEqual(result.stdout, READY_TEXT.encode('utf-8'))

    @unittest.skipUnless(os.name == 'nt', 'board.cmd is the Windows cmd entry point')
    def test_board_cmd_runs_from_cmd(self):
        for command in ([str(self.root / 'scripts' / 'board.cmd'), 'ready'], ['scripts\\board', 'ready']):
            with self.subTest(command=command[0]):
                result = subprocess.run(['cmd', '/c', *command], cwd=self.root, capture_output=True,
                                        env=self.env, check=False)
                self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
                self.assertEqual(result.stdout.replace(b'\r\n', b'\n'), READY_TEXT.encode('utf-8'))


if __name__ == '__main__':
    unittest.main()
