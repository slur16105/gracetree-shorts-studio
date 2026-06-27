import type { EngineCommand, EngineEvent, StartJobCommand } from '@gracetree/contracts'
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { spawnMock } = vi.hoisted(() => ({
  spawnMock: vi.fn()
}))

vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>()
  return {
    ...actual,
    default: { ...actual, spawn: spawnMock },
    spawn: spawnMock
  }
})

import { EngineClient } from './engine-client'

interface FakeChild extends EventEmitter {
  stdin: PassThrough
  stdout: PassThrough
  stderr: PassThrough
  kill: ReturnType<typeof vi.fn>
}

function createFakeChild(): FakeChild {
  const child = new EventEmitter() as FakeChild
  child.stdin = new PassThrough()
  child.stdout = new PassThrough()
  child.stderr = new PassThrough()
  child.kill = vi.fn(() => true)
  return child
}

function command(jobId: string): EngineCommand {
  return {
    protocolVersion: 1,
    type: 'check_health',
    jobId,
    timestamp: '2026-06-20T00:00:00.000Z',
    payload: {}
  }
}

function event(jobId: string): EngineEvent {
  return {
    protocolVersion: 1,
    type: 'health_checked',
    jobId,
    timestamp: '2026-06-20T00:00:00.000Z',
    payload: { status: 'ok' }
  }
}

function registerCommand(jobId: string): EngineCommand {
  return {
    protocolVersion: 1,
    type: 'register_input_files',
    jobId,
    timestamp: '2026-06-20T00:00:00.000Z',
    payload: {
      sourcePaths: ['/source/large.mp4'],
      managedRoot: '/managed/GraceTreeData'
    }
  }
}

function replaceCommand(jobId: string): EngineCommand {
  return {
    protocolVersion: 1,
    type: 'manage_input',
    jobId,
    timestamp: '2026-06-20T00:00:00.000Z',
    payload: {
      action: 'replace',
      inputId: '22222222-2222-4222-8222-222222222222',
      sourcePath: '/source/large.mp4',
      managedRoot: '/managed/GraceTreeData'
    }
  }
}

