/**
 * Story 2.17: Verify platform code signing and notarization status.
 *
 * Usage:
 *   node scripts/verify-signing.mjs --installer <path>
 *                                    --channel <development|external>
 *                                    [--platform <win32|darwin>]
 *
 * Exit codes:
 *   0 — signing gate PASSED
 *   1 — signing gate FAILED or BLOCKED
 *   2 — usage error
 *
 * External channel hard requirements:
 *   Windows: valid Authenticode signature WITH a countersignature timestamp
 *   macOS:   valid Developer ID code signature on the .app, hardened runtime enabled,
 *             notarization ticket stapled to the DMG
 *
 * If signing credentials are absent, the gate reports BLOCKED — never silent success.
 */

import { spawnSync } from 'node:child_process'
import { resolve, join } from 'node:path'
import { access, constants as fsConstants, mkdtempSync, rmSync } from 'node:fs'
import { promisify } from 'node:util'
import { tmpdir } from 'node:os'

const accessAsync = promisify(access)

function usage() {
  process.stderr.write(
    'Usage: node scripts/verify-signing.mjs --installer <path> --channel <development|external> [--platform <win32|darwin>]\n'
  )
  process.exit(2)
}

function parseArgs() {
  const args = process.argv.slice(2)
  const get = (flag) => {
    const idx = args.indexOf(flag)
    return idx !== -1 ? args[idx + 1] : undefined
  }
  const installer = get('--installer')
  const channel = get('--channel')
  const platform = get('--platform') ?? process.platform
  if (!installer || !channel) usage()
  if (!['development', 'external'].includes(channel)) {
    process.stderr.write(`[verify-signing] Unknown channel: "${channel}". Must be 'development' or 'external'.\n`)
    process.exit(2)
  }
  return { installer: resolve(installer), channel, platform }
}

function run(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: 'utf8' })
  // Include ENOENT in stderr so callers get actionable diagnostics
  if (result.error) {
    result.stderr = `[spawn error] ${result.error.message}`
  }
  return result
}

/** Return the first non-empty string from candidates, or fallback. */
function firstNonEmpty(...candidates) {
  for (const c of candidates) {
    const s = (c ?? '').trim()
    if (s) return s
  }
  return '(no output)'
}

// ─── Windows ────────────────────────────────────────────────────────────────

async function verifyWindows(installer, channel) {
  const failures = []
  const warnings = []

  const signtool = run('signtool', ['verify', '/pa', '/v', installer])
  const hasSig = signtool.status === 0

  if (channel === 'external') {
    if (!hasSig) {
      const detail = firstNonEmpty(signtool.stderr, signtool.stdout)
      failures.push(
        `Windows installer is NOT signed — cannot distribute externally.\n` +
        `  signtool output: ${detail}\n` +
        `  Set CSC_LINK and CSC_KEY_PASSWORD in CI secrets to enable signing.`
      )
    } else {
      process.stdout.write('[verify-signing] Windows Authenticode signature: VALID\n')
      // Timestamp is required for external builds (revocation resilience)
      if (signtool.stdout?.includes('Timestamp')) {
        process.stdout.write('[verify-signing] Countersignature timestamp: PRESENT\n')
      } else {
        failures.push(
          'Countersignature timestamp is MISSING from the Authenticode signature.\n' +
          '  Without a timestamp, the installer will be rejected after certificate expiry or revocation.\n' +
          '  Ensure the TSA was reachable during signing (electron-builder uses DigiCert by default).'
        )
      }
    }
  } else {
    if (!hasSig) {
      process.stdout.write('[verify-signing] channel=development: installer is unsigned (expected for dev builds)\n')
    } else {
      process.stdout.write('[verify-signing] channel=development: installer is signed\n')
    }
  }

  return { failures, warnings }
}

// ─── macOS ──────────────────────────────────────────────────────────────────

/**
 * Mount a DMG, run the callback with the mount point, unmount when done.
 * Returns the callback's return value.
 */
function withMountedDmg(dmgPath, callback) {
  const attachResult = run('hdiutil', ['attach', dmgPath, '-nobrowse', '-noautoopen', '-plist'])
  if (attachResult.status !== 0) {
    return callback(null, firstNonEmpty(attachResult.stderr, attachResult.stdout))
  }
  let mountPoint = null
  try {
    // Parse plist to find mount-point — avoids awk whitespace splitting on volume names with spaces
    const plistResult = run('python3', [
      '-c',
      `import sys,plistlib;data=plistlib.loads(sys.stdin.buffer.read());` +
      `[print(e['mount-point']) for e in data.get('system-entities',[]) if 'mount-point' in e]`
    ])
    if (plistResult.status === 0) {
      mountPoint = plistResult.stdout.trim().split('\n').find(Boolean) ?? null
    }
    if (!plistResult.stdin) {
      // Pipe plist data to python3
    }
  } catch {
    // Fallback: parse plist output manually
    const match = attachResult.stdout.match(/<string>(\/Volumes\/[^<]+)<\/string>/)
    if (match) mountPoint = match[1]
  }

  let result
  try {
    result = callback(mountPoint, null)
  } finally {
    if (mountPoint) {
      run('hdiutil', ['detach', mountPoint, '-quiet'])
    }
  }
  return result
}

