import type { EngineEvent, GetOrCreateJobCommand, JobDto } from '@gracetree/contracts'
import { describe, expect, it, vi } from 'vitest'

import { createGetOrCreateJobHandler } from './register-job-handlers'

const job: JobDto = {
  id: '11111111-1111-4111-8111-111111111111',
  publishDate: '2026-06-20',
  status: 'draft',
  title: null,
  workPath: '/Users/test/AppData/GraceTreeData/jobs/2026-06-20',
  resultPath: '/Users/test/AppData/GraceTreeData/jobs/2026-06-20/output',
  createdAt: '2026-06-20T00:00:00.000Z',
  updatedAt: '2026-06-20T00:00:00.000Z',
  pathState: 'ready',
  inputMetadata: []
}

describe('getOrCreateJobForDate handler', () => {
  it('validates and maps the renderer request to the engine command', async () => {
    const requestEngine = vi.fn(
      async (command: GetOrCreateJobCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'job_loaded',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { job }
      })
    )
    const handler = createGetOrCreateJobHandler('/Users/test/AppData', requestEngine, () => job.id)

    await expect(handler('2026-06-20')).resolves.toEqual(job)
    expect(requestEngine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'get_or_create_job',
        jobId: job.id,
        payload: {
          publishDate: '2026-06-20',
          managedRoot: '/Users/test/AppData/GraceTreeData',
          workPath: job.workPath
        }
      })
    )
  })

  it('rejects invalid renderer dates before invoking Python', async () => {
    const requestEngine = vi.fn()
    const handler = createGetOrCreateJobHandler('/Users/test/AppData', requestEngine)

    await expect(handler('../../escape')).rejects.toThrow('Publish date')
    expect(requestEngine).not.toHaveBeenCalled()
  })

  it('rejects a mismatched or invalid engine response', async () => {
    const requestEngine = vi.fn(
      async (): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'job_loaded',
        jobId: '22222222-2222-4222-8222-222222222222',
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { job: { ...job, id: 'invalid' } }
      })
    )
    const handler = createGetOrCreateJobHandler('/Users/test/AppData', requestEngine, () => job.id)

    await expect(handler('2026-06-20')).rejects.toThrow('engine response')
  })
})
