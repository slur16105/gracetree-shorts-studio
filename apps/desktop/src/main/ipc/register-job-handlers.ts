import type {
  CancelJobCommand,
  CompletedJobDto,
  EngineEvent,
  GetOrCreateJobCommand,
  JobDto,
  ListCompletedJobsCommand
} from '@gracetree/contracts'
import { isCompletedJobsListedEvent, isJobCancelledEvent, isJobCompletedEvent, isJobFailedEvent, isJobLoadedEvent } from '@gracetree/contracts'
import {
  JOB_CANCEL_CHANNEL,
  JOB_GET_OR_CREATE_CHANNEL,
  JOB_START_CHANNEL,
  JOBS_LIST_COMPLETED_CHANNEL,
  JOBS_OPEN_DOWNLOADS_CHANNEL,
  JOBS_OPEN_LOG_CHANNEL,
  type CompletedJobSummary
} from '@gracetree/contracts/desktop-api'
import { app, shell, ipcMain } from 'electron'
import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { dirname, resolve, sep } from 'node:path'

import { createManagedJobPaths, isValidJobId, isValidPublishDate } from '../files/managed-paths'
import type { JobService } from '../jobs/job-service'

type RequestEngine = (
  command: GetOrCreateJobCommand | ListCompletedJobsCommand | CancelJobCommand
) => Promise<EngineEvent>

interface PathResolver {
  resolve(...paths: string[]): string
}

export function isCanonicalResultPath(
  workPath: string,
  resultPath: string,
  pathResolver: PathResolver = { resolve }
): boolean {
  const canonicalWorkPath = pathResolver.resolve(workPath)
  return pathResolver.resolve(resultPath) === pathResolver.resolve(canonicalWorkPath, 'output')
}

export function createGetOrCreateJobHandler(
  userDataPath: string,
  requestEngine: RequestEngine,
  idFactory: () => string = randomUUID
): (publishDate: string) => Promise<JobDto> {
  return async (publishDate: string): Promise<JobDto> => {
    if (!isValidPublishDate(publishDate)) {
      throw new Error('Publish date must be a valid YYYY-MM-DD date')
    }
    const paths = createManagedJobPaths(userDataPath, publishDate)
    const requestId = idFactory()
    if (!isValidJobId(requestId)) {
      throw new Error('Generated job ID is invalid')
    }

    const command: GetOrCreateJobCommand = {
      protocolVersion: 1,
      type: 'get_or_create_job',
      jobId: requestId,
      timestamp: new Date().toISOString(),
      payload: {
        publishDate,
        managedRoot: paths.managedRoot,
        workPath: paths.workPath
      }
    }
    const event = await requestEngine(command)
    if (
      !isJobLoadedEvent(event) ||
      event.jobId !== requestId ||
      event.payload.job.publishDate !== publishDate ||
      !isValidJobId(event.payload.job.id)
    ) {
      throw new Error('Python engine response is invalid')
    }

    const workPath = resolve(event.payload.job.workPath)
    if (
      workPath !== resolve(paths.workPath) ||
      !isCanonicalResultPath(workPath, event.payload.job.resultPath)
    ) {
      throw new Error('Python engine response contains an invalid managed path')
    }
    return event.payload.job
  }
}

export function createListCompletedJobsHandler(
  managedRoot: string,
  requestEngine: RequestEngine,
  idFactory: () => string = randomUUID,
  fsExistsSync: (path: string) => boolean = existsSync
): (managedRoot: string) => Promise<CompletedJobSummary[]> {
  return async (_managedRoot: string): Promise<CompletedJobSummary[]> => {
    const requestId = idFactory()
    const command: ListCompletedJobsCommand = {
      protocolVersion: 1,
      type: 'list_completed_jobs',
      jobId: requestId,
      timestamp: new Date().toISOString(),
      payload: { managedRoot }
    }
    const event = await requestEngine(command)
    if (!isCompletedJobsListedEvent(event) || event.jobId !== requestId) {
      throw new Error('Python engine response is invalid')
    }
    return event.payload.jobs.map((job: CompletedJobDto): CompletedJobSummary => ({
      ...job,
      resultExists: fsExistsSync(job.resultPath)
    }))
  }
}

export function createOpenDownloadsFolderHandler(
  downloadsPath: string,
  shellOpenPath: (path: string) => Promise<string> = shell.openPath.bind(shell)
): () => Promise<void> {
  return async (): Promise<void> => {
    // Completed videos are exported to the OS Downloads folder, so "open" always
    // targets that fixed location — no per-job path lookup or validation needed.
    const openError = await shellOpenPath(downloadsPath)
    if (openError) {
      throw new Error(`Failed to open downloads folder: ${openError}`)
    }
  }
}

