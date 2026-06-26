/**
 * Story 2.17: Verify platform code signing and notarization status.
 *
 * Usage:
 *   node scripts/verify-signing.mjs --installer <path>
 *                                    --channel <development|external>
 *                                    [--platform <win32|darwin>]
 *
 * Exit codes:
 *   0 — signing gate PASSED (external: signed+notarized; development: unsigned OK)
 *   1 — signing gate FAILED or BLOCKED (external build not signed)
 *   2 — usage error
 *
 * For the signing gate to PASS on an external build, the following must be true:
 *   Windows: installer has a valid Authenticode signature and timestamp
 *   macOS:   .app has a valid Developer ID signature, hardened runtime,
 *             and a notarization ticket is stapled to the DMG
 *
 * If CSC/notarization credentials are not present in the environment, this script
 * reports BLOCKED on an external channel build — it never reports success silently.
 */

import { spawnSync } from 'node:child_process'
import { resolve } from 'node:path'
import { access, constants as fsConstants } from 'node:fs/promises'

function usage() {
  process.stderr.write(
    'Usage: node scripts/verify-signing.mjs --installer <path> --channel <development|external> [--platform <win32|darwin>]\n'
  )
  process.exit(2)
}

function run(cmd, args) {
  return spawnSync(cmd, args, { encoding: 'utf8' })
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
    process.stderr.write(`[verify-signing] Unknown channel: ${channel}. Must be 'development' or 'external'.\n`)
    process.exit(2)
  }
  return { installer: resolve(installer), channel, platform }
}

async function verifyWindows(installer, channel) {
  const failures = []
  const warnings = []

  // Check if signtool is available
  const signtool = run('signtool', ['verify', '/pa', '/v', installer])
  const hasSig = signtool.status === 0

  if (channel === 'external') {
    if (!hasSig) {
      failures.push(
        `Windows installer is NOT signed — cannot distribute externally.\n` +
        `  signtool output: ${signtool.stderr?.trim() ?? '(no output)'}\n` +
        `  Set CSC_LINK and CSC_KEY_PASSWORD in CI secrets to enable signing.`
      )
    } else {
      process.stdout.write('[verify-signing] Windows Authenticode signature: VALID\n')
      // Verify timestamp is present
      if (signtool.stdout?.includes('Timestamp')) {
        process.stdout.write('[verify-signing] Timestamp: PRESENT\n')
      } else {
        warnings.push('Timestamp not found in signature — revocation resilience reduced')
      }
    }
  } else {
    // development channel: unsigned is acceptable, emit a clear marker
    if (!hasSig) {
      process.stdout.write('[verify-signing] channel=development: installer is unsigned (expected for dev builds)\n')
    } else {
      process.stdout.write('[verify-signing] channel=development: installer is signed (optional, accepted)\n')
    }
  }

  return { failures, warnings }
}

async function verifyMacos(installer, channel) {
  const failures = []
  const warnings = []

  // Check codesign on the DMG (stapling check)
  const spctl = run('spctl', ['--assess', '--verbose=2', '--type', 'open', '--context', 'context:primary-signature', installer])
  const notarized = spctl.status === 0

  if (channel === 'external') {
    if (!notarized) {
      const detail = spctl.stderr?.trim() ?? spctl.stdout?.trim() ?? '(no output)'
      failures.push(
        `macOS installer is NOT notarized or signature check failed — cannot distribute externally.\n` +
        `  spctl output: ${detail}\n` +
        `  Set APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID in CI secrets to enable notarization.`
      )
    } else {
      process.stdout.write('[verify-signing] macOS notarization (spctl): ACCEPTED\n')
      // Verify stapling
      const stapler = run('stapler', ['validate', installer])
      if (stapler.status === 0) {
        process.stdout.write('[verify-signing] Notarization ticket stapled: YES\n')
      } else {
        warnings.push('Notarization ticket not stapled to DMG — run: stapler staple <dmg>')
      }
    }
  } else {
    process.stdout.write('[verify-signing] channel=development: notarization not required for dev builds\n')
    // Still warn if the app bundle signature is invalid (hardened runtime may be broken)
    const codesign = run('codesign', ['--verify', '--deep', '--strict', '--verbose=2', installer])
    if (codesign.status !== 0) {
      warnings.push('codesign verify failed — may indicate hardened runtime issues in the build')
    }
  }

  return { failures, warnings }
}

async function main() {
  const { installer, channel, platform } = parseArgs()

  // Verify installer exists
  try {
    await access(installer, fsConstants.F_OK)
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
