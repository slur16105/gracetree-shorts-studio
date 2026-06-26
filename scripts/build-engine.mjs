/**
 * Story 2.12: Build the GraceTree Python engine as a PyInstaller onedir bundle.
 *
 * Usage:
 *   node scripts/build-engine.mjs [--platform <darwin|win32|linux>]
 *
 * Steps:
 *   1. Run PyInstaller with engine/packaging/gracetree-engine.spec
 *   2. Compute SHA-256 checksums of key bundle files
 *   3. Write engine/packaging/bundle-manifest.json with version, checksums, licenses
 *
 * The resulting bundle is at:
 *   dist/gracetree-engine/          (macOS / Linux)
 *   dist\gracetree-engine\          (Windows)
 *
 * Requirements:
 *   - PyInstaller installed in the active Python env:
 *       pip install pyinstaller
 *   - All engine dependencies installed:
 *       pip install -r engine/requirements.lock
 */

import { createReadStream } from 'node:fs'
import { createHash } from 'node:crypto'
import { readFile, writeFile, readdir } from 'node:fs/promises'
import { resolve, join } from 'node:path'
import { spawnSync } from 'node:child_process'

import { resolvePythonCommand } from './python-command.mjs'

const ROOT = resolve(import.meta.dirname, '..')
const SPEC = join(ROOT, 'engine', 'packaging', 'gracetree-engine.spec')
const DIST = join(ROOT, 'dist', 'gracetree-engine')
const MANIFEST_OUT = join(ROOT, 'engine', 'packaging', 'bundle-manifest.json')
const PYPROJECT = join(ROOT, 'engine', 'pyproject.toml')

// ── helpers ──────────────────────────────────────────────────────────────────

function die(msg) {
  console.error(`\n❌  ${msg}`)
  process.exit(1)
}

function sha256(filePath) {
  return new Promise((ok, fail) => {
    const hash = createHash('sha256')
    createReadStream(filePath)
      .on('data', (d) => hash.update(d))
      .on('end', () => ok(hash.digest('hex')))
      .on('error', fail)
  })
}

async function readVersion() {
  const toml = await readFile(PYPROJECT, 'utf8')
  const m = toml.match(/^version\s*=\s*"([^"]+)"/m)
  if (!m) die('Could not parse version from engine/pyproject.toml')
  return m[1]
}

async function collectFiles(dir, base = dir, results = []) {
  const entries = await readdir(dir, { withFileTypes: true })
  for (const e of entries) {
    const full = join(dir, e.name)
    if (e.isDirectory()) {
      await collectFiles(full, base, results)
    } else {
      results.push(full)
    }
  }
  return results
}

// ── main ─────────────────────────────────────────────────────────────────────

const platform = process.argv.includes('--platform')
  ? process.argv[process.argv.indexOf('--platform') + 1]
  : process.platform

console.log(`\n🔨  Building GraceTree engine for platform: ${platform}`)

// Step 1: Run PyInstaller
const { command, prefixArgs } = resolvePythonCommand()
const pyinstallerArgs = [
  ...prefixArgs,
  '-m', 'PyInstaller',
  '--clean',
  '--noconfirm',
  SPEC,
]
console.log(`\n▶  ${command} ${pyinstallerArgs.join(' ')}\n`)

const result = spawnSync(command, pyinstallerArgs, {
  cwd: ROOT,
  stdio: 'inherit',
  env: {
    ...process.env,
    PYTHONPATH: join(ROOT, 'engine'),
  },
})

if (result.status !== 0) {
  die(`PyInstaller exited with code ${result.status ?? '(signal)'}`)
}

// Step 2: Checksum all files in the bundle
console.log('\n🔍  Computing checksums…')
const allFiles = await collectFiles(DIST)
const fileEntries = []

for (const f of allFiles) {
  const rel = f.slice(DIST.length + 1).replace(/\\/g, '/')
  const digest = await sha256(f)

  // Assign a license label based on file category
  let license = 'MIT'
  if (rel.startsWith('licenses/')) license = 'see licenses/'
  if (rel.startsWith('migrations/') || rel.startsWith('contracts/')) license = 'Apache-2.0'

  fileEntries.push({ path: rel, sha256: digest, license })
  process.stdout.write('.')
}
console.log(` ${fileEntries.length} files`)

// Step 3: Write manifest
const version = await readVersion()
const manifest = {
  engine_version: version,
  platform,
  build_date: new Date().toISOString(),
  files: fileEntries,
}

await writeFile(MANIFEST_OUT, JSON.stringify(manifest, null, 2) + '\n', 'utf8')
console.log(`\n✅  Bundle manifest → ${MANIFEST_OUT}`)
console.log(`    engine_version: ${version}`)
console.log(`    platform:       ${platform}`)
console.log(`    files:          ${fileEntries.length}`)
console.log(`\n📦  Bundle output → ${DIST}`)
