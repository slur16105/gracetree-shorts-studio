import { resolve } from 'node:path'

import { spawnPython } from './python-command.mjs'

const root = resolve(import.meta.dirname, '..')
const child = spawnPython(['-m', 'pytest', 'engine/tests'], {
  cwd: root,
  env: { ...process.env, PYTHONPATH: resolve(root, 'engine') },
  stdio: 'inherit'
})

const exitCode = await new Promise((resolveExit, reject) => {
  child.once('error', reject)
  child.once('close', resolveExit)
})

process.exitCode = exitCode ?? 1
