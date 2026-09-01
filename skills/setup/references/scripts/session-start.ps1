# SessionStart / SubagentStart hook: inject project context as additionalContext.
# The same script is registered for both hooks so subagents see the same project
# context as the main session. Subagents do not inherit CLAUDE.md or the parent's
# SessionStart context; this hook is the official path that reaches them.
# All literals in this script are ASCII (PowerShell 5.1 reads BOM-less files as cp949).
# Injected files are read with -Encoding UTF8 so their Korean content survives.

param(
    [ValidateSet('SessionStart', 'SubagentStart')]
    [string] $HookEventName = 'SessionStart'
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# .claude/hooks -> project root
$projRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# Tiered injection (token efficiency).
# - Always (main + sub): the header (repeat-violation traps + on-demand doc index).
# - Main session only: the user-gate header. Those rules all face the user, and a
#   subagent neither sees the user nor holds AskUserQuestion. Injected into one, it
#   appends a turn-end block after its own output format and corrupts whatever
#   downstream stage parses that output.
# - Main session only: the workflow doc. Subagents do not run the git/report workflow.
# - On demand (NOT injected): everything the header index points at.
if ($HookEventName -eq 'SubagentStart') {
    $files = @(
        '.claude\hooks\session-start-header.md'
    )
} else {
    $files = @(
        '.claude\hooks\session-start-header.md',
        '.claude\hooks\main-session-header.md',
        'docs\workflow.md'
    )
}

$sb = [System.Text.StringBuilder]::new()
foreach ($rel in $files) {
    $full = Join-Path $projRoot $rel
    if (Test-Path -LiteralPath $full) {
        [void]$sb.AppendLine("=== $rel ===")
        [void]$sb.AppendLine((Get-Content -LiteralPath $full -Raw -Encoding UTF8))
        [void]$sb.AppendLine('')
    } else {
        [void]$sb.AppendLine("=== $rel (missing) ===")
        [void]$sb.AppendLine('')
    }
}

$payload = [pscustomobject]@{
    hookSpecificOutput = [pscustomobject]@{
        hookEventName     = $HookEventName
        additionalContext = $sb.ToString()
    }
}

$json = $payload | ConvertTo-Json -Depth 10 -Compress
[Console]::Out.Write($json)
