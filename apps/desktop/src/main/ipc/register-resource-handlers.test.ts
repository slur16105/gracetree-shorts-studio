import type { EngineEvent, GetResourcesCommand, UpdateResourceCommand } from '@gracetree/contracts'
import { describe, expect, it, vi } from 'vitest'

import {
  createGetResourcesHandler,
  createUpdateResourceHandler,
  selectResourceFile
} from './register-resource-handlers'

const managedRoot = '/managed'
const requestId = '11111111-1111-4111-8111-111111111111'
const idFactory = () => requestId

const sampleResources = [
  {
    type: 'default_bgm' as const,
    managedPath: '/managed/resources/default_bgm.mp3',
    status: 'ready' as const,
    updatedAt: '2026-06-20T00:00:00.000Z'
  }
]

const dialogMock = vi.hoisted(() => ({
  showOpenDialog: vi.fn()
}))

vi.mock('electron', () => ({
  dialog: dialogMock
}))

describe('getResources handler', () => {
  it('sends a get_resources command and returns ResourceDto[]', async () => {
    const requestEngine = vi.fn(
      async (command: GetResourcesCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'resources_loaded',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { resources: sampleResources }
      })
    )
    const handler = createGetResourcesHandler(managedRoot, requestEngine, idFactory)

    const result = await handler(managedRoot)

    expect(result).toEqual(sampleResources)
    expect(requestEngine).toHaveBeenCalledTimes(1)
    expect(requestEngine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'get_resources',
        jobId: requestId,
        payload: { managedRoot }
      })
    )
  })

  it('rejects an invalid engine event', async () => {
    const handler = createGetResourcesHandler(
      managedRoot,
      vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'health_checked',
          jobId: requestId,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: { status: 'ok' }
        })
      ),
      idFactory
    )

    await expect(handler(managedRoot)).rejects.toThrow('engine response')
  })
})

describe('updateResource handler', () => {
  it('sends an update_resource command and returns ResourceUpdateResult with no error', async () => {
    const requestEngine = vi.fn(
      async (command: UpdateResourceCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'resource_updated',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { resources: sampleResources, error: null }
      })
    )
    const handler = createUpdateResourceHandler(managedRoot, requestEngine, idFactory)

    const result = await handler('default_bgm', '/source/bgm.mp3', managedRoot)

    expect(result.resources).toEqual(sampleResources)
    expect(result.error).toBeNull()
    expect(requestEngine).toHaveBeenCalledTimes(1)
    expect(requestEngine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'update_resource',
        jobId: requestId,
        payload: {
          resourceType: 'default_bgm',
          sourcePath: '/source/bgm.mp3',
          managedRoot
        }
      })
    )
  })

  it('returns ResourceUpdateResult with error when engine reports an error', async () => {
    const engineError = {
      resourceType: 'default_bgm' as const,
      code: 'SOURCE_UNREADABLE',
      message: '파일을 읽을 수 없습니다'
    }
    const requestEngine = vi.fn(
      async (command: UpdateResourceCommand): Promise<EngineEvent> => ({
        protocolVersion: 1,
        type: 'resource_updated',
        jobId: command.jobId,
        timestamp: '2026-06-20T00:00:00.000Z',
        payload: { resources: sampleResources, error: engineError }
      })
    )
    const handler = createUpdateResourceHandler(managedRoot, requestEngine, idFactory)

    const result = await handler('default_bgm', '/source/bgm.mp3', managedRoot)

    expect(result.error).toEqual(engineError)
    expect(result.resources).toEqual(sampleResources)
  })

  it('rejects an invalid engine event', async () => {
    const handler = createUpdateResourceHandler(
      managedRoot,
      vi.fn(
        async (): Promise<EngineEvent> => ({
          protocolVersion: 1,
          type: 'health_checked',
          jobId: requestId,
          timestamp: '2026-06-20T00:00:00.000Z',
          payload: { status: 'ok' }
        })
      ),
      idFactory
    )

    await expect(handler('default_bgm', '/source/bgm.mp3', managedRoot)).rejects.toThrow(
      'engine response'
    )
  })
})

describe('selectResourceFile', () => {
  it('returns null when the dialog is cancelled', async () => {
    dialogMock.showOpenDialog.mockResolvedValue({ canceled: true, filePaths: [] })

    const result = await selectResourceFile('default_bgm')

    expect(result).toBeNull()
  })

  it('returns { name, sourcePath } when a file is selected', async () => {
    dialogMock.showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['/source/background.mp3']
    })

    const result = await selectResourceFile('default_bgm')

    expect(result).toEqual({ name: 'background.mp3', sourcePath: '/source/background.mp3' })
  })

  it('uses video filters for title_scripture_video', async () => {
    dialogMock.showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['/source/title.mp4']
    })

    await selectResourceFile('title_scripture_video')

    expect(dialogMock.showOpenDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: [{ name: 'Video Files', extensions: ['mp4', 'mov', 'avi', 'mkv'] }]
      })
    )
  })

  it('uses font filters for subtitle_font', async () => {
    dialogMock.showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['/source/font.ttf']
    })

    await selectResourceFile('subtitle_font')

    expect(dialogMock.showOpenDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: [{ name: 'Font Files', extensions: ['ttf', 'otf', 'woff', 'woff2'] }]
      })
    )
  })
})
