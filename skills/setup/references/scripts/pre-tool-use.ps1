# PreToolUse hook.
#   Read / Skill  -> record that a required doc or skill was consumed this session.
#   Edit / Write  -> gate the edit on a rule's "requires", then emit reminders.
# All literals are ASCII; rule data lives in file-pattern-map.json (UTF-8).
# Reminders fire at most once per session per rule; the gate is checked on every
# edit until satisfied. Any unexpected failure exits 0 (fail-open) so a broken
# hook never blocks work.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$stdin = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($stdin)) { exit 0 }

try {
    $inObj = $stdin | ConvertFrom-Json
} catch {
    exit 0
}

$toolName = $inObj.tool_name
if ($toolName -ne 'Edit' -and $toolName -ne 'Write' -and $toolName -ne 'Read' -and $toolName -ne 'Skill') {
    exit 0
}

$sessionId = $inObj.session_id
if ([string]::IsNullOrWhiteSpace($sessionId)) { $sessionId = 'noid' }
$sessionIdSafe = ($sessionId -replace '[^a-zA-Z0-9_-]', '_')

$projRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# Project-relative path. Recognizes the worktree convention
# <parent>/<Repo>-worktrees/<folder>/<rel> first: those paths share a string prefix
# with the main tree and would otherwise be mangled into "-worktrees/...".
function Get-RelPath([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return '' }
    $n = $p.Replace([char]92, [char]47)
    if ($n -match '/[^/]+-worktrees/[^/]+/(.+)$') { return $Matches[1] }
    $r = $projRoot.Replace([char]92, [char]47).TrimEnd([char]47)
    if ($n.ToLower().StartsWith(($r + '/').ToLower())) { return $n.Substring($r.Length + 1) }
    return $n
}

$stateDir = Join-Path $env:TEMP 'claude-code-hook-state'
try {
    if (-not (Test-Path -LiteralPath $stateDir)) {
        [void](New-Item -ItemType Directory -Path $stateDir -Force)
    }
} catch { exit 0 }

$firedFile = Join-Path $stateDir "fired-rules-$sessionIdSafe.txt"
$doneFile = Join-Path $stateDir "requires-done-$sessionIdSafe.txt"

function Read-Lines([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return @() }
    $loaded = Get-Content -LiteralPath $path -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($loaded) { return @($loaded) }
    return @()
}

function Add-Line([string]$path, [string]$value) {
    $existing = Read-Lines $path
    if ($existing -contains $value) { return }
    $all = @($existing) + @($value) | Select-Object -Unique
    $all | Out-File -LiteralPath $path -Encoding UTF8 -Force
}

# ---- Observation: record consumed docs and skills, never block ----

if ($toolName -eq 'Read') {
    $rel = Get-RelPath $inObj.tool_input.file_path
    if (-not [string]::IsNullOrWhiteSpace($rel)) {
        try { Add-Line $doneFile ("read:" + $rel.ToLower()) } catch { }
    }
    exit 0
}

if ($toolName -eq 'Skill') {
    $skill = $inObj.tool_input.skill
    if (-not [string]::IsNullOrWhiteSpace($skill)) {
        # Plugin skills arrive as "plugin:skill"; record the bare name too.
        $bare = ($skill -split ':')[-1]
        try {
            Add-Line $doneFile ("skill:" + $skill.ToLower())
            Add-Line $doneFile ("skill:" + $bare.ToLower())
        } catch { }
    }
    exit 0
}

# ---- Edit / Write: match rules, gate, then remind ----

$filePath = $inObj.tool_input.file_path
if ([string]::IsNullOrWhiteSpace($filePath)) { exit 0 }
$rel = Get-RelPath $filePath
$fileName = Split-Path $rel -Leaf

$rulesPath = Join-Path $PSScriptRoot 'file-pattern-map.json'
if (-not (Test-Path -LiteralPath $rulesPath)) { exit 0 }
try {
    $rulesRoot = Get-Content -LiteralPath $rulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    exit 0
}
$rules = $rulesRoot.rules
if ($null -eq $rules) { exit 0 }

$matched = @()
foreach ($rule in $rules) {
    if ($rule.scopePath -and $rule.scopePath.Count -gt 0) {
        $inScope = $false
        foreach ($sp in $rule.scopePath) {
            if ($rel -like "$sp*") { $inScope = $true; break }
        }
        if (-not $inScope) { continue }
    }

    if ($rule.excludePath -and $rule.excludePath.Count -gt 0) {
        $excluded = $false
        foreach ($ep in $rule.excludePath) {
            if ($rel -like "*$ep*") { $excluded = $true; break }
        }
        if ($excluded) { continue }
    }

    $patternMatched = $false
    foreach ($pat in $rule.patterns) {
        if ($fileName -like $pat -or $rel -like $pat) {
            $patternMatched = $true; break
        }
    }
    if (-not $patternMatched) { continue }

    $matched += $rule
}

if ($matched.Count -eq 0) { exit 0 }

# Gate: every matched rule carrying "requires" must have its docs read and skills
# loaded this session.
$done = Read-Lines $doneFile
$missing = @()
foreach ($r in $matched) {
    if ($null -eq $r.requires) { continue }
    if ($r.requires.reads) {
        foreach ($doc in $r.requires.reads) {
            if (-not ($done -contains ("read:" + $doc.ToLower()))) {
                $missing += "Read: $doc"
            }
        }
    }
    if ($r.requires.skills) {
        foreach ($sk in $r.requires.skills) {
            if (-not ($done -contains ("skill:" + $sk.ToLower()))) {
                $missing += "Skill: $sk"
            }
        }
    }
}

if ($missing.Count -gt 0) {
    $missing = $missing | Select-Object -Unique
    $reasonLines = @("This edit is gated: required project guides have not been loaded in this session.")
    $reasonLines += "Do these first, then retry the edit:"
    foreach ($m in $missing) { $reasonLines += "  - $m" }
    $reasonLines += "They carry the rules this edit must follow."
    $reasonLines += "Use the Read tool and the Skill tool -- reading a doc through a shell command does not count."
    $reason = $reasonLines -join "`n"

    $denyPayload = [pscustomobject]@{
        hookSpecificOutput = [pscustomobject]@{
            hookEventName            = 'PreToolUse'
            permissionDecision       = 'deny'
            permissionDecisionReason = $reason
        }
    }
    [Console]::Out.Write(($denyPayload | ConvertTo-Json -Depth 10 -Compress))
    exit 0
}

# Reminders: once per rule per session.
$fired = Read-Lines $firedFile
$fresh = @($matched | Where-Object { -not ($fired -contains $_.id) })
if ($fresh.Count -eq 0) { exit 0 }

$lines = @('Project guide reminders (first match this session):')
foreach ($r in $fresh) {
    $lines += "[$($r.id)] $($r.message)"
}
$context = $lines -join "`n"

try {
    foreach ($r in $fresh) { Add-Line $firedFile $r.id }
} catch { }

$payload = [pscustomobject]@{
    hookSpecificOutput = [pscustomobject]@{
        hookEventName     = 'PreToolUse'
        additionalContext = $context
    }
}
[Console]::Out.Write(($payload | ConvertTo-Json -Depth 10 -Compress))
