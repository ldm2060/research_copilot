# Manual integration smoke test for copilot guard hooks.
# Usage: pwsh -File self/hooks/tests/integration_run.ps1
#
# Exercises each hook with fake stdin payloads and asserts the decision JSON.
# Does NOT register the hooks in .claude/settings.json (Task 20 does that).

$ErrorActionPreference = "Stop"
$python = "D:/article/.venv/Scripts/python.exe"
$repo = "D:/article"

$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("copilot-smoke-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpRoot | Out-Null
$workspace = $tmpRoot
New-Item -ItemType Directory -Path "$workspace/.copilot" | Out-Null

function Run-Hook ($script, $payload) {
    $json = $payload | ConvertTo-Json -Compress -Depth 10
    $stdinFile = Join-Path $tmpRoot "stdin.txt"
    Set-Content -Path $stdinFile -Value $json -NoNewline -Encoding UTF8
    $stdoutFile = Join-Path $tmpRoot "stdout.txt"
    $stderrFile = Join-Path $tmpRoot "stderr.txt"
    $proc = Start-Process -FilePath $python `
        -ArgumentList "$repo/self/hooks/scripts/$script" `
        -WorkingDirectory $workspace `
        -RedirectStandardInput $stdinFile `
        -RedirectStandardOutput $stdoutFile `
        -RedirectStandardError $stderrFile `
        -NoNewWindow -PassThru -Wait
    return (Get-Content $stdoutFile -Raw)
}

function Assert ($cond, $msg) {
    if (-not $cond) {
        Write-Host "FAIL: $msg" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: $msg" -ForegroundColor Green
}

# Sanity: scripts import cleanly
& $python -c "import sys; sys.path.insert(0, '$repo/self/hooks/scripts'); import _copilot_hook_lib, copilot_write_guard, copilot_subagent_stop"
Assert ($LASTEXITCODE -eq 0) "scripts import cleanly"

# Test 1: PreToolUse — literature writing ideas.md → deny
$lit = Join-Path $tmpRoot "lit.jsonl"
'{"role":"assistant","metadata":{"subagent_type":"copilot-literature"}}' | Set-Content -Path $lit -Encoding UTF8
$payload = @{
    tool_name = "Write"
    tool_input = @{ file_path = (Join-Path $workspace ".copilot/ideas.md") }
    transcript_path = $lit
}
$out = Run-Hook -script "copilot_write_guard.py" -payload $payload
Assert ($out -match '"deny"') "PreToolUse denies non-owned write (copilot-literature -> ideas.md)"

# Test 2: SubagentStop — first boot, no snapshot, no handoff → allow + NO-SNAPSHOT log
$payload = @{ transcript_path = $lit; stop_hook_active = $false }
$out = Run-Hook -script "copilot_subagent_stop.py" -payload $payload
Assert ($out -match '"allow"') "SubagentStop allows on first boot (SOFT degrade)"

$log = Get-Content "$workspace/.copilot/__violations.log" -Raw -ErrorAction SilentlyContinue
Assert ($log -and $log -match "NO-SNAPSHOT") "violations.log records NO-SNAPSHOT entry"

Write-Host "ALL INTEGRATION CHECKS PASSED" -ForegroundColor Green
Remove-Item -Recurse -Force $tmpRoot
exit 0
