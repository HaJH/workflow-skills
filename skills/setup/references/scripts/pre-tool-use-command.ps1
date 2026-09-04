# PreToolUse hook for command and MCP-tool calls.
#   Bash / PowerShell -> deny a raw command that omits flags the project requires.
#   mcp__* tools      -> deny a tool call that omits fields the project requires.
# Both shapes are here because both are the same failure: a call reached through an
# autonomous flow, where the slash-command or skill file that carries the required
# arguments is not in context, so an argument is dropped and nothing notices.
# All literals are ASCII; rule data lives in command-gate.json (UTF-8).
# Any unexpected failure exits 0 (fail-open) so a broken hook never blocks work.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Read stdin as UTF-8 explicitly. [Console]::In decodes piped input with the console
# codepage, which mangles non-ASCII field names in the payload -- with a non-ASCII
# field name in a rule, every call would then be denied.
try {
    $stdinReader = [System.IO.StreamReader]::new([Console]::OpenStandardInput(), [System.Text.UTF8Encoding]::new($false))
    $stdin = $stdinReader.ReadToEnd()
} catch {
    exit 0
}
if ([string]::IsNullOrWhiteSpace($stdin)) { exit 0 }
$stdin = $stdin.TrimStart([char]0xFEFF)

try {
    $inObj = $stdin | ConvertFrom-Json
} catch {
    exit 0
}

$toolName = [string]$inObj.tool_name
if ([string]::IsNullOrWhiteSpace($toolName)) { exit 0 }

$rulesPath = Join-Path $PSScriptRoot 'command-gate.json'
if (-not (Test-Path -LiteralPath $rulesPath)) { exit 0 }
try {
    $rulesRoot = Get-Content -LiteralPath $rulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    exit 0
}

function Write-Deny([string]$reason) {
    $denyPayload = [pscustomobject]@{
        hookSpecificOutput = [pscustomobject]@{
            hookEventName            = 'PreToolUse'
            permissionDecision       = 'deny'
            permissionDecisionReason = $reason
        }
    }
    [Console]::Out.Write(($denyPayload | ConvertTo-Json -Depth 10 -Compress))
}

# Follows a dotted path into the tool input. A missing link returns $null rather than
# throwing, so a rule naming a field the caller never sent reads as "missing".
function Get-FieldValue($root, [string]$path) {
    $node = $root
    foreach ($seg in ($path -split '\.')) {
        if ($null -eq $node) { return $null }
        try { $node = $node.$seg } catch { return $null }
    }
    return $node
}

function Test-HasValue($value) {
    if ($null -eq $value) { return $false }
    if ($value -is [string]) { return -not [string]::IsNullOrWhiteSpace($value) }
    if ($value -is [System.Collections.IEnumerable]) { return (@($value).Count -gt 0) }
    return $true
}

# ---- Bash / PowerShell: required flags on a matched command ----

if ($toolName -eq 'Bash' -or $toolName -eq 'PowerShell') {
    $command = [string]$inObj.tool_input.command
    if ([string]::IsNullOrWhiteSpace($command)) { exit 0 }

    # Drop quoted spans first: a commit message or an MR description may legitimately
    # contain the guarded command as text, and matching it there blocks an unrelated
    # call. Only an invocation outside string literals counts. Handles here-strings too
    # (@'...'@ leaves the quotes paired). Then collapse whitespace so a line
    # continuation cannot hide a flag from the search.
    $unquoted = $command -replace "'[^']*'", ' ' -replace '"[^"]*"', ' '
    $flat = $unquoted -replace '\s+', ' '

    foreach ($rule in @($rulesRoot.commands)) {
        if ($null -eq $rule -or [string]::IsNullOrWhiteSpace([string]$rule.match)) { continue }
        try { $hit = $flat -match ([string]$rule.match) } catch { continue }
        if (-not $hit) { continue }

        $missing = @()
        foreach ($req in @($rule.requiredFlags)) {
            if ($null -eq $req -or [string]::IsNullOrWhiteSpace([string]$req.flag)) { continue }
            if ($flat -notmatch [regex]::Escape([string]$req.flag)) {
                $missing += ("  " + [string]$req.flag + " - " + [string]$req.why)
            }
        }
        if ($missing.Count -eq 0) { continue }

        $reason = @("Blocked: this command is missing arguments the project requires.", '') + $missing
        if (-not [string]::IsNullOrWhiteSpace([string]$rule.message)) {
            $reason += @('', [string]$rule.message)
        }
        Write-Deny ($reason -join "`n")
        exit 0
    }
    exit 0
}

# ---- MCP tools: required fields on a matched tool ----

foreach ($rule in @($rulesRoot.mcpTools)) {
    if ($null -eq $rule -or [string]::IsNullOrWhiteSpace([string]$rule.tool)) { continue }
    if ($toolName -ne [string]$rule.tool) { continue }

    $toolInput = $inObj.tool_input
    if ($null -eq $toolInput) { continue }

    $missing = @()
    foreach ($req in @($rule.requiredFields)) {
        if ($null -eq $req -or [string]::IsNullOrWhiteSpace([string]$req.field)) { continue }
        if (-not (Test-HasValue (Get-FieldValue $toolInput ([string]$req.field)))) {
            $missing += ("  " + [string]$req.field + " - " + [string]$req.why)
        }
    }
    if ($missing.Count -eq 0) { continue }

    $reason = @("Blocked: this tool call is missing fields the project requires.", '') + $missing
    if (-not [string]::IsNullOrWhiteSpace([string]$rule.message)) {
        $reason += @('', [string]$rule.message)
    }
    Write-Deny ($reason -join "`n")
    exit 0
}

exit 0
