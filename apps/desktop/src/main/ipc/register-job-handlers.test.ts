import type {
  CompletedJobDto,
  EngineCommand,
  EngineEvent,
  JobDto
} from '@gracetree/contracts'
import { win32 } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import {
  createGetOrCreateJobHandler,
  createListCompletedJobsHandler,
  createOpenResultFolderHandler,
  isCanonicalResultPath
} from './register-job-handlers'

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

const completedJob: CompletedJobDto = {
  id: '22222222-2222-4222-8222-222222222222',
  publishDate: '2026-06-15',
  title: '주님의 은혜',
  completedAt: '2026-06-15T10:00:00.000Z',
  resultPath: '/Users/test/AppData/GraceTreeData/jobs/2026-06-15/output'
}

type MockRequestEngine = (command: EngineCommand) => Promise<EngineEvent>

describe('getOrCreateJobForDate handler', () => {
  it('validates and maps the renderer request to the engine command', async () => {
    const requestEngine = vi.fn<MockRequestEngine>(
      async (command) => ({
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

  it.each(['input', 'temp', 'output/nested'])(
    'rejects a non-canonical result directory: %s',
    async (directory) => {
      const requestEngine = vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'job_loaded',
          jobId: job.id,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: {
            job: {
              ...job,
              resultPath: `${job.workPath}/${directory}`
            }
          }
        })
      )
      const handler = createGetOrCreateJobHandler(
        '/Users/test/AppData',
        requestEngine,
        () => job.id
      )

      await expect(handler('2026-06-20')).rejects.toThrow('invalid managed path')
    }
  )

  it('rejects Windows cross-drive and absolute-relative path bypasses', () => {
    const workPath = String.raw`C:\Users\test\AppData\GraceTreeData\jobs\2026-06-20`

    expect(isCanonicalResultPath(workPath, String.raw`D:\output`, win32)).toBe(false)
    expect(isCanonicalResultPath(workPath, String.raw`C:\output`, win32)).toBe(false)
    expect(
      isCanonicalResultPath(
        workPath,
        String.raw`C:\Users\test\AppData\GraceTreeData\jobs\2026-06-20\output`,
        win32
      )
    ).toBe(true)
  })
})

describe('listCompletedJobs handler', () => {
  const managedRoot = '/Users/test/AppData/GraceTreeData'

  it('sends list_completed_jobs command and returns summaries with resultExists=true', async () => {
    const requestEngine = vi.fn(async (command: EngineCommand): Promise<EngineEvent> => ({
      protocolVersion: 1,
      type: 'completed_jobs_listed',
      jobId: command.jobId,
      timestamp: '2026-06-25T00:00:00.000Z',
      payload: { jobs: [completedJob] }
    }))
    const fsExistsSync = vi.fn(() => true)
    const handler = createListCompletedJobsHandler(
      managedRoot,
      requestEngine,
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync
    )

    const result = await handler(managedRoot)

    expect(requestEngine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'list_completed_jobs',
        payload: { managedRoot }
      })
    )
    expect(result).toEqual([{ ...completedJob, resultExists: true }])
    expect(fsExistsSync).toHaveBeenCalledWith(completedJob.resultPath)
  })

  it('returns resultExists=false when result folder is missing', async () => {
    const requestEngine = vi.fn(async (command: EngineCommand): Promise<EngineEvent> => ({
      protocolVersion: 1,
      type: 'completed_jobs_listed',
      jobId: command.jobId,
      timestamp: '2026-06-25T00:00:00.000Z',
      payload: { jobs: [completedJob] }
    }))
    const fsExistsSync = vi.fn(() => false)
    const handler = createListCompletedJobsHandler(
      managedRoot,
      requestEngine,
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync
    )

    const result = await handler(managedRoot)

    expect(result).toEqual([{ ...completedJob, resultExists: false }])
  })

  it('returns empty array when no completed jobs', async () => {
    const requestEngine = vi.fn(async (command: EngineCommand): Promise<EngineEvent> => ({
      protocolVersion: 1,
      type: 'completed_jobs_listed',
      jobId: command.jobId,
      timestamp: '2026-06-25T00:00:00.000Z',
      payload: { jobs: [] }
    }))
    const handler = createListCompletedJobsHandler(
      managedRoot,
      requestEngine,
      () => '33333333-3333-4333-8333-333333333333'
    )

    const result = await handler(managedRoot)

    expect(result).toEqual([])
  })

  it('throws when engine returns invalid response', async () => {
    const requestEngine = vi.fn(async (): Promise<EngineEvent> => ({
      protocolVersion: 1,
      type: 'health_checked',
      jobId: '33333333-3333-4333-8333-333333333333',
      timestamp: '2026-06-25T00:00:00.000Z',
      payload: { status: 'ok' }
    }))
    const handler = createListCompletedJobsHandler(
      managedRoot,
      requestEngine,
      () => '33333333-3333-4333-8333-333333333333'
    )

    await expect(handler(managedRoot)).rejects.toThrow('engine response is invalid')
  })
})

