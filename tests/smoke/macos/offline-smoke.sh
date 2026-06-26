#!/usr/bin/env bash
# Story 2.15: Offline full-flow smoke test for GraceTree Shorts Studio on macOS (Apple Silicon).
#
# Prerequisites:
#   - App installed via install.sh to /Applications
#   - Network disabled, or test with --skip-network-check (CI cannot easily block the network)
#   - No system Python or FFmpeg on PATH (verify via PATH probe)
#     CI runners have Python installed; pass --skip-path-check to allow it.
#
# Checks:
#   1. PATH isolation (system Python/FFmpeg absent from PATH)
#   2. Network isolation probe (TCP to 8.8.8.8:53)
#   3. Engine health check (bundled binary, health_checked event, with timeout)
#   4. Bundled FFmpeg and FFprobe versions readable
#   5. Emit pass/fail report artifact to /tmp/
#
# Usage:
#   ./offline-smoke.sh [--app-path "/Applications/GraceTree Shorts Studio.app"]
#                      [--skip-network-check]
#                      [--skip-path-check]
#
# Exit code: 0 = all passed, 1 = one or more failed

set -euo pipefail

APP_PATH="/Applications/GraceTree Shorts Studio.app"
SKIP_NETWORK=0
SKIP_PATH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-path)           APP_PATH="$2"; shift 2 ;;
    --skip-network-check) SKIP_NETWORK=1; shift ;;
    --skip-path-check)    SKIP_PATH=1;    shift ;;
    *) shift ;;
  esac
done

FAILURES=()
REPORT=()

pass() {
  local label="$1" detail="${2:-}"
  local msg="[PASS] $label${detail:+: $detail}"
  REPORT+=("$msg")
  echo "$msg"
}

fail() {
  local label="$1" detail="${2:-}"
  local msg="[FAIL] $label${detail:+: $detail}"
  REPORT+=("$msg")
  echo "$msg"
  FAILURES+=("$label")
}

warn() { echo "[WARN] $1"; }

RESOURCES="$APP_PATH/Contents/Resources"
ENGINE_EXE="$RESOURCES/engine/gracetree-engine/gracetree-engine"
FFMPEG_EXE="$RESOURCES/ffmpeg/ffmpeg"
FFPROBE_EXE="$RESOURCES/ffmpeg/ffprobe"

echo "[offline-smoke] GraceTree Shorts Studio — macOS Offline Smoke Test"
echo "[offline-smoke] App: $APP_PATH"
echo ""

# 1. PATH isolation — FAIL if system Python found (engine must use bundled binary)
if [[ $SKIP_PATH -eq 1 ]]; then
  warn "PATH isolation check skipped (--skip-path-check)"
else
  SYS_PYTHON=$(command -v python3 || command -v python || true)
  if [[ -z "$SYS_PYTHON" ]]; then
    pass "No system Python on PATH"
  else
    fail "System Python found on PATH" "$SYS_PYTHON — engine must not fall back to it"
  fi
  SYS_FFMPEG=$(command -v ffmpeg || true)
  if [[ -z "$SYS_FFMPEG" ]]; then
    pass "No system FFmpeg on PATH"
  else
    fail "System FFmpeg found on PATH" "$SYS_FFMPEG"
  fi
fi

# 2. Network isolation — use TCP/53 probe (DNS port, not HTTPS)
if [[ $SKIP_NETWORK -eq 1 ]]; then
  warn "Network isolation check skipped (--skip-network-check)"
else
  if nc -z -w2 8.8.8.8 53 2>/dev/null; then
    fail "Network isolation" "TCP to 8.8.8.8:53 succeeded — network is NOT blocked"
  else
    pass "Network is blocked (TCP to 8.8.8.8:53 unreachable)"
  fi
fi

# 3. Engine health check — with timeout to detect hung process
if [[ -x "$ENGINE_EXE" ]]; then
  HEALTH='{"protocolVersion":1,"type":"check_health","jobId":"offline-mac-001","timestamp":"2026-06-26T00:00:00.000Z","payload":{}}'
  STDERR_TMP=$(mktemp)
  ENGINE_OUT=$(echo "$HEALTH" | timeout 15 "$ENGINE_EXE" 2>"$STDERR_TMP" || true)
  ENGINE_ERR=$(cat "$STDERR_TMP"); rm -f "$STDERR_TMP"
  if echo "$ENGINE_OUT" | grep -q '"type":"health_checked"'; then
    pass "Engine health check (bundled binary)" "jobId: offline-mac-001"
  else
    DIAG="stdout=$(echo "$ENGINE_OUT" | head -1 | cut -c1-120)"
    [[ -n "$ENGINE_ERR" ]] && DIAG="$DIAG | stderr=$(echo "$ENGINE_ERR" | head -1 | cut -c1-120)"
    fail "Engine health check" "$DIAG"
  fi
else
  fail "Engine health check" "binary missing or not executable: $ENGINE_EXE"
fi

# 4. Bundled FFmpeg and FFprobe versions readable
for tool_path in "$FFMPEG_EXE" "$FFPROBE_EXE"; do
  tool_name=$(basename "$tool_path")
  if [[ -x "$tool_path" ]]; then
    TOOL_VER=$("$tool_path" -version 2>&1 | head -1 || true)
    if echo "$TOOL_VER" | grep -q "$tool_name version"; then
      pass "Bundled $tool_name version readable" "$TOOL_VER"
    else
      fail "Bundled $tool_name version readable" "$TOOL_VER"
    fi
  else
    fail "Bundled $tool_name" "missing or not executable: $tool_path"
  fi
done

# 5. Write report
REPORT_PATH="/tmp/gracetree-offline-smoke-report-$$.txt"
printf '%s\n' "${REPORT[@]}" > "$REPORT_PATH"
echo ""
echo "[offline-smoke] Report written to: $REPORT_PATH"

if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "[offline-smoke] All checks PASSED"
  exit 0
else
  echo "[offline-smoke] FAILED (${#FAILURES[@]} check(s)):"
  for f in "${FAILURES[@]}"; do
    echo "  - $f"
  done
  exit 1
fi
