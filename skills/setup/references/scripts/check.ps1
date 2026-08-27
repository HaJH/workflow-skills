# Verification gates. This file is the ONLY list of what "the gate" means for this
# project -- docs and commands point here instead of restating the commands.
#
#   .\scripts\check.ps1
#
# Each gate REJECTS; none of them fixes. Run the formatter before this script.
# Exit code is non-zero on the first failing gate.
#
# Keep only the block for this project's stack and delete the rest. Add a gate by
# adding one Invoke-Gate line; never by listing the command in a document.

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Invoke-Gate([string]$label, [string]$exe, [string[]]$args) {
    Write-Host "== gate: $label"
    & $exe @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "gate failed: $label" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Push-Location $root
try {
    # ---- Rust ----
    Invoke-Gate 'cargo fmt --check' 'cargo' @('fmt', '--all', '--check')
    Invoke-Gate 'cargo clippy' 'cargo' @('clippy', '--workspace', '--all-targets', '--', '-D', 'warnings')
    Invoke-Gate 'cargo test' 'cargo' @('test', '--workspace')
    # Invoke-Gate 'cargo doc' 'cargo' @('doc', '--workspace', '--no-deps')

    # ---- TypeScript (pnpm) ----
    # Invoke-Gate 'lint' 'pnpm' @('--dir', 'ui', 'lint')
    # Invoke-Gate 'typecheck' 'pnpm' @('--dir', 'ui', 'typecheck')
    # Invoke-Gate 'build' 'pnpm' @('--dir', 'ui', 'build')

    # ---- Python ----
    # Invoke-Gate 'ruff' 'ruff' @('check', '.')
    # Invoke-Gate 'ruff format --check' 'ruff' @('format', '--check', '.')
    # Invoke-Gate 'mypy' 'mypy' @('.')
    # Invoke-Gate 'pytest' 'pytest' @('-q')

    # ---- C++ (CMake) ----
    # Invoke-Gate 'configure' 'cmake' @('-S', '.', '-B', 'build')
    # Invoke-Gate 'build' 'cmake' @('--build', 'build', '--config', 'Debug')
    # Invoke-Gate 'ctest' 'ctest' @('--test-dir', 'build', '--output-on-failure')
}
finally {
    Pop-Location
}

Write-Host "all gates passed" -ForegroundColor Green
