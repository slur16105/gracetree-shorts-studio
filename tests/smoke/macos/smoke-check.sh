#!/usr/bin/env bash
# Story 2.14: Post-install smoke checks for GraceTree Shorts Studio on macOS (Apple Silicon).
#
# Checks:
#   1. App bundle exists in /Applications
#   2. Engine bundle binary exists and has +x permission
#   3. FFmpeg and FFprobe binaries exist and have +x permission
#   4. Engine responds to health_checked event (not just any JSON with "type")
#   5. FFmpeg version is readable
#   6. Resource paths survive app bundle relocation (app copied to a temp dir)
#   7. No quarantine xattr on app bundle (FAIL if quarantined, warn is not enough)
#
# Usage:
#   ./smoke-check.sh [--app-path "/Applications/GraceTree Shorts Studio.app"]
#
# Exit code: 0 = all passed, 1 = one or more failed

set -euo pipefail

APP_PATH="/Applications/GraceTree Shorts Studio.app"
if [[ "${1:-}" == "--app-path" && -n "${2:-}" ]]; then
  APP_PATH="$2"
fi

FAILURES=()

check() {
  local label="$1"
  local result="$2"
  local detail="${3:-}"
  if [[ "$result" == "pass" ]]; then
    echo "[PASS] $label${detail:+: $detail}"
  else
    echo "[FAIL] $label${detail:+: $detail}"
    FAILURES+=("$label")
  fi
}

RESOURCES="$APP_PATH/Contents/Resources"
ENGINE_DIR="$RESOURCES/engine/gracetree-engine"
ENGINE_EXE="$ENGINE_DIR/gracetree-engine"
FFMPEG_DIR="$RESOURCES/ffmpeg"
FFMPEG_EXE="$FFMPEG_DIR/ffmpeg"
FFPROBE_EXE="$FFMPEG_DIR/ffprobe"

echo "[smoke-check] App: $APP_PATH"
echo ""

# 1. App bundle
[[ -d "$APP_PATH" ]] && check "App bundle exists" pass || check "App bundle exists" fail "$APP_PATH"

# 2. Engine binary
[[ -d "$ENGINE_DIR" ]] && check "Engine directory exists" pass || check "Engine directory exists" fail "$ENGINE_DIR"
[[ -f "$ENGINE_EXE" ]] && check "Engine binary exists" pass || check "Engine binary exists" fail "$ENGINE_EXE"
[[ -x "$ENGINE_EXE" ]] && check "Engine binary is executable (+x)" pass || check "Engine binary is executable (+x)" fail "$ENGINE_EXE"

# 3. FFmpeg binaries
[[ -f "$FFMPEG_EXE" ]]  && check "FFmpeg binary exists"   pass || check "FFmpeg binary exists"   fail "$FFMPEG_EXE"
[[ -x "$FFMPEG_EXE" ]]  && check "FFmpeg is executable"   pass || check "FFmpeg is executable"   fail "$FFMPEG_EXE"
[[ -f "$FFPROBE_EXE" ]] && check "FFprobe binary exists"  pass || check "FFprobe binary exists"  fail "$FFPROBE_EXE"
[[ -x "$FFPROBE_EXE" ]] && check "FFprobe is executable"  pass || check "FFprobe is executable"  fail "$FFPROBE_EXE"

# 4. Engine health check — must receive a 'health_checked' type event, not just any JSON
if [[ -x "$ENGINE_EXE" ]]; then
  HEALTH_PAYLOAD='{"protocolVersion":1,"type":"check_health","jobId":"smoke-mac-001","timestamp":"2026-06-26T00:00:00.000Z","payload":{}}'
  ENGINE_STDERR=$(mktemp)
  ENGINE_OUT=$(echo "$HEALTH_PAYLOAD" | "$ENGINE_EXE" 2>"$ENGINE_STDERR" || true)
  ENGINE_ERR=$(cat "$ENGINE_STDERR"); rm -f "$ENGINE_STDERR"
  if echo "$ENGINE_OUT" | grep -q '"type":"health_checked"'; then
    check "Engine health check responds (health_checked event)" pass
  else
    DIAG="stdout=$(echo "$ENGINE_OUT" | head -1)"
    [[ -n "$ENGINE_ERR" ]] && DIAG="$DIAG stderr=$(echo "$ENGINE_ERR" | head -1)"
    check "Engine health check responds (health_checked event)" fail "$DIAG"
  fi
