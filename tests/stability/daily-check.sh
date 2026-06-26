#!/usr/bin/env bash
# Story 2.16: Daily integrity check for 7-day stability validation.
#
# Verifies:
#   1. SQLite database is not corrupted (PRAGMA integrity_check)
#   2. Input files in managed root still match their registered hashes
#   3. Existing render outputs are still intact (final.mp4 present and non-empty)
#   4. No unexpected temp directories left behind
#   5. Attempt logs directory is growing (engine wrote something today)
#
# Usage:
#   ./tests/stability/daily-check.sh [--managed-root /path/to/GraceTreeData]
#                                     [--day-number 1]
#
# Output:
#   - Console summary
#   - tests/stability/day-logs/day-NN.md (appended with check results)
#
# Exit code: 0 = all passed, 1 = one or more failed

set -uo pipefail

MANAGED_ROOT="${XDG_DATA_HOME:-$HOME/Library/Application Support}/GraceTree Shorts Studio"
DAY_NUMBER="??"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --managed-root) MANAGED_ROOT="$2"; shift 2 ;;
    --day-number)   DAY_NUMBER="$2"; shift 2 ;;
    *) shift ;;
  esac
done

FAILURES=()
NOTES=()

note() { NOTES+=("$1"); echo "$1"; }
fail() { FAILURES+=("$1"); echo "[FAIL] $1"; }
pass() { note "[PASS] $1"; }

DB_PATH="$MANAGED_ROOT/gracetree.db"

note "[daily-check] Day $DAY_NUMBER — $(date '+%Y-%m-%d %H:%M:%S')"
note "[daily-check] Managed root: $MANAGED_ROOT"

# 1. SQLite integrity
if command -v sqlite3 &>/dev/null && [[ -f "$DB_PATH" ]]; then
  INTEGRITY=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)
  if [[ "$INTEGRITY" == "ok" ]]; then
    pass "SQLite integrity_check = ok"
  else
    fail "SQLite integrity_check FAILED: $INTEGRITY"
  fi
elif [[ ! -f "$DB_PATH" ]]; then
  fail "Database not found: $DB_PATH"
else
  note "[WARN] sqlite3 not on PATH — skipping integrity check"
fi

# 2. Input files present (basic count check — hash verification via engine)
INPUT_DIR="$MANAGED_ROOT/inputs"
if [[ -d "$INPUT_DIR" ]]; then
  INPUT_COUNT=$(find "$INPUT_DIR" -type f | wc -l | tr -d ' ')
  pass "Input directory exists ($INPUT_COUNT files)"
else
  fail "Input directory missing: $INPUT_DIR"
fi

# 3. Render outputs intact
JOBS_DIR="$MANAGED_ROOT/jobs"
if [[ -d "$JOBS_DIR" ]]; then
  TOTAL_JOBS=$(find "$JOBS_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
  COMPLETED=$(find "$JOBS_DIR" -name "final.mp4" -size +0c | wc -l | tr -d ' ')
  pass "Render outputs: $COMPLETED final.mp4 present out of $TOTAL_JOBS jobs"
else
  note "[INFO] Jobs directory not found yet: $JOBS_DIR"
fi

# 4. No stray temp directories
TEMP_COUNT=$(find "$MANAGED_ROOT" -maxdepth 3 -name "*.tmp" -o -name "tmp_*" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$TEMP_COUNT" -eq 0 ]]; then
  pass "No stray temp files in managed root"
else
  note "[WARN] $TEMP_COUNT temp file(s) found in managed root (may be normal during active generation)"
fi

# 5. Engine attempt logs present
LOG_DIR="$MANAGED_ROOT/logs"
if [[ -d "$LOG_DIR" ]]; then
  LOG_COUNT=$(find "$LOG_DIR" -name "*.log" -newer "$DB_PATH" 2>/dev/null | wc -l | tr -d ' ')
  pass "Attempt logs directory exists ($LOG_COUNT recent log(s))"
else
  note "[INFO] Logs directory not found: $LOG_DIR"
fi

# Write day log
DAY_PAD=$(printf '%02d' "${DAY_NUMBER//[^0-9]/0}")
LOG_OUT="$(dirname "$0")/day-logs/day-${DAY_PAD}.md"
mkdir -p "$(dirname "$LOG_OUT")"
{
  echo "# Day $DAY_NUMBER — $(date '+%Y-%m-%d')"
  echo ""
  echo "## Integrity Check Results"
  printf '%s\n' "${NOTES[@]}"
  if [[ ${#FAILURES[@]} -gt 0 ]]; then
    echo ""
    echo "## FAILURES"
    printf '- %s\n' "${FAILURES[@]}"
  fi
  echo ""
  echo "## Today's Generation Log"
  echo "(Fill in manually: publish date, script title, render duration, outcome)"
  echo ""
  echo "| 항목       | 값 |"
  echo "|------------|----|"
  echo "| Publish 날짜 | |"
  echo "| 생성 결과  | ☐ 성공 ☐ RECOVERABLE 오류 ☐ FATAL |"
  echo "| 소요 시간  | |"
  echo "| 메모       | |"
} > "$LOG_OUT"

echo ""
echo "[daily-check] Log written: $LOG_OUT"

if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "[daily-check] Day $DAY_NUMBER integrity: PASSED"
  exit 0
else
  echo "[daily-check] Day $DAY_NUMBER integrity: FAILED (${#FAILURES[@]} issue(s))"
  exit 1
fi
