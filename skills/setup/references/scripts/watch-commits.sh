#!/usr/bin/env bash
# Emit one event per new commit on feature/*|hotfix/* branches that is not yet in main.
#
# The PM session arms this as a persistent Monitor so Dev's progress surfaces in
# real time: worktrees share the repository, so commits made by a Dev subagent in
# its own worktree are visible from the main tree the moment they land.
#
#   Monitor(command: "bash {PROJECT_PATH}/scripts/watch-commits.sh",
#           persistent: true, description: "Dev commit progress")
#
# Every commit present at arming time is treated as already seen, so starting a
# session never replays existing history.

REPO={PROJECT_PATH}
POLL_SECONDS=60
STAT_LINE_LIMIT=25
PATTERNS=('refs/heads/feature/*' 'refs/heads/hotfix/*')

# Errors are swallowed throughout: a branch can be merged or deleted mid-poll,
# and that must not take the monitor down.
branches() {
    git -C "$REPO" for-each-ref --format='%(refname:short)' "${PATTERNS[@]}" 2>/dev/null
}

pending() {
    git -C "$REPO" rev-list --reverse "main..$1" 2>/dev/null
}

seen=$(for b in $(branches); do pending "$b"; done | sort -u | tr '\n' ' ')

while true; do
    for branch in $(branches); do
        for sha in $(pending "$branch"); do
            case " $seen " in *" $sha "*) continue ;; esac
            seen="$seen$sha "

            # Position of this commit within the branch, so the reader can tell
            # a first sketch from a tenth follow-up.
            index=$(git -C "$REPO" rev-list --count "main..$sha" 2>/dev/null)
            echo "[$branch #$index] $(git -C "$REPO" log -1 --format='%h %s' "$sha" 2>/dev/null)"
            # Capped: Monitor stops itself when a single event floods the chat.
            git -C "$REPO" show --stat --format='' "$sha" 2>/dev/null |
                grep -v '^$' | head -"$STAT_LINE_LIMIT"
        done
    done
    sleep "$POLL_SECONDS"
done
