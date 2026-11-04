"""Regression tests for scripts/board.py.

Run from the project root:  python -m unittest discover -s scripts/tests -v

Each test writes its own board into a throwaway repo under a temp directory, so the project's
real board is never read. The CLI tests run board.py with the current interpreter.
"""
from datetime import date
import importlib.util
import os
from pathlib import Path
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

    def test_ready_in_unicode_path_under_ascii_locale(self):
        root = make_repo(self.tmp / '작업 폴더 space')
        env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONDONTWRITEBYTECODE='1')
        result = run_cli(root, 'ready', env=env)
        self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
        self.assertIn('library-ui ← scan-pipeline'.encode('utf-8'), result.stdout)


if __name__ == '__main__':
    unittest.main()
