# PreToolUse hook (Edit|Write|Read|Skill).
#   Read / Skill  -> record that a required doc or skill was consumed this session.
#   Edit / Write  -> lint the text being written, gate the edit on a rule's
#                    "requires", then emit reminders.
# All literals are ASCII; rule data lives in file-pattern-map.json and
# content-lint.json (both UTF-8).
# Reminders fire at most once per session per rule; the gate is checked on every
# edit until satisfied. Any unexpected failure exits 0 (fail-open) so a broken
# hook never blocks work.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Read stdin as UTF-8 explicitly. [Console]::In decodes piped input with the console
# codepage, which mangles every non-ASCII character in the payload before the content
# lint below can see it -- a banned character arrives as '?' and slips through.
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

# Both rule files share the same file-matching shape, so they share the loader and
# the matcher. A rule with no usable data is skipped, never treated as "matches all".
function Read-RuleFile([string]$name) {
    $p = Join-Path $PSScriptRoot $name
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    try {
        return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-RuleMatch($rule, [string]$rel, [string]$fileName) {
    if ($null -eq $rule.patterns -or @($rule.patterns).Count -eq 0) { return $false }

    if ($rule.scopePath -and @($rule.scopePath).Count -gt 0) {
        $inScope = $false
        foreach ($sp in $rule.scopePath) {
            if ($rel -like "$sp*") { $inScope = $true; break }
        }
        if (-not $inScope) { return $false }
    }

    if ($rule.excludePath -and @($rule.excludePath).Count -gt 0) {
        foreach ($ep in $rule.excludePath) {
            if ($rel -like "*$ep*") { return $false }
        }
    }

    foreach ($pat in $rule.patterns) {
        if ($fileName -like $pat -or $rel -like $pat) { return $true }
    }
    return $false
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

# ---- Edit / Write: lint the payload, match rules, gate, then remind ----

$filePath = $inObj.tool_input.file_path
if ([string]::IsNullOrWhiteSpace($filePath)) { exit 0 }
$rel = Get-RelPath $filePath
$fileName = Split-Path $rel -Leaf

# ---- Content lint: block a write carrying a violation that needs no judgment ----
# Only patterns that are always a violation belong in content-lint.json. Anything
# needing a judgment call -- a redundant comment, non-local information, a duplicated
# contract -- is the commit-time comment audit's job, not this hook's.
# Runs before the requires gate and independently of file-pattern-map.json: a banned
# character is banned whether or not the file also has a guide to read first.

$lintRoot = Read-RuleFile 'content-lint.json'
if ($null -ne $lintRoot -and $null -ne $lintRoot.rules) {
    $lintRules = @($lintRoot.rules | Where-Object { Test-RuleMatch $_ $rel $fileName })
}
else {
    $lintRules = @()
}

if ($lintRules.Count -gt 0) {
    if ($toolName -eq 'Edit') { $payloadText = [string]$inObj.tool_input.new_string }
    else { $payloadText = [string]$inObj.tool_input.content }

    $found = @()
    if (-not [string]::IsNullOrEmpty($payloadText)) {
        $payloadLines = $payloadText -split "`n"

        foreach ($lr in $lintRules) {
            # Banned characters are declared as code points, never as literals: this file
            # is ASCII-only so a literal here would be mangled by a non-UTF-8 codepage.
            foreach ($bc in @($lr.bannedChars)) {
                if ($null -eq $bc) { continue }
                try { $ch = [char][Convert]::ToInt32([string]$bc.codePoint, 16) } catch { continue }
                if ($payloadText.IndexOf($ch) -ge 0) {
                    $fix = [string]$bc.name
                    if (-not [string]::IsNullOrWhiteSpace([string]$bc.replacement)) {
                        $fix += " -> '" + [string]$bc.replacement + "'"
                    }
                    $found += ("Banned character: " + $fix)
                }
            }

            $bannedLines = @($lr.bannedLines)
            if ($bannedLines.Count -eq 0) { continue }
            $commentPrefixes = @($lr.commentPrefixes)

            foreach ($rawLine in $payloadLines) {
                $line = $rawLine.TrimEnd([char]13)

                # The comment span of the line, for entries scoped to comments only.
                $commentText = ''
                foreach ($cp in $commentPrefixes) {
                    if ([string]::IsNullOrEmpty([string]$cp)) { continue }
                    $at = $line.IndexOf([string]$cp)
                    if ($at -ge 0) { $commentText = $line.Substring($at); break }
                }

                foreach ($bl in $bannedLines) {
                    if ($null -eq $bl -or [string]::IsNullOrWhiteSpace([string]$bl.regex)) { continue }
                    if ([string]$bl.scope -eq 'comment') { $subject = $commentText }
                    else { $subject = $line }
                    if ([string]::IsNullOrEmpty($subject)) { continue }
                    try { $hit = $subject -match ([string]$bl.regex) } catch { continue }
                    if ($hit) {
                        $found += ([string]$bl.message + ": " + $subject.Trim())
                    }
                }
            }
        }
    }

    $found = @($found | Select-Object -Unique)
    if ($found.Count -gt 0) {
        $lintLines = @('This edit is blocked: it writes something the project forbids outright.')
        foreach ($f in $found) { $lintLines += "  - $f" }
        $lintLines += 'Rewrite the edit without it, then retry.'
        $lintLines += 'These are not judgment calls and have no exception to argue for.'
        Write-Deny ($lintLines -join "`n")
        exit 0
    }
}

# ---- File pattern rules: gate on "requires", then remind ----

$rulesRoot = Read-RuleFile 'file-pattern-map.json'
if ($null -eq $rulesRoot -or $null -eq $rulesRoot.rules) { exit 0 }

$matched = @($rulesRoot.rules | Where-Object { Test-RuleMatch $_ $rel $fileName })
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
    Write-Deny ($reasonLines -join "`n")
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