export function registerJobHandlers(
  userDataPath: string,
  requestEngine: RequestEngine,
  jobService: JobService
): void {
  const getOrCreateJob = createGetOrCreateJobHandler(userDataPath, requestEngine)
  ipcMain.handle(JOB_GET_OR_CREATE_CHANNEL, (_event, publishDate: unknown) => {
    if (typeof publishDate !== 'string') {
      throw new Error('Publish date must be a string')
    }
    return getOrCreateJob(publishDate)
  })

  const managedRoot = createManagedJobPaths(userDataPath, '2000-01-01').managedRoot
  const listCompletedJobs = createListCompletedJobsHandler(managedRoot, requestEngine)
  ipcMain.handle(JOBS_LIST_COMPLETED_CHANNEL, (_event, managedRootArg: unknown) => {
    if (typeof managedRootArg !== 'string') {
      throw new Error('List completed jobs request is invalid')
    }
    return listCompletedJobs(managedRootArg)
  })

  const openDownloadsFolder = createOpenDownloadsFolderHandler(app.getPath('downloads'))
  ipcMain.handle(JOBS_OPEN_DOWNLOADS_CHANNEL, () => openDownloadsFolder())

  // job start-to-log-path cache for openLogFolder
  const jobWorkPaths = new Map<string, string>()
  ipcMain.handle(JOBS_OPEN_LOG_CHANNEL, async (_event, jobId: unknown, attemptId: unknown) => {
    if (typeof jobId !== 'string' || typeof attemptId !== 'string') {
      throw new Error('openLogFolder args invalid')
    }
    let logDir: string | null = null

    const storedWorkPath = jobWorkPaths.get(jobId)
    if (storedWorkPath) {
      logDir = resolve(storedWorkPath, 'logs')
    } else {
      // Fall back to DB when in-session cache is unavailable (e.g. after restart)
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { DatabaseSync } = require('node:sqlite') as {
          DatabaseSync: new (path: string) => {
            prepare(sql: string): { get(...args: unknown[]): unknown }
            close(): void
          }
        }
        const dbPath = resolve(managedRoot, 'studio.db')
        const db = new DatabaseSync(dbPath)
        const row = db
          .prepare('SELECT log_path FROM job_attempts WHERE id = ?')
          .get(attemptId) as { log_path: string | null } | undefined
        db.close()
        if (row?.log_path) {
          logDir = dirname(resolve(row.log_path))
        }
      } catch {
        // node:sqlite unavailable or DB error — logDir stays null
      }
    }

    if (!logDir) {
      throw new Error('Log folder not available for this job')
    }
    const canonicalManaged = resolve(managedRoot)
    if (!logDir.startsWith(canonicalManaged + sep)) {
      throw new Error('Log folder is outside managed root')
    }
    const openError = await shell.openPath(logDir)
    if (openError) {
      throw new Error(`Failed to open log folder: ${openError}`)
    }
  })

  ipcMain.handle(
    JOB_START_CHANNEL,
    (event, jobId: unknown, jobManagedRoot: unknown, workPath: unknown, regenerate: unknown) => {
      if (
        typeof jobId !== 'string' ||
        typeof jobManagedRoot !== 'string' ||
        typeof workPath !== 'string'
      ) {
        throw new Error('startJob args invalid')
      }
      const isRegenerate = regenerate === true
      jobWorkPaths.set(jobId, workPath)
      return jobService.startJob(event.sender, jobId, jobManagedRoot, workPath, isRegenerate)
    }
  )

  ipcMain.handle(JOB_CANCEL_CHANNEL, async (_event, jobId: unknown, attemptId: unknown) => {
    if (typeof jobId !== 'string' || typeof attemptId !== 'string') {
      throw new Error('cancelJob args invalid')
    }
    const command: CancelJobCommand = {
      protocolVersion: 1,
      type: 'cancel_job',
      jobId,
      timestamp: new Date().toISOString(),
      payload: { attemptId }
    }
    const event = await requestEngine(command)
    // Accept any terminal event: job_cancelled is normal, job_completed/job_failed means
    // the job finished before the cancel signal reached a checkpoint (race condition).
    const isTerminalForJob =
      (isJobCancelledEvent(event) || isJobCompletedEvent(event) || isJobFailedEvent(event)) &&
      event.jobId === jobId
    if (!isTerminalForJob) {
      throw new Error('Python engine cancel response is invalid')
    }
  })
}