describe('EngineClient', () => {
  beforeEach(() => {
    spawnMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('queues a duplicate pending job ID and dispatches it after the first settles', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const writes: string[] = []
    child.stdin.on('data', (chunk) => writes.push(chunk.toString()))
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const first = client.request(command('job-1'))
    const second = client.request(command('job-1'))
    await new Promise((resolve) => setImmediate(resolve))

    // The duplicate is queued, not rejected — only the first command is on the wire.
    expect(writes).toHaveLength(1)

    child.stdout.write(`${JSON.stringify(event('job-1'))}\n`)
    await expect(first).resolves.toEqual(event('job-1'))
    await new Promise((resolve) => setImmediate(resolve))

    // First settled → the queued request is now dispatched in submission order.
    expect(writes).toHaveLength(2)

    child.stdout.write(`${JSON.stringify(event('job-1'))}\n`)
    await expect(second).resolves.toEqual(event('job-1'))
    client.stop()
  })

  it('passes the bundled ffmpeg/ffprobe paths to the engine via env', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient(
      '/project',
      '/managed/GraceTreeData',
      undefined,
      '/bundle/ffmpeg',
      '/bundle/ffprobe'
    )
    const pending = client.request(command('job-1'))
    const spawnEnv = spawnMock.mock.calls[0][2].env
    expect(spawnEnv.GRACETREE_FFMPEG).toBe('/bundle/ffmpeg')
    expect(spawnEnv.GRACETREE_FFPROBE).toBe('/bundle/ffprobe')

    child.stdout.write(`${JSON.stringify(event('job-1'))}\n`)
    await expect(pending).resolves.toEqual(event('job-1'))
    client.stop()
  })

  it('terminates a timed-out engine and starts a fresh process for the next request', async () => {
    vi.useFakeTimers()
    const firstChild = createFakeChild()
    const secondChild = createFakeChild()
    spawnMock.mockReturnValueOnce(firstChild).mockReturnValueOnce(secondChild)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const timedOut = client.request(command('job-1'))
    const rejection = expect(timedOut).rejects.toThrow('timed out')

    await vi.advanceTimersByTimeAsync(5000)
    await rejection
    expect(firstChild.kill).toHaveBeenCalledOnce()

    const next = client.request(command('job-2'))
    secondChild.stdout.write(`${JSON.stringify(event('job-2'))}\n`)

    await expect(next).resolves.toEqual(event('job-2'))
    expect(spawnMock).toHaveBeenCalledTimes(2)
    client.stop()
  })

  it('allows input registration to run beyond the default five-second timeout', async () => {
    vi.useFakeTimers()
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const pending = client.request(registerCommand('11111111-1111-4111-8111-111111111111'))

    await vi.advanceTimersByTimeAsync(5_001)
    expect(child.kill).not.toHaveBeenCalled()

    child.stdout.write(
      `${JSON.stringify({
        protocolVersion: 1,
        type: 'input_files_registered',
        jobId: '11111111-1111-4111-8111-111111111111',
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: {
          inputs: [],
          results: [
            {
              originalName: 'large.mp4',
              managedPath: null,
              role: 'unclassified',
              status: 'rejected',
              errorCode: 'COPY_FAILED'
            }
          ]
        }
      })}\n`
    )

    await expect(pending).resolves.toMatchObject({ type: 'input_files_registered' })
    client.stop()
  })

  it('allows input replacement to run beyond the default five-second timeout', async () => {
    vi.useFakeTimers()
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const pending = client.request(replaceCommand('11111111-1111-4111-8111-111111111111'))

    await vi.advanceTimersByTimeAsync(5_001)
    expect(child.kill).not.toHaveBeenCalled()

    child.stdout.write(
      `${JSON.stringify({
        protocolVersion: 1,
        type: 'input_state_changed',
        jobId: '11111111-1111-4111-8111-111111111111',
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { inputs: [] }
      })}\n`
    )

    await expect(pending).resolves.toMatchObject({ type: 'input_state_changed' })
    client.stop()
  })

  it.each([
    ['invalid JSON', 'not-json'],
    ['invalid event', JSON.stringify({ type: 'unknown' })]
  ])('terminates a corrupt engine after receiving %s', async (_label, line) => {
    const corruptChild = createFakeChild()
    const replacementChild = createFakeChild()
    spawnMock.mockReturnValueOnce(corruptChild).mockReturnValueOnce(replacementChild)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const pending = client.request(command('job-1'))

    corruptChild.stdout.write(`${line}\n`)

    await expect(pending).rejects.toThrow(/invalid JSON|invalid event/)
    expect(corruptChild.kill).toHaveBeenCalledOnce()

    const next = client.request(command('job-2'))
    replacementChild.stdout.write(`${JSON.stringify(event('job-2'))}\n`)
    await expect(next).resolves.toEqual(event('job-2'))
    expect(spawnMock).toHaveBeenCalledTimes(2)
    client.stop()
  })
})

function startJobCommand(jobId: string): StartJobCommand {
  return {
    protocolVersion: 1,
    type: 'start_job',
    jobId,
    timestamp: '2026-06-25T00:00:00.000Z',
    payload: { managedRoot: '/managed/GraceTreeData', workPath: '/managed/GraceTreeData/jobs/2026-06-25' }
  }
}

const ATTEMPT_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const JOB_UUID_GEN = '11111111-2222-4333-8444-555555555501'
const JOB_UUID_FAIL = '11111111-2222-4333-8444-555555555502'
const JOB_UUID_CANCEL = '11111111-2222-4333-8444-555555555503'
const JOB_UUID_STREAM = '11111111-2222-4333-8444-555555555504'
const JOB_UUID_STOP = '11111111-2222-4333-8444-555555555505'
const JOB_UUID_TIMEOUT = '11111111-2222-4333-8444-555555555506'

