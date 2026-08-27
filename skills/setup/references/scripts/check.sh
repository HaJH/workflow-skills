#!/usr/bin/env bash
# Verification gates. This file is the ONLY list of what "the gate" means for this
# project -- docs and commands point here instead of restating the commands.
#
#   bash scripts/check.sh
#
# Each gate REJECTS; none of them fixes. Run the formatter before this script.
# Exits on the first failing gate.
#
# Keep only the block for this project's stack and delete the rest. Add a gate by
# adding one `gate` line; never by listing the command in a document.

set -euo pipefail
cd "$(dirname "$0")/.."

gate() {
    local label=$1; shift
    echo "== gate: $label"
    "$@"
}

# ---- Rust ----
gate 'cargo fmt --check' cargo fmt --all --check
gate 'cargo clippy' cargo clippy --workspace --all-targets -- -D warnings
gate 'cargo test' cargo test --workspace
# gate 'cargo doc' cargo doc --workspace --no-deps

# ---- TypeScript (pnpm) ----
# gate 'lint' pnpm --dir ui lint
# gate 'typecheck' pnpm --dir ui typecheck
# gate 'build' pnpm --dir ui build

# ---- Python ----
# gate 'ruff' ruff check .
# gate 'ruff format --check' ruff format --check .
# gate 'mypy' mypy .
# gate 'pytest' pytest -q

# ---- C++ (CMake) ----
# gate 'configure' cmake -S . -B build
# gate 'build' cmake --build build --config Debug
# gate 'ctest' ctest --test-dir build --output-on-failure

echo "all gates passed"