else
  FAILURES+=("Engine health check (skipped — binary not executable)")
fi

# 5. FFmpeg version
if [[ -x "$FFMPEG_EXE" ]]; then
  FF_VER=$("$FFMPEG_EXE" -version 2>&1 | head -1 || true)
  if echo "$FF_VER" | grep -q "ffmpeg version"; then
    check "FFmpeg version readable" pass
  else
    check "FFmpeg version readable" fail "$FF_VER"
  fi
else
  FAILURES+=("FFmpeg version (skipped — binary not executable)")
fi

# 6. Resource resolution after app relocation
# Use $$ (PID) for uniqueness — avoids second-granularity timestamp collision in parallel runs
TEMP_APP="/private/tmp/gracetree-smoke-$$.app"
if [[ -d "$APP_PATH" ]]; then
  # Run cp without -e so cp failure doesn't abort before the fail() record
  set +e
  cp -R "$APP_PATH" "$TEMP_APP" 2>/tmp/gracetree-cp-err-$$.txt
  CP_STATUS=$?
  set -e
  if [[ $CP_STATUS -ne 0 ]]; then
    check "Engine accessible after app relocation" fail "cp -R failed: $(cat /tmp/gracetree-cp-err-$$.txt)"
    rm -f "/tmp/gracetree-cp-err-$$.txt"
  else
    rm -f "/tmp/gracetree-cp-err-$$.txt"
    RELOCATED_ENGINE="$TEMP_APP/Contents/Resources/engine/gracetree-engine/gracetree-engine"
    RELOCATED_FFMPEG="$TEMP_APP/Contents/Resources/ffmpeg/ffmpeg"
    RELOCATED_FFPROBE="$TEMP_APP/Contents/Resources/ffmpeg/ffprobe"
    [[ -x "$RELOCATED_ENGINE"  ]] && check "Engine +x after app relocation" pass \
                                  || check "Engine +x after app relocation" fail "$RELOCATED_ENGINE"
    [[ -x "$RELOCATED_FFMPEG"  ]] && check "FFmpeg +x after app relocation"  pass \
                                  || check "FFmpeg +x after app relocation"  fail "$RELOCATED_FFMPEG"
    [[ -x "$RELOCATED_FFPROBE" ]] && check "FFprobe +x after app relocation" pass \
                                  || check "FFprobe +x after app relocation" fail "$RELOCATED_FFPROBE"
    rm -rf "$TEMP_APP"
  fi
else
  FAILURES+=("App relocation check (skipped — app bundle missing)")
fi

# 7. Quarantine xattr check — FAIL if quarantined (Gatekeeper would block execution)
if command -v xattr &>/dev/null; then
  QUARANTINE=$(xattr -l "$APP_PATH" 2>/dev/null | grep "com.apple.quarantine" || true)
  if [[ -z "$QUARANTINE" ]]; then
    check "No quarantine attribute on app bundle" pass
  else
    check "No quarantine attribute on app bundle" fail \
      "quarantine is set — remove with: xattr -dr com.apple.quarantine \"$APP_PATH\""
  fi
else
  FAILURES+=("Quarantine check (skipped — xattr not available)")
fi

echo ""
if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "[smoke-check] All checks PASSED"
  exit 0
else
  echo "[smoke-check] FAILED (${#FAILURES[@]} check(s)):"
  for f in "${FAILURES[@]}"; do
    echo "  - $f"
  done
  exit 1
fi
