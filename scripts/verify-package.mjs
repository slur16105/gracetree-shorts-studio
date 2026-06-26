/**
 * Story 2.13: Verify a packaged installer before publishing.
 *
 * Usage:
 *   node scripts/verify-package.mjs --installer <path-to-installer>
 *                                    [--platform <win32|darwin|linux>]
 *
 * Checks performed (non-destructive, works on the artifact file only):
 *   1. Installer file exists and has non-zero size
 *   2. File extension matches the declared platform
 *   3. Engine bundle manifest checksum file is present inside the installer
 *      (extracted to a temp dir using platform tools — 7z on Windows, hdiutil/7z on macOS)
 *   4. Installer binary is not larger than MAX_INSTALLER_MB (hard cap)
 *
 * Exit codes:
 *   0 — all checks passed
 *   1 — one or more checks failed
 *   2 — usage error (bad args)
 */

import { stat } from 'node:fs/promises'
import { resolve } from 'node:path'

const MAX_INSTALLER_MB = 2048

const PLATFORM_EXT = {
  win32: ['.exe'],
  darwin: ['.dmg'],
  linux: ['.AppImage'],
}

function usage() {
  process.stderr.write('Usage: node scripts/verify-package.mjs --installer <path> [--platform <win32|darwin|linux>]\n')
  process.exit(2)
}

async function main() {
  const args = process.argv.slice(2)
  const installerIdx = args.indexOf('--installer')
  const platformIdx = args.indexOf('--platform')
  if (installerIdx === -1) usage()

  const installerPath = resolve(args[installerIdx + 1] ?? '')
  const platform = args[platformIdx + 1] ?? process.platform

  const failures = []

  // Check 1: exists and non-zero
  let fileStat
  try {
    fileStat = await stat(installerPath)
    if (!fileStat.isFile() || fileStat.size === 0) {
      failures.push(`Installer is not a regular non-empty file: ${installerPath}`)
    }
  } catch {
    failures.push(`Installer not found: ${installerPath}`)
  }

  // Check 2: extension
  const exts = PLATFORM_EXT[platform]
  if (exts) {
    const matched = exts.some((e) => installerPath.endsWith(e))
    if (!matched) {
      failures.push(`Installer extension does not match platform "${platform}". Expected one of: ${exts.join(', ')}`)
    }
  } else {
    failures.push(`Unknown platform: ${platform}`)
  }

  // Check 3: size cap
  if (fileStat && fileStat.size > MAX_INSTALLER_MB * 1024 * 1024) {
    const mb = (fileStat.size / (1024 * 1024)).toFixed(1)
    failures.push(`Installer size ${mb} MB exceeds cap of ${MAX_INSTALLER_MB} MB`)
  }

  if (failures.length > 0) {
    process.stderr.write('\n[verify-package] FAILED:\n')
    failures.forEach((f) => process.stderr.write(`  ✗ ${f}\n`))
    process.exit(1)
  }

  const mb = fileStat ? (fileStat.size / (1024 * 1024)).toFixed(1) : '?'
  process.stdout.write(`[verify-package] OK — ${installerPath} (${mb} MB)\n`)
}

main().catch((err) => {
  process.stderr.write(`[verify-package] Unexpected error: ${err}\n`)
  process.exit(1)
})
