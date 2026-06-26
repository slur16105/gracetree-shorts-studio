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

if [[ ! -f "$DMG" ]]; then
  echo "[install] DMG not found: $DMG" >&2
  exit 1
fi

echo "[install] Mounting $DMG"
MOUNT_DIR=$(hdiutil attach "$DMG" -nobrowse -noautoopen | awk '/Volumes/ { print $NF }')

if [[ -z "$MOUNT_DIR" ]]; then
  echo "[install] Failed to mount DMG" >&2
  exit 1
fi

APP=$(ls "$MOUNT_DIR"/*.app 2>/dev/null | head -1)
if [[ -z "$APP" ]]; then
  echo "[install] No .app found in $MOUNT_DIR" >&2
  hdiutil detach "$MOUNT_DIR" -quiet || true
  exit 1
fi

echo "[install] Copying $(basename "$APP") to /Applications"
cp -R "$APP" /Applications/

hdiutil detach "$MOUNT_DIR" -quiet

APP_DEST="/Applications/$(basename "$APP")"
if [[ ! -d "$APP_DEST" ]]; then
  echo "[install] App not found after copy: $APP_DEST" >&2
  exit 1
fi

echo "[install] OK — installed to $APP_DEST"
