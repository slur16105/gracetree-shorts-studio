import type { DesktopApi } from '@gracetree/contracts/desktop-api'
import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'

import { desktopApi } from './desktop-api'

const electronMock = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
  getPathForFile: vi.fn()
}))

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: electronMock.exposeInMainWorld
  },
  ipcRenderer: {
    invoke: electronMock.invoke
  },
  webUtils: {
    getPathForFile: electronMock.getPathForFile
  }
}))

describe('desktopApi bridge surface', () => {
  beforeEach(() => {
    electronMock.exposeInMainWorld.mockClear()
    electronMock.invoke.mockClear()
    electronMock.getPathForFile.mockClear()
    vi.resetModules()
  })

  it('rejects privileged properties at the contract boundary', () => {
    expectTypeOf<{ ipcRenderer: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ fs: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ path: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ child_process: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ send: (channel: string) => void }>().not.toMatchTypeOf<DesktopApi>()
  })

  it('is a frozen allowlisted surface without privileged APIs', async () => {
    expect(Object.isFrozen(desktopApi)).toBe(true)
    expect(Object.keys(desktopApi)).toEqual([
      'getOrCreateJobForDate',
      'selectInputFiles',
      'registerInputFiles'
    ])
    expect(desktopApi).not.toHaveProperty('ipcRenderer')
    expect(desktopApi).not.toHaveProperty('fs')
    expect(desktopApi).not.toHaveProperty('path')
    expect(desktopApi).not.toHaveProperty('child_process')
    expect(desktopApi).not.toHaveProperty('send')
    electronMock.invoke.mockResolvedValue({ id: 'job' })
    await desktopApi.getOrCreateJobForDate('2026-06-20')
    expect(electronMock.invoke).toHaveBeenCalledWith('jobs:get-or-create-for-date', '2026-06-20')
    await desktopApi.selectInputFiles()
    expect(electronMock.invoke).toHaveBeenCalledWith('inputs:select-files')
    electronMock.getPathForFile.mockReturnValue('/source/voice.mp3')
    await desktopApi.registerInputFiles('job', [{ name: 'voice.mp3' }])
    expect(electronMock.invoke).toHaveBeenCalledWith('inputs:register-files', 'job', [
      { name: 'voice.mp3', sourcePath: '/source/voice.mp3' }
    ])
  })

  it('wires exactly one desktopApi namespace through contextBridge', async () => {
    await import('./index')

    expect(electronMock.exposeInMainWorld).toHaveBeenCalledTimes(1)
    const [[key, exposedValue]] = electronMock.exposeInMainWorld.mock.calls
    expect(key).toBe('desktopApi')
    expect(Object.keys(exposedValue)).toEqual([
      'getOrCreateJobForDate',
      'selectInputFiles',
      'registerInputFiles'
    ])
    expect(Object.isFrozen(exposedValue)).toBe(true)
  })
})
