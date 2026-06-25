import type {
  EngineEvent,
  ManageInputCommand,
  RegisterInputFilesCommand
} from '@gracetree/contracts'
import { describe, expect, it, vi } from 'vitest'

import { createManageInputHandler, createRegisterInputFilesHandler } from './register-file-handlers'

const jobId = '11111111-1111-4111-8111-111111111111'

describe('input file batch handler', () => {
  it('normalizes one batch and preserves independent invalid results', async () => {
    const requestEngine = vi.fn(
      async (command: RegisterInputFilesCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'input_files_registered',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: {
          inputs: [],
          results: command.payload.sourcePaths.map((sourcePath) => ({
            originalName: sourcePath.split('/').at(-1) ?? sourcePath,
            managedPath: `/managed/${sourcePath.split('/').at(-1)}`,
            role: 'unclassified',
            status: 'registered',
            errorCode: null,
            input: {
              id: '22222222-2222-4222-8222-222222222222',
              jobId: command.jobId,
              role: 'unclassified',
              originalName: sourcePath.split('/').at(-1) ?? sourcePath,
              managedPath: `/managed/${sourcePath.split('/').at(-1)}`,
              status: 'ready',
              createdAt: '2026-06-20T00:00:00.000Z',
              updatedAt: '2026-06-20T00:00:00.000Z'
            }
          }))
        }
      })
    )
    const handler = createRegisterInputFilesHandler('/managed', requestEngine)

    const batch = await handler(jobId, [
      { name: 'bad.txt', sourcePath: 'relative/bad.txt' },
      { name: 'voice.mp3', sourcePath: '/source/voice.mp3' }
    ])

    expect(batch.results.map((item) => item.status)).toEqual(['rejected', 'registered'])
    expect(requestEngine).toHaveBeenCalledTimes(1)
    expect(requestEngine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'register_input_files',
        jobId,
        payload: {
          managedRoot: '/managed',
          sourcePaths: ['/source/voice.mp3']
        }
      })
    )
  })

  it('rejects invalid job IDs and empty or oversized batches', async () => {
    const handler = createRegisterInputFilesHandler('/managed', vi.fn())

    await expect(handler('invalid', [{ name: 'a', sourcePath: '/a' }])).rejects.toThrow()
    await expect(handler(jobId, [])).rejects.toThrow()
    await expect(
      handler(
        jobId,
        Array.from({ length: 101 }, (_, index) => ({
          name: `${index}.txt`,
          sourcePath: `/source/${index}.txt`
        }))
      )
    ).rejects.toThrow()
  })

  it('rejects an invalid engine event', async () => {
    const handler = createRegisterInputFilesHandler(
      '/managed',
      vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'health_checked',
          jobId,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: { status: 'ok' }
        })
      )
    )

    await expect(
      handler(jobId, [{ name: 'voice.mp3', sourcePath: '/source/voice.mp3' }])
    ).rejects.toThrow('engine response')
  })

  it('rejects an engine response with a mismatched batch size', async () => {
    const handler = createRegisterInputFilesHandler(
      '/managed',
      vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'input_files_registered',
          jobId,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: { results: [], inputs: [] }
        })
      )
    )

    await expect(
      handler(jobId, [{ name: 'voice.mp3', sourcePath: '/source/voice.mp3' }])
    ).rejects.toThrow('mismatched batch')
  })
})

describe('input management handler', () => {
  const inputId = '22222222-2222-4222-8222-222222222222'

  it('validates and forwards role, remove, and replacement actions', async () => {
    const requestEngine = vi.fn(
      async (command: ManageInputCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'input_state_changed',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { inputs: [] }
      })
    )
    const manage = createManageInputHandler('/managed', requestEngine)

    await manage(jobId, { action: 'assign_role', inputId, role: 'voice' })
    await manage(jobId, { action: 'remove', inputId })
    await manage(jobId, { action: 'replace', inputId, sourcePath: '/source/voice.mp3' })

    expect(requestEngine).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        type: 'manage_input',
        payload: {
          action: 'assign_role',
          inputId,
          role: 'voice',
          managedRoot: '/managed'
        }
      })
    )
    expect(requestEngine).toHaveBeenNthCalledWith(
      3,
      expect.objectContaining({
        payload: {
          action: 'replace',
          inputId,
          sourcePath: '/source/voice.mp3',
          managedRoot: '/managed'
        }
      })
    )
  })

  it('rejects invalid IDs, roles, paths, and engine responses', async () => {
    const validEngine = vi.fn(
      async (): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'input_state_changed',
        jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { inputs: [] }
      })
    )
    const manage = createManageInputHandler('/managed', validEngine)

    await expect(manage('bad', { action: 'remove', inputId })).rejects.toThrow('Job ID')
    await expect(
      manage(jobId, { action: 'assign_role', inputId, role: 'other' as 'voice' })
    ).rejects.toThrow('role')
    await expect(
      manage(jobId, { action: 'replace', inputId, sourcePath: 'relative.mp3' })
    ).rejects.toThrow('path')

    const badEngine = createManageInputHandler(
      '/managed',
      vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'health_checked',
          jobId,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: { status: 'ok' }
        })
      )
    )
    await expect(badEngine(jobId, { action: 'remove', inputId })).rejects.toThrow('engine response')
  })
})
