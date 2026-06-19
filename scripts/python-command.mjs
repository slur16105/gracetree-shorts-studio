import { spawn, spawnSync } from 'node:child_process'

function candidates() {
  if (process.env.PYTHON) {
    return [[process.env.PYTHON, []]]
  }

  return process.platform === 'win32'
    ? [
        ['py', ['-3']],
        ['python', []]
      ]
    : [
        ['python3', []],
        ['python', []]
      ]
}

export function resolvePythonCommand() {
  for (const [command, prefixArgs] of candidates()) {
    const result = spawnSync(command, [...prefixArgs, '--version'], {
      stdio: 'ignore'
    })
    if (result.status === 0) {
      return { command, prefixArgs }
    }
  }

  throw new Error('Python 3 executable not found. Set the PYTHON environment variable.')
}

export function spawnPython(args, options) {
  const { command, prefixArgs } = resolvePythonCommand()
  return spawn(command, [...prefixArgs, ...args], options)
}
