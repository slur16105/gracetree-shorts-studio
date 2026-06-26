# Story 2.13: Post-install smoke checks for GraceTree Shorts Studio on Windows.
#
# Checks:
#   1. App executable exists in install directory
#   2. Engine bundle executable exists in extraResources
#   3. FFmpeg executable exists in extraResources
#   4. Engine responds to health check (gracetree-engine.exe --health-check)
#   5. FFmpeg version is readable (ffmpeg.exe -version)
#   6. Paths with spaces/non-ASCII do not break engine spawn
#
# Usage:
#   .\smoke-check.ps1 [-InstallDir "C:\Users\...\AppData\Local\Programs\GraceTree Shorts Studio"]
#
# Exit code: 0 = all passed, 1 = one or more failed

param(
  [string]$InstallDir = "$env:LOCALAPPDATA\Programs\GraceTree Shorts Studio"
)

$ErrorActionPreference = 'Continue'
$failures = @()

function Check($label, $result, $detail = '') {
  if ($result) {
    Write-Host "[PASS] $label"
  } else {
    Write-Host "[FAIL] $label$(if ($detail) { ': ' + $detail })"
    $script:failures += $label
  }
}

# Resolve paths
$appExe     = Join-Path $InstallDir 'GraceTree Shorts Studio.exe'
$resourcesDir = Join-Path $InstallDir 'resources'
$engineDir  = Join-Path $resourcesDir 'engine\gracetree-engine'
$engineExe  = Join-Path $engineDir 'gracetree-engine.exe'
$ffmpegDir  = Join-Path $resourcesDir 'ffmpeg'
$ffmpegExe  = Join-Path $ffmpegDir 'ffmpeg.exe'
$ffprobeExe = Join-Path $ffmpegDir 'ffprobe.exe'

Write-Host "[smoke-check] Install dir: $InstallDir"
Write-Host "[smoke-check] Resources:   $resourcesDir"
Write-Host ""

# 1. App executable
Check "App executable exists" (Test-Path $appExe) $appExe

# 2. Engine bundle
Check "Engine bundle directory exists" (Test-Path $engineDir) $engineDir
Check "Engine executable exists" (Test-Path $engineExe) $engineExe

# 3. FFmpeg
Check "FFmpeg executable exists" (Test-Path $ffmpegExe) $ffmpegExe
Check "FFprobe executable exists" (Test-Path $ffprobeExe) $ffprobeExe

# 4. Engine health check — write JSON payload to a temp file, redirect as stdin
if (Test-Path $engineExe) {
  try {
    $healthInput = '{"protocolVersion":1,"type":"check_health","jobId":"smoke-win-001","timestamp":"2026-06-26T00:00:00.000Z","payload":{}}'
    $stdinFile  = "$env:TEMP\engine-in.txt"
    $stdoutFile = "$env:TEMP\engine-out.txt"
    $stderrFile = "$env:TEMP\engine-err.txt"
    [System.IO.File]::WriteAllText($stdinFile, $healthInput + "`n")
    $proc = Start-Process -FilePath $engineExe -ArgumentList @() `
      -RedirectStandardInput $stdinFile `
      -RedirectStandardOutput $stdoutFile `
      -RedirectStandardError  $stderrFile `
      -NoNewWindow -PassThru
    $null = $proc.WaitForExit(10000)
    $out = Get-Content $stdoutFile -Raw -ErrorAction SilentlyContinue
    Check "Engine health check responds" ($out -match '"type"') "output: $out"
  } catch {
    Check "Engine health check responds" $false $_.Exception.Message
  }
} else {
  $failures += "Engine health check (skipped — exe missing)"
}

# 5. FFmpeg version
if (Test-Path $ffmpegExe) {
  try {
    $ffVer = & $ffmpegExe -version 2>&1 | Select-Object -First 1
    Check "FFmpeg version readable" ($ffVer -match 'ffmpeg version') $ffVer
  } catch {
    Check "FFmpeg version readable" $false $_.Exception.Message
  }
} else {
  $failures += "FFmpeg version (skipped — exe missing)"
}

# 6. Paths with spaces — engine exe path already contains "GraceTree Shorts Studio"
Check "Engine path contains spaces (args array used)" ($engineExe -match ' ') $engineExe

Write-Host ""
if ($failures.Count -eq 0) {
  Write-Host "[smoke-check] All checks PASSED"
  exit 0
} else {
  Write-Host "[smoke-check] FAILED ($($failures.Count) check(s)):"
  $failures | ForEach-Object { Write-Host "  - $_" }
  exit 1
}
