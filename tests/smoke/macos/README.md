# macOS Smoke Tests

These scripts verify that the installed GraceTree Shorts Studio package works correctly on a clean Apple Silicon (arm64) Mac.

## Prerequisites

- Apple Silicon Mac (M1/M2/M3) — clean install, no Python or FFmpeg on PATH
- The DMG installer built by `node scripts/build-desktop.mjs --platform darwin --arch arm64`

## Running

```bash
# 1. Mount and install the app
./install.sh /path/to/GraceTree-Shorts-Studio-*-macos-arm64.dmg

# 2. Run all smoke checks
./smoke-check.sh
```

Scripts exit with code 0 on success, non-zero on failure.

## Notes

- The app is installed to `/Applications/GraceTree Shorts Studio.app` by default.
- Gatekeeper quarantine is expected on a freshly downloaded DMG; the smoke test
  verifies the structure without launching the GUI. Full notarization is covered by
  Story 2.17.
- Executable bits (+x) on the engine and FFmpeg binaries are verified explicitly
  because macOS will refuse to exec files without them.
