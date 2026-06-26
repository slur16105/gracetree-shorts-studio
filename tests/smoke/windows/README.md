# Windows Smoke Tests

These scripts verify that the installed GraceTree Shorts Studio package works correctly on a clean Windows x64 system.

## Prerequisites

- Windows x64 machine or VM (clean, no Python, no FFmpeg on PATH)
- The NSIS installer built by `node scripts/build-desktop.mjs --platform win32 --arch x64`

## Running

```powershell
# 1. Install the app silently
.\install.ps1 -InstallerPath "path\to\GraceTree-Shorts-Studio-*-windows-x64-setup.exe"

# 2. Run all smoke checks
.\smoke-check.ps1
```

The scripts exit with code 0 on success, non-zero on failure.
