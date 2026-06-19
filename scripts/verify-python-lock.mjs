import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const pyproject = await readFile(resolve(root, 'engine/pyproject.toml'), 'utf8')
const lock = await readFile(resolve(root, 'engine/requirements.lock'), 'utf8')
const locked = new Set(
  lock
    .split('\n')
    .map((line) => line.trim().toLowerCase())
    .filter(Boolean)
)

const requiredPins = [...pyproject.matchAll(/"([a-zA-Z0-9_-]+)==([^"]+)"/g)].map(
  ([, name, version]) => `${name.toLowerCase().replaceAll('_', '-')}==${version}`
)

const missing = requiredPins.filter((pin) => !locked.has(pin))
if (missing.length > 0) {
  throw new Error(`engine/requirements.lock is missing pyproject pins: ${missing.join(', ')}`)
}
