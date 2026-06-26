#!/usr/bin/env bash
# Story 2.14: Mount a DMG and drag the app to /Applications.
#
# Usage:
#   ./install.sh <path-to-dmg>
#
# Exit code: 0 on success, 1 on failure.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path-to-dmg>" >&2
  exit 1
fi

DMG="$1"
MOUNT_DIR=""

cleanup() {
  if [[ -n "$MOUNT_DIR" ]]; then
    hdiutil detach "$MOUNT_DIR" -quiet 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ ! -f "$DMG" ]]; then
  echo "[install] DMG not found: $DMG" >&2
  exit 1
fi

echo "[install] Mounting $DMG"
# Use -plist output to get the mount path reliably — avoids awk whitespace splitting
# when the volume name contains spaces (e.g. "GraceTree Shorts Studio 1.0.0").
PLIST=$(hdiutil attach "$DMG" -nobrowse -noautoopen -plist)
MOUNT_DIR=$(echo "$PLIST" | python3 -c "
import sys, plistlib
data = plistlib.loads(sys.stdin.buffer.read())
for ent in data.get('system-entities', []):
    mp = ent.get('mount-point', '')
    if mp:
        print(mp)
        break
")

if [[ -z "$MOUNT_DIR" ]]; then
  echo "[install] Failed to determine mount point from hdiutil output" >&2
  exit 1
fi

echo "[install] Mounted at: $MOUNT_DIR"

APP=$(find "$MOUNT_DIR" -maxdepth 1 -name "*.app" -type d | head -1)
if [[ -z "$APP" ]]; then
  echo "[install] No .app found in $MOUNT_DIR" >&2
  exit 1
fi

echo "[install] Copying $(basename "$APP") to /Applications"
cp -R "$APP" /Applications/

# Explicit detach after successful copy — ignore non-zero exit (e.g. Spotlight lock)
MOUNT_DIR_SAVE="$MOUNT_DIR"
MOUNT_DIR=""  # Clear so the EXIT trap does not double-detach
hdiutil detach "$MOUNT_DIR_SAVE" -quiet 2>/dev/null || \
  echo "[install] WARN: hdiutil detach returned non-zero (Spotlight may hold the volume; safe to ignore)"

APP_DEST="/Applications/$(basename "$APP")"
if [[ ! -d "$APP_DEST" ]]; then
  echo "[install] App not found after copy: $APP_DEST" >&2
  exit 1
fi

echo "[install] OK — installed to $APP_DEST"
