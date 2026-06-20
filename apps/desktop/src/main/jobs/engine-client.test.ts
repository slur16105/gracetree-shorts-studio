import type { EngineCommand, EngineEvent } from '@gracetree/contracts'
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

describe('EngineClient', () => {
  beforeEach(() => {
    spawnMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('rejects a duplicate pending job ID without replacing the first resolver', async () => {
    const child = createFakeChild()
    spawnMock.mockReturnValue(child)
    const client = new EngineClient('/project', '/managed/GraceTreeData')
    const first = client.request(command('job-1'))

    await expect(client.request(command('job-1'))).rejects.toThrow('already pending')

    child.stdout.write(`${JSON.stringify(event('job-1'))}\n`)
    await expect(first).resolves.toEqual(event('job-1'))
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
