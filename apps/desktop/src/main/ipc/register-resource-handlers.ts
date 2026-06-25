import type {
  EngineEvent,
  GetResourcesCommand,
  ResourceDto,
  ResourceType,
  UpdateResourceCommand
} from '@gracetree/contracts'
import {
  RESOURCE_TYPES,
  isResourceUpdatedEvent,
  isResourcesLoadedEvent
} from '@gracetree/contracts'
import {
  RESOURCE_GET_CHANNEL,
  RESOURCE_SELECT_FILE_CHANNEL,
  RESOURCE_UPDATE_CHANNEL,
  type ResourceUpdateResult,
  type SelectedInputFile
} from '@gracetree/contracts/desktop-api'
import { dialog, ipcMain } from 'electron'
import { basename } from 'node:path'
import { randomUUID } from 'node:crypto'

import { createManagedJobPaths } from '../files/managed-paths'

type GetResourcesEngine = (command: GetResourcesCommand) => Promise<EngineEvent>
type UpdateResourceEngine = (command: UpdateResourceCommand) => Promise<EngineEvent>

function isValidResourceType(value: unknown): value is ResourceType {
  return typeof value === 'string' && (RESOURCE_TYPES as readonly string[]).includes(value)
}

export function createGetResourcesHandler(
  managedRoot: string,
  requestEngine: GetResourcesEngine,
  idFactory: () => string = randomUUID
): (managedRoot: string) => Promise<ResourceDto[]> {
  return async (_managedRoot: string): Promise<ResourceDto[]> => {
    const requestId = idFactory()
    const command: GetResourcesCommand = {
      protocolVersion: 1,
      type: 'get_resources',
      jobId: requestId,
      timestamp: new Date().toISOString(),
      payload: { managedRoot }
    }
    const event = await requestEngine(command)
    if (!isResourcesLoadedEvent(event) || event.jobId !== requestId) {
      throw new Error('Python engine response is invalid')
    }
    return event.payload.resources
  }
}

export function createUpdateResourceHandler(
  managedRoot: string,
  requestEngine: UpdateResourceEngine,
  idFactory: () => string = randomUUID
): (resourceType: ResourceType, sourcePath: string, managedRoot: string) => Promise<ResourceUpdateResult> {
  return async (resourceType: ResourceType, sourcePath: string, _managedRoot: string): Promise<ResourceUpdateResult> => {
    const requestId = idFactory()
    const command: UpdateResourceCommand = {
      protocolVersion: 1,
      type: 'update_resource',
      jobId: requestId,
      timestamp: new Date().toISOString(),
      payload: { resourceType, sourcePath, managedRoot }
    }
    const event = await requestEngine(command)
    if (!isResourceUpdatedEvent(event) || event.jobId !== requestId) {
      throw new Error('Python engine response is invalid')
    }
    return {
      resources: event.payload.resources,
      error: event.payload.error
    }
  }
}

const FILE_FILTERS: Record<ResourceType, { name: string; extensions: string[] }[]> = {
  title_scripture_video: [
    { name: 'Video Files', extensions: ['mp4', 'mov', 'avi', 'mkv'] }
  ],
  prayer_loop_video: [
    { name: 'Video Files', extensions: ['mp4', 'mov', 'avi', 'mkv'] }
  ],
  default_bgm: [
    { name: 'Audio Files', extensions: ['mp3', 'wav', 'aac', 'm4a', 'ogg', 'flac'] }
  ],
  subtitle_font: [
    { name: 'Font Files', extensions: ['ttf', 'otf', 'woff', 'woff2'] }
  ]
}

export async function selectResourceFile(
  resourceType: ResourceType
): Promise<SelectedInputFile | null> {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    title: '리소스 파일 선택',
    filters: FILE_FILTERS[resourceType]
  })
  if (result.canceled || result.filePaths.length === 0) return null
  const sourcePath = result.filePaths[0]!
  return { name: basename(sourcePath), sourcePath }
}

export function registerResourceHandlers(
  userDataPath: string,
  requestEngine: GetResourcesEngine & UpdateResourceEngine
): void {
  const managedRoot = createManagedJobPaths(userDataPath, '2000-01-01').managedRoot
  const getResources = createGetResourcesHandler(managedRoot, requestEngine)
  const updateResource = createUpdateResourceHandler(managedRoot, requestEngine)

  ipcMain.handle(RESOURCE_GET_CHANNEL, (_event, managedRootArg: unknown) => {
    if (typeof managedRootArg !== 'string') {
      throw new Error('Resource get request is invalid')
    }
    return getResources(managedRootArg)
  })

  ipcMain.handle(
    RESOURCE_UPDATE_CHANNEL,
    (_event, resourceType: unknown, sourcePath: unknown, managedRootArg: unknown) => {
      if (
        !isValidResourceType(resourceType) ||
        typeof sourcePath !== 'string' ||
        typeof managedRootArg !== 'string'
      ) {
        throw new Error('Resource update request is invalid')
      }
      return updateResource(resourceType, sourcePath, managedRootArg)
    }
  )

  ipcMain.handle(RESOURCE_SELECT_FILE_CHANNEL, (_event, resourceType: unknown) => {
    if (!isValidResourceType(resourceType)) {
      throw new Error('Resource select file request is invalid')
    }
    return selectResourceFile(resourceType)
  })
}
