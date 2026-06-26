#!/usr/bin/env bash
# Story 2.15: Offline full-flow smoke test for GraceTree Shorts Studio on macOS (Apple Silicon).
#
# Prerequisites:
#   - App installed via install.sh to /Applications
#   - Network disabled (Wi-Fi off + Ethernet unplugged) or pfctl firewall blocking outbound
#   - No system Python or FFmpeg on PATH (or verify via PATH probe)
#
# Checks:
#   1. Verify no system Python/FFmpeg on PATH
#   2. Optional network isolation probe
#   3. Engine health check (bundled binary, stdin JSON)
#   4. FFprobe with bundled binary (sample file if provided)
#   5. Emit pass/fail report artifact to /tmp/
#
# Usage:
#   ./offline-smoke.sh [--app-path "/Applications/GraceTree Shorts Studio.app"]
#                      [--sample-file /path/to/sample.mp4]
#                      [--skip-network-check]
#
# Exit code: 0 = all passed, 1 = one or more failed

set -uo pipefail

APP_PATH="/Applications/GraceTree Shorts Studio.app"
SAMPLE_FILE=""
SKIP_NETWORK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-path)       APP_PATH="$2"; shift 2 ;;
    --sample-file)    SAMPLE_FILE="$2"; shift 2 ;;
    --skip-network-check) SKIP_NETWORK=1; shift ;;
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

RESOURCES="$APP_PATH/Contents/Resources"
ENGINE_EXE="$RESOURCES/engine/gracetree-engine/gracetree-engine"
FFMPEG_EXE="$RESOURCES/ffmpeg/ffmpeg"
FFPROBE_EXE="$RESOURCES/ffmpeg/ffprobe"

echo "[offline-smoke] GraceTree Shorts Studio — macOS Offline Smoke Test"
echo "[offline-smoke] App: $APP_PATH"
echo ""

# 1. No system Python/FFmpeg on PATH
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  pass "No system Python on PATH"
else
  echo "[WARN] System Python found on PATH — engine must use bundled binary only"
fi

if ! command -v ffmpeg &>/dev/null; then
  pass "No system FFmpeg on PATH"
else
  echo "[WARN] System FFmpeg found on PATH — smoke test uses bundled FFmpeg explicitly"
fi

# 2. Network isolation check (optional)
if [[ $SKIP_NETWORK -eq 0 ]]; then
  if ! curl --max-time 2 --silent --head "https://8.8.8.8" &>/dev/null; then
    pass "Network is blocked (HTTPS to 8.8.8.8 unreachable)"
  else
    echo "[WARN] Network appears reachable — true offline isolation not confirmed"
  fi
fi

# 3. Engine health check
if [[ -x "$ENGINE_EXE" ]]; then
  HEALTH='{"protocolVersion":1,"type":"check_health","jobId":"offline-mac-001","timestamp":"2026-06-26T00:00:00.000Z","payload":{}}'
  ENGINE_OUT=$(echo "$HEALTH" | "$ENGINE_EXE" 2>/dev/null || true)
  if echo "$ENGINE_OUT" | grep -q '"type":"health_checked"'; then
    pass "Engine health check (bundled binary, no system Python)" "jobId: offline-mac-001"
  else
    fail "Engine health check" "output: $ENGINE_OUT"
  fi
else
  fail "Engine health check" "binary missing or not executable: $ENGINE_EXE"
fi

# 4. FFprobe with bundled binary
if [[ -x "$FFPROBE_EXE" ]]; then
  if [[ -n "$SAMPLE_FILE" && -f "$SAMPLE_FILE" ]]; then
    PROBE_OUT=$("$FFPROBE_EXE" -v quiet -print_format json -show_streams "$SAMPLE_FILE" 2>/dev/null || true)
    if echo "$PROBE_OUT" | grep -q '"codec_type"'; then
      pass "FFprobe on sample file (bundled binary)" "$SAMPLE_FILE"
    else
      fail "FFprobe on sample file" "no codec_type in output"
    fi
  else
    FF_VER=$("$FFPROBE_EXE" -version 2>&1 | head -1 || true)
    if echo "$FF_VER" | grep -q "ffprobe version"; then
      pass "FFprobe version readable (bundled binary)" "$FF_VER"
    else
      fail "FFprobe version readable" "$FF_VER"
    fi
  fi
else
  fail "FFprobe binary" "missing or not executable: $FFPROBE_EXE"
fi

# 5. Write report
REPORT_PATH="/tmp/gracetree-offline-smoke-report-$(date +%s).txt"
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
