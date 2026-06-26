import type {
  CancelJobCommand,
  CompletedJobDto,
  EngineEvent,
  GetOrCreateJobCommand,
  JobDto,
  ListCompletedJobsCommand
} from '@gracetree/contracts'
import { isCompletedJobsListedEvent, isJobCancelledEvent, isJobLoadedEvent } from '@gracetree/contracts'
import {
  JOB_CANCEL_CHANNEL,
  JOB_GET_OR_CREATE_CHANNEL,
  JOB_START_CHANNEL,
  JOBS_LIST_COMPLETED_CHANNEL,
  JOBS_OPEN_LOG_CHANNEL,
  JOBS_OPEN_RESULT_CHANNEL,
  type CompletedJobSummary
} from '@gracetree/contracts/desktop-api'
import { shell, ipcMain } from 'electron'
import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { resolve, sep } from 'node:path'

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

export function createOpenResultFolderHandler(
  managedRoot: string,
  requestEngine: RequestEngine,
  idFactory: () => string = randomUUID,
  fsExistsSync: (path: string) => boolean = existsSync,
  shellOpenPath: (path: string) => Promise<string> = shell.openPath.bind(shell)
): (jobId: string) => Promise<void> {
  return async (jobId: string): Promise<void> => {
    // 1. Authoritative path lookup from DB — renderer cannot supply arbitrary paths
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

    const job = event.payload.jobs.find((j: CompletedJobDto) => j.id === jobId)
    if (!job) {
      throw new Error(`Job not found: ${jobId}`)
    }

    // 2. Validate path is within managedRoot.
    // resolve() normalises '..' segments but does NOT dereference symlinks.
    // Symlink escape is a separate OS-level concern; this guard prevents path-traversal.
    const canonicalManaged = resolve(managedRoot)
    const canonicalResult = resolve(job.resultPath)
    if (!canonicalResult.startsWith(canonicalManaged + sep)) {
      throw new Error(`Result path is outside managed root: ${job.resultPath}`)
    }

    // 3. Existence check (use resolved path so normalised '..' forms are handled consistently)
    if (!fsExistsSync(canonicalResult)) {
      throw new Error(`Result folder does not exist: ${job.resultPath}`)
    }

    // 4. Open in OS file explorer (use resolved path for consistency with the security check)
    const openError = await shellOpenPath(canonicalResult)
    if (openError) {
      throw new Error(`Failed to open result folder: ${openError}`)
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

  const openResultFolder = createOpenResultFolderHandler(managedRoot, requestEngine)
  ipcMain.handle(JOBS_OPEN_RESULT_CHANNEL, (_event, jobId: unknown) => {
    if (typeof jobId !== 'string') {
      throw new Error('Open result folder request is invalid')
    }
    return openResultFolder(jobId)
  })

  // job start-to-log-path cache for openLogFolder
  const jobWorkPaths = new Map<string, string>()
  ipcMain.handle(JOBS_OPEN_LOG_CHANNEL, async (_event, jobId: unknown, _attemptId: unknown) => {
    if (typeof jobId !== 'string') {
      throw new Error('openLogFolder args invalid')
    }
    const storedWorkPath = jobWorkPaths.get(jobId)
    if (!storedWorkPath) {
      throw new Error('Log folder not available for this job')
    }
    const logDir = resolve(storedWorkPath, 'logs')
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
    (event, jobId: unknown, jobManagedRoot: unknown, workPath: unknown) => {
      if (
        typeof jobId !== 'string' ||
        typeof jobManagedRoot !== 'string' ||
        typeof workPath !== 'string'
      ) {
        throw new Error('startJob args invalid')
      }
      jobWorkPaths.set(jobId, workPath)
      return jobService.startJob(event.sender, jobId, jobManagedRoot, workPath)
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
    if (!isJobCancelledEvent(event) || event.jobId !== jobId) {
      throw new Error('Python engine cancel response is invalid')
    }
  })
}
