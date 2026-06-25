import type {
  CompletedJobDto,
  EngineEvent,
  GetOrCreateJobCommand,
  JobDto,
  ListCompletedJobsCommand
} from '@gracetree/contracts'
import { isCompletedJobsListedEvent, isJobLoadedEvent } from '@gracetree/contracts'
import {
  JOBS_LIST_COMPLETED_CHANNEL,
  JOBS_OPEN_RESULT_CHANNEL,
  JOB_GET_OR_CREATE_CHANNEL,
  type CompletedJobSummary
} from '@gracetree/contracts/desktop-api'
import { shell, ipcMain } from 'electron'
import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

import { createManagedJobPaths, isValidJobId, isValidPublishDate } from '../files/managed-paths'

type RequestEngine = (command: GetOrCreateJobCommand | ListCompletedJobsCommand) => Promise<EngineEvent>

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
  fsExistsSync: (path: string) => boolean = existsSync,
  shellOpenPath: (path: string) => Promise<string> = shell.openPath.bind(shell)
): (jobId: string, resultPath: string) => Promise<void> {
  return async (_jobId: string, resultPath: string): Promise<void> => {
    if (!fsExistsSync(resultPath)) {
      throw new Error(`Result folder does not exist: ${resultPath}`)
    }
    await shellOpenPath(resultPath)
  }
}

export function registerJobHandlers(userDataPath: string, requestEngine: RequestEngine): void {
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

  const openResultFolder = createOpenResultFolderHandler()
  ipcMain.handle(JOBS_OPEN_RESULT_CHANNEL, (_event, jobId: unknown, resultPath: unknown) => {
    if (typeof jobId !== 'string' || typeof resultPath !== 'string') {
      throw new Error('Open result folder request is invalid')
    }
    return openResultFolder(jobId, resultPath)
  })
}
