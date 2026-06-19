import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

import { spawnPython } from '../../scripts/python-command.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const fixturePath = join(root, 'packages/contracts/fixtures/valid-check-health.json')
const first = JSON.parse(await readFile(fixturePath, 'utf8'))
const second = { ...first, jobId: 'health-check-2' }

const child = spawnPython(['-m', 'gracetree_engine'], {
  cwd: root,
  env: { ...process.env, PYTHONPATH: join(root, 'engine') },
  stdio: ['pipe', 'pipe', 'pipe']
})

let stdout = ''
let stderr = ''
child.stdout.setEncoding('utf8')
child.stderr.setEncoding('utf8')
child.stdout.on('data', (chunk) => {
  stdout += chunk
})
child.stderr.on('data', (chunk) => {
  stderr += chunk
})

child.stdin.write(`${JSON.stringify(first)}\n`)
child.stdin.write(`${JSON.stringify(second)}\n`)
child.stdin.end()

const exitCode = await new Promise((resolveExit, reject) => {
  const timeout = setTimeout(() => {
    child.kill('SIGKILL')
    reject(new Error(`engine timed out; stdout=${stdout}; stderr=${stderr}`))
  }, 5000)

  child.once('error', (error) => {
    clearTimeout(timeout)
    reject(error)
  })
  child.once('close', (code) => {
    clearTimeout(timeout)
    resolveExit(code)
  })
})

if (exitCode !== 0) {
  throw new Error(`engine exited with ${exitCode}: ${stderr}`)
}
if (stderr !== '') {
  throw new Error(`engine wrote diagnostics for valid input: ${stderr}`)
}

const events = stdout.trim().split('\n').map(JSON.parse)
if (events.length !== 2 || events[0].jobId !== first.jobId || events[1].jobId !== second.jobId) {
  throw new Error(`unexpected engine events: ${stdout}`)
}

const eventSchema = JSON.parse(
  await readFile(join(root, 'packages/contracts/schemas/engine-event.schema.json'), 'utf8')
)
for (const event of events) {
  for (const key of eventSchema.required) {
    if (!(key in event)) {
      throw new Error(`event is missing ${key}: ${JSON.stringify(event)}`)
    }
  }
  if (
    event.protocolVersion !== 1 ||
    event.type !== 'health_checked' ||
    event.payload?.status !== 'ok' ||
    !event.timestamp.endsWith('Z')
  ) {
    throw new Error(`event violates the shared contract: ${JSON.stringify(event)}`)
  }
}

const invalid = JSON.parse(
  await readFile(
    join(root, 'packages/contracts/fixtures/invalid-command-bad-timestamp.json'),
    'utf8'
  )
)
const invalidChild = spawnPython(['-m', 'gracetree_engine'], {
  cwd: root,
  env: { ...process.env, PYTHONPATH: join(root, 'engine') },
  stdio: ['pipe', 'pipe', 'pipe']
})
let invalidStdout = ''
let invalidStderr = ''
invalidChild.stdout.setEncoding('utf8')
invalidChild.stderr.setEncoding('utf8')
invalidChild.stdout.on('data', (chunk) => {
  invalidStdout += chunk
})
invalidChild.stderr.on('data', (chunk) => {
  invalidStderr += chunk
})
invalidChild.stdin.end(`${JSON.stringify(invalid)}\n`)

const invalidExitCode = await new Promise((resolveExit, reject) => {
  const timeout = setTimeout(() => {
    invalidChild.kill('SIGKILL')
    reject(new Error('invalid-input engine process timed out'))
  }, 5000)
  invalidChild.once('error', (error) => {
    clearTimeout(timeout)
    reject(error)
  })
  invalidChild.once('close', (code) => {
    clearTimeout(timeout)
    resolveExit(code)
  })
})

if (invalidExitCode === 0 || invalidStdout !== '' || !invalidStderr.includes('INVALID_COMMAND')) {
  throw new Error(
    `schema-invalid command was not rejected: code=${invalidExitCode}, stdout=${invalidStdout}, stderr=${invalidStderr}`
  )
}
