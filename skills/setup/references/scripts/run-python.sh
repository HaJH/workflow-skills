#!/usr/bin/env bash

if [[ $# -lt 1 ]]; then
    printf '%s\n' 'Usage: run-python.sh <script.py> [args...]' >&2
    exit 1
fi

script="$1"
shift
probe='import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'

for candidate in python3 python py; do
    launcher=("$candidate")
    if [[ "$candidate" == py ]]; then
        launcher+=(-3)
    fi
    if "${launcher[@]}" -c "$probe" </dev/null >/dev/null 2>&1; then
        exec "${launcher[@]}" "$script" "$@"
    fi
done

printf '%s\n' 'No working Python 3.9 or newer found (tried python3, python, py -3).' >&2
exit 1
