/**
 * Story 2.13: Build the GraceTree Shorts Studio Electron installer.
 *
 * Usage:
 *   node scripts/build-desktop.mjs [--platform <win32|darwin|linux>] [--arch <x64|arm64>]
 *
 * Steps:
 *   1. Ensure engine bundle exists (engine/dist/gracetree-engine/)
 *   2. Run `electron-vite build` to compile the renderer/main/preload
 *   3. Run `electron-builder` to create the platform installer
 *
 * The resulting installer is placed at apps/desktop/dist/installer/.
 *
 * Requirements:
 *   - pnpm install (devDeps include electron-builder)
 *   - Engine bundle pre-built by scripts/build-engine.mjs
 *   - FFmpeg binaries at resources/ffmpeg/{win32,darwin,linux}/
 */

import { access, constants as fsConstants } from 'node:fs/promises'
import { resolve, join } from 'node:path'
import { spawnSync } from 'node:child_process'

const ROOT = resolve(import.meta.dirname, '..')
const ENGINE_DIST = join(ROOT, 'dist', 'gracetree-engine')
const DESKTOP = join(ROOT, 'apps', 'desktop')

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, { stdio: 'inherit', cwd: ROOT, ...opts })
  if (result.error || result.status !== 0) {
    const detail = result.error ? `: ${result.error.message}` : ''
    process.stderr.write(`\n[build-desktop] FAILED: ${cmd} ${args.join(' ')}${detail}\n`)
    process.exit(result.status ?? 1)
  }
}

async function ensureEngineBundle() {
  try {
    await access(ENGINE_DIST, fsConstants.F_OK)
    console.log('[build-desktop] Engine bundle found at', ENGINE_DIST)
  } catch {
    console.error('[build-desktop] Engine bundle not found:', ENGINE_DIST)
    console.error('[build-desktop] Run `node scripts/build-engine.mjs` first.')
    process.exit(1)
  }
}

function parsePlatformArgs() {
  const args = process.argv.slice(2)
  const platIdx = args.indexOf('--platform')
  const archIdx = args.indexOf('--arch')
  const platform = platIdx !== -1 ? args[platIdx + 1] : process.platform
  const arch = archIdx !== -1 ? args[archIdx + 1] : process.arch
  return { platform, arch }
}

async function main() {
  const { platform, arch } = parsePlatformArgs()
  console.log(`[build-desktop] Building for ${platform}/${arch}`)

  await ensureEngineBundle()

  // Step 1: Compile Electron sources
  console.log('\n[build-desktop] Step 1: electron-vite build')
  run('pnpm', ['build'], { cwd: DESKTOP })

  // Step 2: Package with electron-builder
  console.log('\n[build-desktop] Step 2: electron-builder')
  const platformFlag = platform === 'win32' ? '--win' : platform === 'darwin' ? '--mac' : '--linux'
  const archFlag = arch === 'arm64' ? '--arm64' : '--x64'
  run('pnpm', ['exec', 'electron-builder', platformFlag, archFlag, '--config', 'electron-builder.yml'], {
    cwd: DESKTOP,
    env: { ...process.env, CSC_IDENTITY_AUTO_DISCOVERY: 'false' },
  })

  console.log('\n[build-desktop] Done. Installer at apps/desktop/dist/installer/')
}

main().catch((err) => {
  console.error('[build-desktop]', err)
  process.exit(1)
})