function generationEvent(type: string, jobId: string, extra: Record<string, unknown> = {}): EngineEvent {
  return {
    protocolVersion: 1,
    type: type as EngineEvent['type'],
    jobId,
    timestamp: '2026-06-25T00:00:00.000Z',
    payload: { attemptId: ATTEMPT_UUID, ...extra }
  } as EngineEvent
}

describe('EngineClient.streamJob', () => {
  beforeEach(() => {
    spawnMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls onEvent for every event until job_completed and resolves', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const received: EngineEvent[] = []

    const done = client.streamJob(startJobCommand(JOB_UUID_GEN), (e) => received.push(e))

    const events = [
      generationEvent('job_accepted', JOB_UUID_GEN),
      generationEvent('stage_started', JOB_UUID_GEN, { stageId: 'final_composition', stageName: '최종 합성' }),
      generationEvent('progress', JOB_UUID_GEN, { stageId: 'final_composition', percent: 30 }),
      generationEvent('job_completed', JOB_UUID_GEN, { artifactPath: '/p/a.mp4', artifactName: 'a.mp4' })
    ]
    for (const ev of events) {
      child.stdout.write(`${JSON.stringify(ev)}\n`)
    }

    await expect(done).resolves.toBeUndefined()
    expect(received).toHaveLength(4)
    expect(received.map((e) => e.type)).toEqual([
      'job_accepted', 'stage_started', 'progress', 'job_completed'
    ])
    client.stop()
  })

  it('resolves on job_failed', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const done = client.streamJob(startJobCommand(JOB_UUID_FAIL), () => {})
    child.stdout.write(
      `${JSON.stringify(generationEvent('job_accepted', JOB_UUID_FAIL))}\n`
    )
    child.stdout.write(
      `${JSON.stringify(generationEvent('job_failed', JOB_UUID_FAIL, { errorCode: 'PROCESS_FAILED', stageId: 'final_composition', recoverable: false, details: null }))}\n`
    )
    await expect(done).resolves.toBeUndefined()
    client.stop()
  })

  it('resolves on job_cancelled', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const done = client.streamJob(startJobCommand(JOB_UUID_CANCEL), () => {})
    child.stdout.write(
      `${JSON.stringify(generationEvent('job_cancelled', JOB_UUID_CANCEL))}\n`
    )
    await expect(done).resolves.toBeUndefined()
    client.stop()
  })

  it('stream and pending listeners coexist independently', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const health = client.request(command('health-1'))
    const streamReceived: string[] = []
    const gen = client.streamJob(startJobCommand(JOB_UUID_STREAM), (e) => streamReceived.push(e.type))

    child.stdout.write(`${JSON.stringify(event('health-1'))}\n`)
    await expect(health).resolves.toMatchObject({ type: 'health_checked' })

    child.stdout.write(
      `${JSON.stringify(generationEvent('job_completed', JOB_UUID_STREAM, { artifactPath: '/a.mp4', artifactName: 'a.mp4' }))}\n`
    )
    await expect(gen).resolves.toBeUndefined()
    expect(streamReceived).toEqual(['job_completed'])
    client.stop()
  })

  it('rejects all stream listeners when child process is stopped', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const gen = client.streamJob(startJobCommand(JOB_UUID_STOP), () => {})
    client.stop()
    await expect(gen).rejects.toThrow('stopped')
  })

  it('rejects with timeout after GENERATION_TIMEOUT_MS', async () => {
    vi.useFakeTimers()
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')

    const gen = client.streamJob(startJobCommand(JOB_UUID_TIMEOUT), () => {})
    const rejection = expect(gen).rejects.toThrow('timed out')
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000 + 1)
    await rejection
    client.stop()
  })
})
