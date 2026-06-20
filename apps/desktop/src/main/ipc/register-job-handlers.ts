import type { EngineEvent, GetOrCreateJobCommand, JobDto } from '@gracetree/contracts'
import { isJobLoadedEvent } from '@gracetree/contracts'
import { JOB_GET_OR_CREATE_CHANNEL } from '@gracetree/contracts/desktop-api'
import { ipcMain } from 'electron'
import { randomUUID } from 'node:crypto'
import { relative, resolve } from 'node:path'

import { createManagedJobPaths, isValidJobId, isValidPublishDate } from '../files/managed-paths'

type RequestEngine = (command: GetOrCreateJobCommand) => Promise<EngineEvent>

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
    const resultPath = resolve(event.payload.job.resultPath)
    if (
      workPath !== resolve(paths.workPath) ||
      relative(workPath, resultPath).startsWith('..') ||
      relative(workPath, resultPath) === ''
    ) {
      throw new Error('Python engine response contains an invalid managed path')
    }
    return event.payload.job
  }
}

export function registerJobHandlers(userDataPath: string, requestEngine: RequestEngine): void {
  const handler = createGetOrCreateJobHandler(userDataPath, requestEngine)
  ipcMain.handle(JOB_GET_OR_CREATE_CHANNEL, (_event, publishDate: unknown) => {
    if (typeof publishDate !== 'string') {
      throw new Error('Publish date must be a string')
    }
    return handler(publishDate)
  })
}
