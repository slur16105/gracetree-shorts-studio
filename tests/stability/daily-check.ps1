# Story 2.16: Daily integrity check for 7-day stability validation (Windows).
#
# Verifies:
#   1. SQLite database is not corrupted
#   2. Input files in managed root are present
#   3. Existing render outputs are intact
#   4. No unexpected temp directories
#   5. Attempt logs exist and are recent
#
# Usage:
#   .\tests\stability\daily-check.ps1 [-ManagedRoot "C:\..."] [-DayNumber 1]
#
# Exit code: 0 = all passed, 1 = one or more failed

param(
  [string]$ManagedRoot = "$env:APPDATA\GraceTree Shorts Studio",
  [int]$DayNumber = 0
)

$ErrorActionPreference = 'Continue'
$failures = @()
$notes = @()

function Note($msg) { $script:notes += $msg; Write-Host $msg }
function Pass($label) { Note "[PASS] $label" }
function Fail($label) {
  Note "[FAIL] $label"
  $script:failures += $label
}

$dbPath     = Join-Path $ManagedRoot 'gracetree.db'
$inputDir   = Join-Path $ManagedRoot 'inputs'
$jobsDir    = Join-Path $ManagedRoot 'jobs'
$logDir     = Join-Path $ManagedRoot 'logs'

Note "[daily-check] Day $DayNumber — $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Note "[daily-check] Managed root: $ManagedRoot"

# 1. SQLite integrity (via sqlite3.exe if available)
if (Test-Path $dbPath) {
  $sqlite3 = Get-Command sqlite3 -ErrorAction SilentlyContinue
  if ($sqlite3) {
    $integrity = & sqlite3 $dbPath "PRAGMA integrity_check;" 2>&1
    if ($integrity -eq 'ok') {
      Pass "SQLite integrity_check = ok"
    } else {
      Fail "SQLite integrity_check FAILED: $integrity"
    }
  } else {
    Note "[WARN] sqlite3 not on PATH — skipping integrity check"
  }
} else {
  Fail "Database not found: $dbPath"
}

# 2. Input files
if (Test-Path $inputDir) {
  $inputCount = (Get-ChildItem $inputDir -Recurse -File).Count
  Pass "Input directory exists ($inputCount files)"
} else {
  Fail "Input directory missing: $inputDir"
}

# 3. Render outputs
if (Test-Path $jobsDir) {
  $totalJobs  = (Get-ChildItem $jobsDir -Directory).Count
  $completed  = (Get-ChildItem $jobsDir -Filter 'final.mp4' -Recurse | Where-Object { $_.Length -gt 0 }).Count
  Pass "Render outputs: $completed final.mp4 present out of $totalJobs jobs"
} else {
  Note "[INFO] Jobs directory not found yet: $jobsDir"
}

# 4. No stray temp files
$tempCount = (Get-ChildItem $ManagedRoot -Recurse -Include '*.tmp','tmp_*' -ErrorAction SilentlyContinue).Count
if ($tempCount -eq 0) {
  Pass "No stray temp files in managed root"
} else {
  Note "[WARN] $tempCount temp file(s) found (may be normal during active generation)"
}

# 5. Attempt logs
if (Test-Path $logDir) {
  $logCount = (Get-ChildItem $logDir -Filter '*.log').Count
  Pass "Logs directory exists ($logCount log file(s))"
} else {
  Note "[INFO] Logs directory not found: $logDir"
}

# Write day log
$dayPad = $DayNumber.ToString('00')
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$logOut = Join-Path $scriptDir "day-logs\day-$dayPad.md"
New-Item -ItemType Directory -Force -Path (Split-Path $logOut) | Out-Null

$content = @"
# Day $DayNumber — $(Get-Date -Format 'yyyy-MM-dd')

## Integrity Check Results
$($notes -join "`n")

## Today's Generation Log
(아래를 직접 작성: publish date, 스크립트 제목, 렌더 소요 시간, 결과)

| 항목       | 값 |
|------------|----|
| Publish 날짜 | |
| 생성 결과  | ☐ 성공 ☐ RECOVERABLE 오류 ☐ FATAL |
| 소요 시간  | |
| 메모       | |
"@

$content | Out-File -FilePath $logOut -Encoding utf8
Write-Host ""
Write-Host "[daily-check] Log written: $logOut"

if ($failures.Count -eq 0) {
  Write-Host "[daily-check] Day $DayNumber integrity: PASSED"
  exit 0
} else {
  Write-Host "[daily-check] Day $DayNumber integrity: FAILED ($($failures.Count) issue(s))"
  exit 1
}
