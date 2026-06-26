# Story 2.15: Offline full-flow smoke test for GraceTree Shorts Studio on Windows.
#
# Prerequisites:
#   - App installed via install.ps1
#   - Network adapter disabled or firewall blocking outbound (verified in Step 2)
#   - No Python or FFmpeg on system PATH
#     CI runners have Python installed; pass -SkipPathCheck to allow it.
#
# Checks:
#   1. PATH isolation (system Python/FFmpeg absent — FAIL if found)
#   2. Network isolation probe (TCP to 8.8.8.8:53)
#   3. Engine health check with hard timeout + process kill (health_checked event)
#   4. Bundled FFmpeg and FFprobe versions readable
#   5. Emit pass/fail report artifact
#
# Usage:
#   .\offline-smoke.ps1 [-InstallDir "C:\...\GraceTree Shorts Studio"]
#                       [-SkipNetworkCheck]
#                       [-SkipPathCheck]
#
# Exit code: 0 = all passed, 1 = one or more failed, 2 = usage error

param(
  [string]$InstallDir = "$env:LOCALAPPDATA\Programs\GraceTree Shorts Studio",
  [switch]$SkipNetworkCheck,
  [switch]$SkipPathCheck
)

$ErrorActionPreference = 'Continue'
$failures = @()
$report = @()

function Pass($label, $detail = '') {
  $msg = "[PASS] $label$(if ($detail) { ': ' + $detail })"
  $script:report += $msg; Write-Host $msg
}
function Fail($label, $detail = '') {
  $msg = "[FAIL] $label$(if ($detail) { ': ' + $detail })"
  $script:report += $msg; Write-Host $msg
  $script:failures += $label
}
function Warn($msg) { Write-Host "[WARN] $msg" }

$resourcesDir = Join-Path $InstallDir 'resources'
$engineExe    = Join-Path $resourcesDir 'engine\gracetree-engine\gracetree-engine.exe'
$ffmpegExe    = Join-Path $resourcesDir 'ffmpeg\ffmpeg.exe'
$ffprobeExe   = Join-Path $resourcesDir 'ffmpeg\ffprobe.exe'

Write-Host "[offline-smoke] GraceTree Shorts Studio — Windows Offline Smoke Test"
Write-Host "[offline-smoke] Install dir: $InstallDir"
Write-Host ""

# 1. PATH isolation
if ($SkipPathCheck) {
  Warn "PATH isolation check skipped (-SkipPathCheck)"
} else {
  $sysPython  = Get-Command python  -ErrorAction SilentlyContinue
  $sysPython3 = Get-Command python3 -ErrorAction SilentlyContinue
  $sysFFmpeg  = Get-Command ffmpeg  -ErrorAction SilentlyContinue
  if (-not $sysPython -and -not $sysPython3) {
    Pass "No system Python on PATH"
  } else {
    $found = ($sysPython ?? $sysPython3).Source
    Fail "System Python found on PATH" "$found — engine must not fall back to it"
  }
  if (-not $sysFFmpeg) {
    Pass "No system FFmpeg on PATH"
  } else {
    Fail "System FFmpeg found on PATH" $sysFFmpeg.Source
  }
}

# 2. Network isolation — use Test-NetConnection (TCP/53) which correctly distinguishes RST vs timeout
if ($SkipNetworkCheck) {
  Warn "Network isolation check skipped (-SkipNetworkCheck)"
} else {
  $netTest = Test-NetConnection -ComputerName '8.8.8.8' -Port 53 -WarningAction SilentlyContinue
  if ($netTest.TcpTestSucceeded) {
    Fail "Network isolation" "TCP to 8.8.8.8:53 succeeded — network is NOT blocked"
  } else {
    Pass "Network is blocked (TCP to 8.8.8.8:53 unreachable)"
  }
}

# 3. Engine health check — unique temp files + hard timeout + kill on timeout
if (Test-Path $engineExe) {
  $healthInput = '{"protocolVersion":1,"type":"check_health","jobId":"offline-win-001","timestamp":"2026-06-26T00:00:00.000Z","payload":{}}'
  $uid = [System.Diagnostics.Process]::GetCurrentProcess().Id
  $stdinFile  = "$env:TEMP\gracetree-smoke-in-$uid.txt"
  $stdoutFile = "$env:TEMP\gracetree-smoke-out-$uid.txt"
  $stderrFile = "$env:TEMP\gracetree-smoke-err-$uid.txt"
  [System.IO.File]::WriteAllText($stdinFile, $healthInput + "`n")
  try {
    $proc = Start-Process -FilePath $engineExe -ArgumentList @() `
      -RedirectStandardInput $stdinFile `
      -RedirectStandardOutput $stdoutFile `
      -RedirectStandardError  $stderrFile `
      -NoNewWindow -PassThru
    $exited = $proc.WaitForExit(15000)
    if (-not $exited) {
      try { $proc.Kill() } catch { }
      Fail "Engine health check" "timed out after 15 s — engine process hung"
    } else {
      $out = Get-Content $stdoutFile -Raw -ErrorAction SilentlyContinue
      $err = (Get-Content $stderrFile -Raw -ErrorAction SilentlyContinue) ?? ''
      if ($out -match '"type"\s*:\s*"health_checked"') {
        Pass "Engine health check (bundled binary, no system Python)" "jobId: offline-win-001"
      } else {
        $detail = "stdout=$($out.Substring(0, [Math]::Min(120, $out.Length)))"
        if ($err) { $detail += " | stderr=$($err.Substring(0, [Math]::Min(120, $err.Length)))" }
        Fail "Engine health check" $detail
      }
    }
  } finally {
    Remove-Item $stdinFile, $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
  }
} else {
  Fail "Engine health check" "binary not found: $engineExe"
}

# 4. Bundled FFmpeg and FFprobe versions
foreach ($tool in @(@{Name='ffmpeg'; Path=$ffmpegExe}, @{Name='ffprobe'; Path=$ffprobeExe})) {
  if (Test-Path $tool.Path) {
    $ver = & $tool.Path -version 2>&1 | Select-Object -First 1
    if ($ver -match "$($tool.Name) version") {
      Pass "Bundled $($tool.Name) version readable" $ver
    } else {
      Fail "Bundled $($tool.Name) version readable" $ver
    }
  } else {
    Fail "Bundled $($tool.Name)" "not found: $($tool.Path)"
  }
}

# 5. Write report artifact
$reportPath = "$env:TEMP\gracetree-offline-smoke-report-$([System.Diagnostics.Process]::GetCurrentProcess().Id).txt"
$report | Out-File -FilePath $reportPath -Encoding utf8
Write-Host ""
Write-Host "[offline-smoke] Report written to: $reportPath"

if ($failures.Count -eq 0) {
  Write-Host "[offline-smoke] All checks PASSED"
  exit 0
} else {
  Write-Host "[offline-smoke] FAILED ($($failures.Count) check(s)):"
  $failures | ForEach-Object { Write-Host "  - $_" }
  exit 1
}
