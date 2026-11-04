#!/usr/bin/env python3
"""Read docs/board.md and report what its prerequisite lines imply, or show it as a page.

    scripts/board ready      (scripts\board ready in Windows cmd)
    scripts/board            (opens the page; same as scripts/board view)

scripts/board and scripts/board.cmd find a working Python through scripts/run-python.sh.

`view` renders the board as a read-only kanban page (scripts/board-view.html), writes it to
the temp directory and opens it in the browser. The page is a snapshot: run it again to see
later changes.

Edges live in one place and one format -- a `- prereq: `<id>`` bullet directly under a card
(docs/board.md, "Prerequisite Line"), or the same bullet in the board's own language
(VOCABULARY). Everything else about a card is prose for humans; the verdict reads only that
bullet.

A card is `- **`<id>`** · <title> — <summary>`, or `- **`<id>`** — <summary>` with no title. The
title is recognised only by the ` · ` right after the id, because summaries already contain ` — `.

  ready   -- cards nothing is blocking, so a session can pick one right now
  blocked -- cards waiting on a card that is still in ToDo or In Progress
  stale   -- the prerequisite is already done (Done or the archive), so the edge is a lie the
             card keeps telling
  broken  -- the prerequisite matches no card anywhere: a typo, or a card dropped without
             looking at who pointed at it

`ready` exits 1 when anything is stale or broken, so it can gate a commit, and 2 when the
board files cannot be read.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime
import html
from pathlib import Path
import re
import sys
import tempfile
import webbrowser


DEFAULT_REPO = '{PROJECT_PATH}'

# The words the parser reads, one row per language. Every row is read on every board, so a board
# written in the project's language parses without configuration. Add a language by appending a
# row, and a word by adding its key to every row; editing an existing word stops the boards
# already written with it from parsing.
VOCABULARY = (
    {'prereq': 'prereq', 'adjacent': 'adjacent', 'branch': 'branch', 'report': 'report',
     'started': 'started', 'finished': 'done', 'detail': '(detail: issues/)'},
    {'prereq': '선행', 'adjacent': '인접', 'branch': '브랜치', 'report': '보고서',
     'started': '시작', 'finished': '완료', 'detail': '(상세: issues/)'},
)


def any_word(key: str) -> str:
    return '(?:' + '|'.join(re.escape(row[key]) for row in VOCABULARY) + ')'


EDGE_KIND = {row[kind]: kind for row in VOCABULARY for kind in ('prereq', 'adjacent')}

CARD_RE = re.compile(r'^- (⚑ )?\*\*`([a-z0-9-]+)`\*\*(.*)$')
EDGE_RE = re.compile(r'^\s+-\s*(' + '|'.join(map(re.escape, EDGE_KIND)) + r'):(.*)$')
# A status line opens with the branch word in In Progress and with the start word in Done.
STATUS_RE = re.compile(r'^\s+-\s*(?:' + any_word('branch') + '|' + any_word('started') + r')\b')
BRANCH_RE = re.compile(any_word('branch') + r' `([^`]+)`')
REPORT_RE = re.compile(any_word('report') + r' `([^`]+)`')
STARTED_RE = re.compile(any_word('started') + r' (\d{4}-\d{2}-\d{2})')
FINISHED_RE = re.compile(any_word('finished') + r' (\d{4}-\d{2}-\d{2})')
ID_RE = re.compile(r'`([a-z0-9-]+)`')
DETAIL_SUFFIXES = tuple(row['detail'] for row in VOCABULARY)


class BoardError(Exception):
    """A board file could not be read; the message names it."""


@dataclass
class Card:
    id: str
    summary: str
    title: str | None = None
    flag: bool = False
    prereqs: list[str] = field(default_factory=list)
    adjacent: list[str] = field(default_factory=list)
    branch: str | None = None
    report: str | None = None
    started: date | None = None
    finished: date | None = None


@dataclass
class Group:
    name: str | None
    cards: list[Card] = field(default_factory=list)


@dataclass
class Board:
    in_progress: list[Card]
    done: list[Card]
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
    rest = match.group(3).strip()
    for suffix in DETAIL_SUFFIXES:
        if rest.endswith(suffix):
            rest = rest[:-len(suffix)].strip()
    title = None
    if rest.startswith('·'):
        title, _, rest = rest[1:].partition(' — ')
        title = title.strip() or None
    elif rest.startswith('—'):
        rest = rest[1:]
    return Card(id=match.group(2), summary=rest.strip(), title=title, flag=bool(match.group(1)))


def found_date(pattern: re.Pattern, line: str) -> date | None:
    match = pattern.search(line)
    try:
        return date.fromisoformat(match.group(1)) if match else None
    except ValueError:
        return None


def apply_sub_bullet(card: Card, line: str) -> None:
    edge = EDGE_RE.match(line)
    if edge:
        target = card.prereqs if EDGE_KIND[edge.group(1)] == 'prereq' else card.adjacent
        target.extend(ID_RE.findall(edge.group(2)))
        return
    if STATUS_RE.match(line):
        branch = BRANCH_RE.search(line)
        report = REPORT_RE.search(line)
        card.branch = branch.group(1) if branch else None
        card.report = report.group(1) if report else None
        card.started = found_date(STARTED_RE, line)
        card.finished = found_date(FINISHED_RE, line)


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


def section_cards(lines: list[str], title: str) -> list[Card]:
    groups: list[Group] = []
    parse_cards(section(lines, title), groups)
    return [card for group in groups for card in group.cards]


def parse_board(board_text: str, archive_text: str) -> Board:
    lines = unfenced_lines(board_text)
    todo: list[Group] = []
    parse_cards(section(lines, 'ToDo'), todo)
    archived = {match.group(2) for line in unfenced_lines(archive_text) if (match := CARD_RE.match(line))}
    return Board(in_progress=section_cards(lines, 'In Progress'), done=section_cards(lines, 'Done'),
                 groups=todo, archived=archived)


def load_board(repo: Path) -> Board:
    texts = []
    for name in ('board.md', 'board-archive.md'):
        path = repo / 'docs' / name
        try:
            texts.append(path.read_text(encoding='utf-8-sig'))
        except OSError as error:
            raise BoardError(f'board: cannot read {path} ({error.strerror})') from None
        except UnicodeDecodeError:
            raise BoardError(f'board: cannot read {path} (not UTF-8 -- save it as UTF-8)') from None
    return parse_board(*texts)


def todo_cards(board: Board) -> list[Card]:
    return [card for group in board.groups for card in group.cards]


def judge(board: Board) -> Verdict:
    live = {card.id for card in todo_cards(board)}
    running = {card.id for card in board.in_progress}
    finished = board.archived | {card.id for card in board.done}
    blocked, stale, broken = [], [], []
    for card in todo_cards(board):
        for dep in card.prereqs:
            if dep in finished:
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
            f'In Progress {len({card.id for card in board.in_progress})} / '
            f'Done {len({card.id for card in board.done})} / archived {len(board.archived)}')


def format_ready(board: Board, verdict: Verdict) -> str:
    def block(title: str, items: list[str], keep_empty: bool = True) -> list[str]:
        if not items and not keep_empty:
            return []
        return ['', title] + ([f'  {item}' for item in items] or ['  (none)'])

    edges = lambda pairs: [f'{card} ← {dep}' for card, dep in pairs]  # noqa: E731
    lines = [counts_line(board)]
    lines += block(f'ready ({len(verdict.ready)})', verdict.ready)
    lines += block(f'blocked ({len(verdict.blocked)})', edges(verdict.blocked))
    lines += block(f'stale edges -- prerequisite already done; delete the line ({len(verdict.stale)})',
                   edges(verdict.stale), keep_empty=False)
    lines += block(f'broken edges -- prerequisite matches no card ({len(verdict.broken)})',
                   edges(verdict.broken), keep_empty=False)
    return '\n'.join(lines) + '\n'


TEMPLATE = Path(__file__).with_name('board-view.html')
MARKERS = ('title', 'header', 'todo', 'in-progress', 'done', 'details')
HEADING_RE = re.compile(r'^(#{1,3})\s+(.*)$')
BULLET_RE = re.compile(r'^[-*]\s+(.*)$')
NUMBERED_RE = re.compile(r'^\d+\.\s+(.*)$')
QUOTE_RE = re.compile(r'^>\s?(.*)$')


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(text))
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def render_issue(markdown: str) -> str:
    """The subset of Markdown an issue file uses: headings, lists, quotes, fences, paragraphs,
    inline code and bold. Everything is escaped first; anything else stays as plain text."""
    out: list[str] = []
    paragraph: list[str] = []
    quote: list[str] = []
    items: list[str] = []
    list_tag = ''
    code: list[str] | None = None

    def flush() -> None:
        nonlocal list_tag
        if paragraph:
            out.append(f'<p>{" ".join(paragraph)}</p>')
            paragraph.clear()
        if quote:
            out.append(f'<blockquote>{" ".join(quote)}</blockquote>')
            quote.clear()
        if items:
            out.append(f'<{list_tag}>' + ''.join(f'<li>{item}</li>' for item in items) + f'</{list_tag}>')
            items.clear()
        list_tag = ''

    for line in markdown.lstrip('﻿').replace('\r\n', '\n').split('\n'):
        if code is not None:
            if line.startswith('```'):
                out.append(f'<pre>{esc(chr(10).join(code))}</pre>')
                code = None
            else:
                code.append(line)
            continue
        heading, bullet = HEADING_RE.match(line), BULLET_RE.match(line)
        numbered, quoted = NUMBERED_RE.match(line), QUOTE_RE.match(line)
        if line.startswith('```'):
            flush()
            code = []
        elif heading:
            flush()
            level = len(heading.group(1)) + 2
            out.append(f'<h{level}>{inline(heading.group(2).strip())}</h{level}>')
        elif bullet or numbered:
            tag = 'ul' if bullet else 'ol'
            if tag != list_tag:
                flush()
                list_tag = tag
            items.append(inline((bullet or numbered).group(1).strip()))
        elif quoted:
            if items or paragraph:
                flush()
            quote.append(inline(quoted.group(1).strip()))
        elif not line.strip():
            flush()
        else:
            if items or quote:
                flush()
            paragraph.append(inline(line.strip()))
    if code is not None:
        out.append(f'<pre>{esc(chr(10).join(code))}</pre>')
    flush()
    return '\n'.join(out)


def blocked_ids(verdict: Verdict) -> set[str]:
    return {card_id for card_id, _ in verdict.blocked}


def edges_of(pairs: list[tuple[str, str]], card_id: str) -> list[str]:
    return [dep for owner, dep in pairs if owner == card_id]


def progress_meta(card: Card, now: datetime) -> str:
    parts = [card.branch] if card.branch else []
    if card.started:
        parts += [f'started {card.started:%m-%d}', f'day {(now.date() - card.started).days + 1}']
    return ' · '.join(parts)


def done_meta(card: Card) -> str:
    return f'done {card.finished:%m-%d}' if card.finished else ''


def card_html(card: Card, classes: str, head: str, badges: list[str], meta: str = '') -> str:
    """One line each: the id with its badges, the title, the summary. The page clips a line that
    does not fit; the detail panel shows the whole text."""
    badge_html = f'<span class="badges">{"".join(badges)}</span>' if badges else ''
    parts = [f'<article class="{classes}" data-card="{esc(card.id)}">',
             f'<div class="card-head">{head}<span class="id">{esc(card.id)}</span>{badge_html}</div>']
    if card.title:
        parts.append(f'<p class="title">{inline(card.title)}</p>')
    if card.summary:
        parts.append(f'<p class="summary">{inline(card.summary)}</p>')
    if meta:
        parts.append(f'<p class="meta">{esc(meta)}</p>')
    parts.append('</article>')
    return '\n'.join(parts)


def card_grid(articles: list[str]) -> str:
    if not articles:
        return '<p class="empty">none</p>'
    return '<div class="cards">\n' + '\n'.join(articles) + '\n</div>'


def detail_badge(card: Card, issues: dict[str, str]) -> list[str]:
    return ['<span class="badge detail">detail</span>'] if card.id in issues else []


def todo_badges(card: Card, verdict: Verdict, issues: dict[str, str]) -> list[str]:
    cleanup = edges_of(verdict.stale, card.id) or edges_of(verdict.broken, card.id)
    return (['<span class="badge cleanup">needs cleanup</span>'] if cleanup else []) + detail_badge(card, issues)


def render_todo(board: Board, verdict: Verdict, issues: dict[str, str]) -> str:
    """A ToDo card is ready unless it is dimmed, with what it waits on on its meta line."""
    if not board.groups:
        return '<p class="empty">none</p>'
    sections = []
    for group in board.groups:
        articles = []
        for rank, card in enumerate(group.cards, 1):
            head = f'<span class="rank">{rank}</span>' + ('<span class="flag">⚑</span>' if card.flag else '')
            waits_on = edges_of(verdict.blocked, card.id)
            classes = 'card blocked' if waits_on else 'card'
            meta = f'blocked ← {", ".join(waits_on)}' if waits_on else ''
            articles.append(card_html(card, classes, head, todo_badges(card, verdict, issues), meta))
        if group.name is None:
            parts = ['<section class="group">']
        else:
            parts = [f'<section class="group" data-group="{esc(group.name)}">',
                     f'<h3><button type="button" class="group-toggle" aria-expanded="true">'
                     f'<span class="group-name">{esc(group.name)}</span>'
                     f'<span class="count">{len(group.cards)}</span></button></h3>']
        parts += [card_grid(articles), '</section>']
        sections.append('\n'.join(parts))
    return '\n'.join(sections)


def render_in_progress(board: Board, issues: dict[str, str], now: datetime) -> str:
    return card_grid([card_html(card, 'card', '', detail_badge(card, issues), progress_meta(card, now))
                      for card in board.in_progress])


def render_done(board: Board, issues: dict[str, str]) -> str:
    return card_grid([card_html(card, 'card', '', detail_badge(card, issues), done_meta(card))
                      for card in board.done])


def edge_list(ids: list[str]) -> str:
    return ', '.join(f'<code>{esc(card_id)}</code>' for card_id in ids)


def render_detail(card: Card, place: str, verdict: Verdict, issues: dict[str, str]) -> str:
    rows = []
    for label, ids in (('waiting on', edges_of(verdict.blocked, card.id)),
                       ('stale prerequisite (already archived)', edges_of(verdict.stale, card.id)),
                       ('broken prerequisite (no such card)', edges_of(verdict.broken, card.id)),
                       ('adjacent', card.adjacent)):
        if ids:
            rows.append(f'<dt>{label}</dt><dd>{edge_list(ids)}</dd>')
    parts = [f'<template id="detail-{esc(card.id)}">', f'<h2>{esc(card.id)}</h2>']
    if card.title:
        parts.append(f'<p class="title">{inline(card.title)}</p>')
    parts.append(f'<p class="meta">{esc(place)}</p>')
    if card.summary:
        parts.append(f'<p class="summary">{inline(card.summary)}</p>')
    if rows:
        parts.append(f'<dl>{"".join(rows)}</dl>')
    if card.id in issues:
        parts.append(f'<div class="issue">{render_issue(issues[card.id])}</div>')
    else:
        parts.append('<p class="empty">no issue file</p>')
    parts.append('</template>')
    return '\n'.join(parts)


def render_details(board: Board, verdict: Verdict, issues: dict[str, str], now: datetime) -> str:
    waiting = blocked_ids(verdict)
    parts = []
    for card in board.in_progress:
        meta = progress_meta(card, now)
        parts.append(render_detail(card, 'in progress' + (f' · {meta}' if meta else ''), verdict, issues))
    for card in board.done:
        parts.append(render_detail(card, done_meta(card) or 'done', verdict, issues))
    for group in board.groups:
        for rank, card in enumerate(group.cards, 1):
            state = 'blocked' if card.id in waiting else 'ready'
            place = f'{group.name or "ToDo"} · #{rank} · {state}'
            parts.append(render_detail(card, place, verdict, issues))
    return '\n'.join(parts)


def cleanup_line(verdict: Verdict) -> str:
    if not (verdict.stale or verdict.broken):
        return ''
    return (f'needs cleanup: {len(verdict.stale)} stale, {len(verdict.broken)} broken edges '
            f'-- run scripts/board ready for the list')


def render_header(board: Board, verdict: Verdict, project: str, now: datetime) -> str:
    parts = [f'<h1>{esc(project)}</h1>',
             f'<p class="meta">generated {now:%Y-%m-%d %H:%M} · ready {len(verdict.ready)} · '
             f'blocked {len(blocked_ids(verdict))} · in progress {len(board.in_progress)} · '
             f'done {len(board.done)} · archived {len(board.archived)}</p>']
    notice = cleanup_line(verdict)
    if notice:
        parts.append(f'<p class="notice">{esc(notice)}</p>')
    return '\n'.join(parts)


def render_view(board: Board, verdict: Verdict, issues: dict[str, str], project: str, now: datetime) -> str:
    page = TEMPLATE.read_text(encoding='utf-8-sig')
    fills = {
        'title': esc(project),
        'header': render_header(board, verdict, project, now),
        'todo': render_todo(board, verdict, issues),
        'in-progress': render_in_progress(board, issues, now),
        'done': render_done(board, issues),
        'details': render_details(board, verdict, issues, now),
    }
    for name in MARKERS:
        marker = f'<!--BOARD:{name}-->'
        if page.count(marker) != 1:
            raise ValueError(f'{TEMPLATE.name}: marker {marker} must appear exactly once')
        page = page.replace(marker, fills[name])
    return page


def read_issues(repo: Path, board: Board) -> dict[str, str]:
    issues = {}
    for card in board.in_progress + board.done + todo_cards(board):
        path = repo / 'docs' / 'issues' / f'{card.id}.md'
        try:
            issues[card.id] = path.read_text(encoding='utf-8-sig', errors='replace')
        except OSError:
            continue
    return issues


def default_output(project: str) -> Path:
    return Path(tempfile.gettempdir()) / f'board-view-{re.sub(r"[^A-Za-z0-9._-]", "_", project)}.html'


def run_ready(repo: Path) -> int:
    board = load_board(repo)
    verdict = judge(board)
    sys.stdout.write(format_ready(board, verdict))
    return 1 if verdict.stale or verdict.broken else 0


def run_view(repo: Path, out: Path | None, open_browser: bool) -> int:
    board = load_board(repo)
    verdict = judge(board)
    project = repo.resolve().name or str(repo)
    path = out or default_output(project)
    page = render_view(board, verdict, read_issues(repo, board), project, datetime.now())
    path.write_bytes(page.encode('utf-8'))
    lines = [f'board view: {path}',
             f'{counts_line(board)} -- ready {len(verdict.ready)}, blocked {len(blocked_ids(verdict))}']
    if cleanup_line(verdict):
        lines.append(cleanup_line(verdict))
    sys.stdout.write('\n'.join(lines) + '\n')
    if open_browser:
        webbrowser.open(path.resolve().as_uri())
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='replace', newline='\n')
    parser = argparse.ArgumentParser(description='Read the work board (docs/board.md).')
    parser.add_argument('--repo', type=Path, default=Path(DEFAULT_REPO),
                        help='project root holding docs/board.md (default: the main tree)')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('ready', help='startable, blocked, stale and broken cards')
    view = commands.add_parser('view', help='open the board as a read-only kanban page')
    view.add_argument('--out', type=Path, help='write the page here instead of the temp directory')
    view.add_argument('--no-open', action='store_true', help='write the page without opening a browser')
    args = parser.parse_args(argv)
    try:
        if args.command == 'view':
            return run_view(args.repo, args.out, not args.no_open)
        return run_ready(args.repo)
    except BoardError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