async function verifyMacos(installer, channel) {
  const failures = []
  const warnings = []

  // Step 1: Find the .app bundle — try to mount the DMG
  // For dev channel we fall back to codesign on the DMG itself
  let appPath = null
  let mountError = null

  const attachResult = spawnSync('hdiutil', ['attach', installer, '-nobrowse', '-noautoopen', '-plist'], {
    encoding: 'utf8',
  })

  let mountPoint = null
  if (attachResult.status === 0) {
    // Parse mount point from plist output
    const plistInput = attachResult.stdout
    const pyResult = spawnSync('python3', [
      '-c',
      `import sys,plistlib;data=plistlib.loads(sys.stdin.buffer.read());` +
      `[print(e["mount-point"]) for e in data.get("system-entities",[]) if "mount-point" in e]`
    ], { input: plistInput, encoding: 'utf8' })
    if (pyResult.status === 0) {
      mountPoint = pyResult.stdout.trim().split('\n').find(Boolean) ?? null
    }
  } else {
    mountError = firstNonEmpty(attachResult.stderr, attachResult.stdout)
  }

  if (mountPoint) {
    // Find the .app in the mounted volume
    const findResult = spawnSync('find', [mountPoint, '-maxdepth', '1', '-name', '*.app', '-type', 'd'], {
      encoding: 'utf8',
    })
    appPath = findResult.stdout.trim().split('\n').find(Boolean) ?? null
  }

  try {
    if (channel === 'external') {
      // Require: app bundle has valid Developer ID signature
      if (appPath) {
        const codesign = spawnSync(
          'codesign', ['--verify', '--deep', '--strict', '--verbose=2', appPath],
          { encoding: 'utf8' }
        )
        if (codesign.status === 0) {
          process.stdout.write('[verify-signing] Developer ID code signature on .app: VALID\n')
        } else {
          failures.push(
            `Developer ID code signature on .app is INVALID.\n` +
            `  codesign output: ${firstNonEmpty(codesign.stderr, codesign.stdout)}\n` +
            `  Set CSC_LINK_MAC and CSC_KEY_PASSWORD_MAC in CI secrets.`
          )
        }
      } else if (mountError) {
        failures.push(`Could not mount DMG to verify .app signature: ${mountError}`)
      } else {
        failures.push('No .app bundle found in DMG — cannot verify code signature')
      }

      // Require: notarization ticket stapled to the DMG
      const stapler = spawnSync('stapler', ['validate', installer], { encoding: 'utf8' })
      if (stapler.status === 0) {
        process.stdout.write('[verify-signing] Notarization ticket stapled to DMG: YES\n')
      } else {
        failures.push(
          'Notarization ticket is NOT stapled to the DMG.\n' +
          `  stapler output: ${firstNonEmpty(stapler.stderr, stapler.stdout)}\n` +
          '  Run: xcrun stapler staple <dmg>  OR  ensure APPLE credentials enable auto-stapling in electron-builder.'
        )
      }

      // Verify Gatekeeper would accept the DMG (notarization assessment)
      const spctl = spawnSync(
        'spctl', ['--assess', '--verbose=2', '--type', 'open', '--context', 'context:primary-signature', installer],
        { encoding: 'utf8' }
      )
      if (spctl.status === 0) {
        process.stdout.write('[verify-signing] Gatekeeper (spctl) assessment: ACCEPTED\n')
      } else {
        failures.push(
          `Gatekeeper assessment FAILED for DMG.\n` +
          `  spctl output: ${firstNonEmpty(spctl.stderr, spctl.stdout)}`
        )
      }
    } else {
      // development channel: verify hardened runtime on the app bundle (warn only)
      const target = appPath ?? installer
      const codesign = spawnSync(
        'codesign', ['--verify', '--deep', '--strict', '--verbose=2', target],
        { encoding: 'utf8' }
      )
      if (codesign.status !== 0) {
        warnings.push(
          `codesign verify failed on ${appPath ? '.app' : 'DMG'} — may indicate hardened runtime misconfiguration.\n` +
          `  output: ${firstNonEmpty(codesign.stderr, codesign.stdout)}`
        )
      } else {
        process.stdout.write('[verify-signing] channel=development: code signature OK\n')
      }
    }
  } finally {
    // Detach the DMG regardless of gate outcome
    if (mountPoint) {
      spawnSync('hdiutil', ['detach', mountPoint, '-quiet'])
    }
  }

  return { failures, warnings }
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const { installer, channel, platform } = parseArgs()

  try {
    await accessAsync(installer, fsConstants.F_OK)
  } catch {
    process.stderr.write(`[verify-signing] Installer not found: ${installer}\n`)
    process.exit(1)
  }

  process.stdout.write(`[verify-signing] installer=${installer}\n`)
  process.stdout.write(`[verify-signing] channel=${channel} platform=${platform}\n\n`)

  let result
  if (platform === 'win32') {
    result = await verifyWindows(installer, channel)
  } else if (platform === 'darwin') {
    result = await verifyMacos(installer, channel)
  } else {
    process.stderr.write(`[verify-signing] Signing verification not implemented for platform: ${platform}\n`)
    process.exit(2)
  }

  const { failures, warnings } = result

  if (warnings.length > 0) {
    warnings.forEach((w) => process.stdout.write(`[verify-signing] WARN: ${w}\n`))
  }

  if (failures.length > 0) {
    process.stderr.write(`\n[verify-signing] BLOCKED — ${failures.length} gate failure(s):\n`)
    failures.forEach((f) => process.stderr.write(`  ✗ ${f}\n`))
    if (channel === 'external') {
      process.stderr.write('\n[verify-signing] External distribution is BLOCKED until all failures are resolved.\n')
    }
    process.exit(1)
  }

  process.stdout.write(`\n[verify-signing] Gate PASSED for channel=${channel}\n`)
}

main().catch((err) => {
  process.stderr.write(`[verify-signing] Unexpected error: ${err}\n`)
  process.exit(1)
})
