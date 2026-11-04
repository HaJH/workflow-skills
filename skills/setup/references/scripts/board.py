#!/usr/bin/env python3
"""Read docs/board.md and report what its prerequisite lines imply.

    bash scripts/run-python.sh scripts/board.py ready

Edges live in one place and one format -- a `- prereq: `<id>`` bullet directly under a card
(docs/board.md, "Prerequisite Line"). Everything else about a card is prose for humans; the
verdict reads only that bullet.

  ready   -- cards nothing is blocking, so a session can pick one right now
  blocked -- cards waiting on a card that is still in ToDo or In Progress
  stale   -- the prerequisite already merged, so the edge is a lie the card keeps telling
  broken  -- the prerequisite matches no card anywhere: a typo, or a card dropped without
             looking at who pointed at it

`ready` exits 1 when anything is stale or broken, so it can gate a commit, and 2 when the
board files cannot be read.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re
import sys


DEFAULT_REPO = '{PROJECT_PATH}'

CARD_RE = re.compile(r'^- (⚑ )?\*\*`([a-z0-9-]+)`\*\*(.*)$')
EDGE_RE = re.compile(r'^\s+-\s*(prereq|adjacent):(.*)$')
STATUS_RE = re.compile(r'^\s+-\s*branch\b')
ID_RE = re.compile(r'`([a-z0-9-]+)`')
DETAIL_SUFFIX = '(detail: issues/)'


class BoardError(Exception):
    """A board file could not be read; the message names it."""


@dataclass
class Card:
    id: str
    summary: str
    flag: bool = False
    prereqs: list[str] = field(default_factory=list)
    adjacent: list[str] = field(default_factory=list)
    branch: str | None = None
    report: str | None = None
    started: date | None = None


@dataclass
class Group:
    name: str | None
    cards: list[Card] = field(default_factory=list)


@dataclass
class Board:
    in_progress: list[Card]
    groups: list[Group]
    archived: set[str]


@dataclass
class Verdict:
    ready: list[str]
    blocked: list[tuple[str, str]]
    stale: list[tuple[str, str]]
    broken: list[tuple[str, str]]


def unfenced_lines(text: str) -> list[str]:
    """Lines outside fenced blocks. The board's own "Format" section shows card syntax inside a
    fence, using the same markup as a real card; those illustrative ids must never count."""
    lines, fenced = [], False
    for line in text.lstrip('﻿').replace('\r\n', '\n').split('\n'):
        if line.startswith('```'):
            fenced = not fenced
            continue
        if not fenced:
            lines.append(line)
    return lines


def section(lines: list[str], title: str) -> list[str]:
    """The lines under `## <title>`, up to the next `## ` header."""
    body, inside = [], False
    for line in lines:
        if line.startswith('## '):
            inside = line[3:].strip() == title
            continue
        if inside:
            body.append(line)
    return body


def parse_card(match: re.Match) -> Card:
    summary = match.group(3).strip()
    if summary.startswith('—'):
        summary = summary[1:].strip()
    if summary.endswith(DETAIL_SUFFIX):
        summary = summary[:-len(DETAIL_SUFFIX)].strip()
    return Card(id=match.group(2), summary=summary, flag=bool(match.group(1)))


def apply_sub_bullet(card: Card, line: str) -> None:
    edge = EDGE_RE.match(line)
    if edge:
        target = card.prereqs if edge.group(1) == 'prereq' else card.adjacent
        target.extend(ID_RE.findall(edge.group(2)))
        return
    if STATUS_RE.match(line):
        branch = re.search(r'branch `([^`]+)`', line)
        report = re.search(r'report `([^`]+)`', line)
        started = re.search(r'started (\d{4}-\d{2}-\d{2})', line)
        card.branch = branch.group(1) if branch else None
        card.report = report.group(1) if report else None
        try:
            card.started = date.fromisoformat(started.group(1)) if started else None
        except ValueError:
            card.started = None


def parse_cards(lines: list[str], groups: list[Group]) -> None:
    """Fill `groups` from a section body. `### <name>` opens a group; cards before any header
    land in a group whose name is None."""
    card = None
    for line in lines:
        if line.startswith('### '):
            groups.append(Group(line[4:].strip()))
            card = None
            continue
        match = CARD_RE.match(line)
        if match:
            if not groups:
                groups.append(Group(None))
            card = parse_card(match)
            groups[-1].cards.append(card)
        elif card is not None and line[:1].isspace():
            apply_sub_bullet(card, line)


def parse_board(board_text: str, archive_text: str) -> Board:
    lines = unfenced_lines(board_text)
    running: list[Group] = []
    parse_cards(section(lines, 'In Progress'), running)
    todo: list[Group] = []
    parse_cards(section(lines, 'ToDo'), todo)
    archived = {match.group(2) for line in unfenced_lines(archive_text) if (match := CARD_RE.match(line))}
    return Board(in_progress=[card for group in running for card in group.cards], groups=todo,
                 archived=archived)


def load_board(repo: Path) -> Board:
    texts = []
    for name in ('board.md', 'board-archive.md'):
        path = repo / 'docs' / name
        try:
            texts.append(path.read_text(encoding='utf-8-sig'))
        except OSError as error:
            raise BoardError(f'board: cannot read {path} ({error.strerror})') from None
    return parse_board(*texts)


def todo_cards(board: Board) -> list[Card]:
    return [card for group in board.groups for card in group.cards]


def judge(board: Board) -> Verdict:
    live = {card.id for card in todo_cards(board)}
    running = {card.id for card in board.in_progress}
    blocked, stale, broken = [], [], []
    for card in todo_cards(board):
        for dep in card.prereqs:
            if dep in board.archived:
                stale.append((card.id, dep))
            elif dep in live or dep in running:
                blocked.append((card.id, dep))
            else:
                broken.append((card.id, dep))
    blocked_ids = {card_id for card_id, _ in blocked}
    ready = list(dict.fromkeys(card.id for card in todo_cards(board) if card.id not in blocked_ids))
    return Verdict(ready=ready, blocked=blocked, stale=stale, broken=broken)


def counts_line(board: Board) -> str:
    return (f'board: ToDo {len({card.id for card in todo_cards(board)})} / '
            f'In Progress {len({card.id for card in board.in_progress})} / archived {len(board.archived)}')


def format_ready(board: Board, verdict: Verdict) -> str:
    def block(title: str, items: list[str], keep_empty: bool = True) -> list[str]:
        if not items and not keep_empty:
            return []
        return ['', title] + ([f'  {item}' for item in items] or ['  (none)'])

    edges = lambda pairs: [f'{card} ← {dep}' for card, dep in pairs]  # noqa: E731
    lines = [counts_line(board)]
    lines += block(f'ready ({len(verdict.ready)})', verdict.ready)
    lines += block(f'blocked ({len(verdict.blocked)})', edges(verdict.blocked))
    lines += block(f'stale edges -- prerequisite already merged; delete the line ({len(verdict.stale)})',
                   edges(verdict.stale), keep_empty=False)
    lines += block(f'broken edges -- prerequisite matches no card ({len(verdict.broken)})',
                   edges(verdict.broken), keep_empty=False)
    return '\n'.join(lines) + '\n'


def run_ready(repo: Path) -> int:
    board = load_board(repo)
    verdict = judge(board)
    sys.stdout.write(format_ready(board, verdict))
    return 1 if verdict.stale or verdict.broken else 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='replace', newline='\n')
    parser = argparse.ArgumentParser(description='Read the work board (docs/board.md).')
    parser.add_argument('--repo', type=Path, default=Path(DEFAULT_REPO),
                        help='project root holding docs/board.md (default: the main tree)')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('ready', help='startable, blocked, stale and broken cards')
    args = parser.parse_args(argv)
    try:
        return run_ready(args.repo)
    except BoardError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