describe('openResultFolder handler', () => {
  const managedRoot = '/Users/test/AppData/GraceTreeData'

  function makeRequestEngine(jobs: CompletedJobDto[] = [completedJob]): MockRequestEngine {
    return vi.fn(async (command: EngineCommand): Promise<EngineEvent> => ({
      protocolVersion: 1,
      type: 'completed_jobs_listed',
      jobId: command.jobId,
      timestamp: '2026-06-26T00:00:00.000Z',
      payload: { jobs }
    }))
  }

  it('resolves job path from DB and calls shell.openPath', async () => {
    const fsExistsSync = vi.fn(() => true)
    const shellOpenPath = vi.fn(async () => '')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine(),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await handler(completedJob.id)

    expect(fsExistsSync).toHaveBeenCalledWith(completedJob.resultPath)
    expect(shellOpenPath).toHaveBeenCalledWith(completedJob.resultPath)
  })

  it('throws when job not found in DB', async () => {
    const fsExistsSync = vi.fn(() => true)
    const shellOpenPath = vi.fn(async () => '')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine([]),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await expect(handler('nonexistent-job-id')).rejects.toThrow('not found')
    expect(shellOpenPath).not.toHaveBeenCalled()
  })

  it('throws when result path is outside managed root', async () => {
    const escapingJob: CompletedJobDto = {
      ...completedJob,
      resultPath: '/other/location/output'
    }
    const fsExistsSync = vi.fn(() => true)
    const shellOpenPath = vi.fn(async () => '')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine([escapingJob]),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await expect(handler(escapingJob.id)).rejects.toThrow('managed root')
    expect(shellOpenPath).not.toHaveBeenCalled()
  })

  it('rejects path that only shares a prefix with managedRoot (no sep suffix)', async () => {
    const escapingJob: CompletedJobDto = {
      ...completedJob,
      resultPath: '/Users/test/AppData/GraceTreeDataExtra/output'
    }
    const fsExistsSync = vi.fn(() => true)
    const shellOpenPath = vi.fn(async () => '')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine([escapingJob]),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await expect(handler(escapingJob.id)).rejects.toThrow('managed root')
    expect(shellOpenPath).not.toHaveBeenCalled()
  })

  it('throws when result folder does not exist', async () => {
    const fsExistsSync = vi.fn(() => false)
    const shellOpenPath = vi.fn(async () => '')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine(),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await expect(handler(completedJob.id)).rejects.toThrow('does not exist')
    expect(shellOpenPath).not.toHaveBeenCalled()
  })

  it('throws when shell.openPath reports an OS error', async () => {
    const fsExistsSync = vi.fn(() => true)
    const shellOpenPath = vi.fn(async () => 'No application is associated with the file')
    const handler = createOpenResultFolderHandler(
      managedRoot,
      makeRequestEngine(),
      () => '33333333-3333-4333-8333-333333333333',
      fsExistsSync,
      shellOpenPath
    )

    await expect(handler(completedJob.id)).rejects.toThrow('Failed to open result folder')
  })
})
