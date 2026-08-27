#!/usr/bin/env bash
# Read the dependency edges out of docs/board.md and report what they imply.
#
#   bash {PROJECT_PATH}/scripts/board-ready.sh
#
# Edges live in one place and one format -- a `- 선행: `<id>`` bullet directly
# under a card (docs/board.md, "선행 줄"). Everything else about a card is prose
# for humans; this reads only that bullet.
#
# Three questions, because those are the ones prose cannot answer:
#
#   ready   -- cards nothing is blocking, so a session can pick one right now
#   stale   -- the prerequisite already merged, so the edge is a lie the card
#              keeps telling
#   broken  -- the prerequisite matches no card anywhere, so it is a typo or a
#              card someone dropped without looking at who pointed at it
#
# Exit status is 1 when anything is stale or broken, so this can gate a commit.

set -u

REPO=${REPO:-{PROJECT_PATH}}
BOARD="$REPO/docs/board.md"
ARCHIVE="$REPO/docs/board-archive.md"

for f in "$BOARD" "$ARCHIVE"; do
    [ -r "$f" ] || { echo "board-ready: cannot read $f" >&2; exit 2; }
done

# A card headline: a top-level bullet whose first inline-code span is the id.
# The `⚑` urgency marker may sit between the dash and the id.
CARD_RE='^- (⚑ )?\*\*`[a-z0-9-]+`\*\*'

ids_in() { grep -oE "$CARD_RE" | grep -oE '`[a-z0-9-]+`' | tr -d '`'; }

# The "형식" section documents the card syntax inside a fenced block, using the
# same markup as a real card. Drop fenced blocks before anything else or those
# illustrative ids enter the graph.
unfenced() { awk '/^```/{f=!f; next} !f' "$1"; }

todo_body() { unfenced "$BOARD" | awk '/^## ToDo$/{f=1} f'; }
running_body() { unfenced "$BOARD" | awk '/^## In Progress$/{f=1} /^## ToDo$/{f=0} f'; }

live=" $(todo_body | ids_in | sort -u | tr '\n' ' ') "
done_=" $(unfenced "$ARCHIVE" | ids_in | sort -u | tr '\n' ' ') "
# In Progress cards are neither ready nor blocking -- they are already running.
running=" $(running_body | ids_in | sort -u | tr '\n' ' ') "

has() { case "$1" in *" $2 "*) return 0 ;; *) return 1 ;; esac; }

ready=() blocked=() stale=() broken=()

# Walk the ToDo section, remembering the last card seen so a 선행 bullet can be
# attributed to it.
while IFS= read -r line; do
    if [[ $line =~ ^-\ (⚑\ )?\*\*\`([a-z0-9-]+)\`\*\* ]]; then
        card=${BASH_REMATCH[2]}
        continue
    fi
    [[ ${card:-} ]] || continue
    [[ $line =~ ^[[:space:]]+-[[:space:]]*선행: ]] || continue

    for dep in $(echo "$line" | grep -oE '`[a-z0-9-]+`' | tr -d '`'); do
        if has "$done_" "$dep"; then
            stale+=("$card ← $dep")
        elif has "$live" "$dep" || has "$running" "$dep"; then
            blocked+=("$card ← $dep")
        else
            broken+=("$card ← $dep")
        fi
    done
done < <(todo_body)

# A card is ready when no surviving edge names it. Recomputed from the blocked
# list rather than tracked inline, because a card with two prerequisites is
# blocked if either one survives.
blocked_ids=" $(printf '%s\n' "${blocked[@]:-}" | awk '{print $1}' | sort -u | tr '\n' ' ') "
for id in $(todo_body | ids_in); do
    has "$blocked_ids" "$id" || ready+=("$id")
done

section() { echo; echo "$1"; shift; [ $# -eq 0 ] && echo "  (none)" || printf '  %s\n' "$@"; }

echo "board: ToDo $(echo $live | wc -w) / In Progress $(echo $running | wc -w) / archived $(echo $done_ | wc -w)"

section "ready (${#ready[@]})" "${ready[@]:-}"
section "blocked (${#blocked[@]})" "${blocked[@]:-}"

fail=0
if [ ${#stale[@]} -gt 0 ]; then
    section "stale edges -- prerequisite already merged; delete the line (${#stale[@]})" "${stale[@]}"
    fail=1
fi
if [ ${#broken[@]} -gt 0 ]; then
    section "broken edges -- prerequisite matches no card (${#broken[@]})" "${broken[@]}"
    fail=1
fi

exit $fail
