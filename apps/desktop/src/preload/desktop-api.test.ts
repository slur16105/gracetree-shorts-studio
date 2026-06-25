import type { DesktopApi } from '@gracetree/contracts/desktop-api'
import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'

import { desktopApi } from './desktop-api'

const electronMock = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  getPathForFile: vi.fn()
}))

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: electronMock.exposeInMainWorld
  },
  ipcRenderer: {
    invoke: electronMock.invoke,
    on: electronMock.on,
    off: electronMock.off
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
      'registerInputFiles',
      'assignInputRole',
      'removeInput',
      'replaceInput',
      'validateScript',
      'getResources',
      'updateResource',
      'selectResourceFile',
      'listCompletedJobs',
      'openResultFolder',
      'startJob',
      'cancelJob',
      'onJobEvent'
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
    await desktopApi.assignInputRole('job', 'input', 'voice')
    expect(electronMock.invoke).toHaveBeenCalledWith('inputs:assign-role', 'job', 'input', 'voice')
    await desktopApi.removeInput('job', 'input')
    expect(electronMock.invoke).toHaveBeenCalledWith('inputs:remove', 'job', 'input')
    await desktopApi.replaceInput('job', 'input', { name: 'new.mp3' })
    expect(electronMock.invoke).toHaveBeenCalledWith('inputs:replace', 'job', 'input', {
      name: 'new.mp3',
      sourcePath: '/source/voice.mp3'
    })
    await desktopApi.validateScript('job', 'input', 'abc123', '/managed/script.txt')
    expect(electronMock.invoke).toHaveBeenCalledWith(
      'script:validate',
      'job',
      'input',
      'abc123',
      '/managed/script.txt'
    )
    await desktopApi.getResources('/managed')
    expect(electronMock.invoke).toHaveBeenCalledWith('resources:get', '/managed')
    await desktopApi.updateResource('default_bgm', '/source/bgm.mp3', '/managed')
    expect(electronMock.invoke).toHaveBeenCalledWith(
      'resources:update',
      'default_bgm',
      '/source/bgm.mp3',
      '/managed'
    )
    await desktopApi.selectResourceFile('default_bgm')
    expect(electronMock.invoke).toHaveBeenCalledWith('resources:select-file', 'default_bgm')
    await desktopApi.listCompletedJobs('/managed')
    expect(electronMock.invoke).toHaveBeenCalledWith('jobs:list-completed', '/managed')
    await desktopApi.openResultFolder('job-id', '/managed/output')
    expect(electronMock.invoke).toHaveBeenCalledWith(
      'jobs:open-result',
      'job-id',
      '/managed/output'
    )
    await desktopApi.startJob('job-id', '/managed', '/work/path')
    expect(electronMock.invoke).toHaveBeenCalledWith('jobs:start', 'job-id', '/managed', '/work/path')
    await desktopApi.cancelJob('job-id', 'attempt-id')
    expect(electronMock.invoke).toHaveBeenCalledWith('jobs:cancel', 'job-id', 'attempt-id')
    const listener = vi.fn()
    const unsub = desktopApi.onJobEvent(listener)
    expect(electronMock.on).toHaveBeenCalledWith('jobs:event', expect.any(Function))
    unsub()
    expect(electronMock.off).toHaveBeenCalledWith('jobs:event', expect.any(Function))
  })

  it('wires exactly one desktopApi namespace through contextBridge', async () => {
    await import('./index')

    expect(electronMock.exposeInMainWorld).toHaveBeenCalledTimes(1)
    const [[key, exposedValue]] = electronMock.exposeInMainWorld.mock.calls
    expect(key).toBe('desktopApi')
    expect(Object.keys(exposedValue)).toEqual([
      'getOrCreateJobForDate',
      'selectInputFiles',
      'registerInputFiles',
      'assignInputRole',
      'removeInput',
      'replaceInput',
      'validateScript',
      'getResources',
      'updateResource',
      'selectResourceFile',
      'listCompletedJobs',
      'openResultFolder',
      'startJob',
      'cancelJob',
      'onJobEvent'
    ])
    expect(Object.isFrozen(exposedValue)).toBe(true)
  })
})
