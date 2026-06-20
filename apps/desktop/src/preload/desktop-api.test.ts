import type { DesktopApi } from '@gracetree/contracts/desktop-api'
import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'

import { desktopApi } from './desktop-api'

const electronMock = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn()
}))

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: electronMock.exposeInMainWorld
  }
}))

describe('desktopApi bridge surface', () => {
  beforeEach(() => {
    electronMock.exposeInMainWorld.mockClear()
    vi.resetModules()
  })

  it('rejects privileged properties at the contract boundary', () => {
    expectTypeOf<{ ipcRenderer: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ fs: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ path: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ child_process: unknown }>().not.toMatchTypeOf<DesktopApi>()
    expectTypeOf<{ send: (channel: string) => void }>().not.toMatchTypeOf<DesktopApi>()
  })

  it('is a frozen empty surface without privileged APIs', () => {
    expect(Object.isFrozen(desktopApi)).toBe(true)
    expect(Object.keys(desktopApi)).toEqual([])
    expect(desktopApi).not.toHaveProperty('ipcRenderer')
    expect(desktopApi).not.toHaveProperty('fs')
    expect(desktopApi).not.toHaveProperty('path')
    expect(desktopApi).not.toHaveProperty('child_process')
    expect(desktopApi).not.toHaveProperty('send')
    expect(desktopApi).not.toHaveProperty('invoke')
  })

  it('wires exactly one empty desktopApi namespace through contextBridge', async () => {
    await import('./index')

    expect(electronMock.exposeInMainWorld).toHaveBeenCalledTimes(1)
    expect(electronMock.exposeInMainWorld).toHaveBeenCalledWith('desktopApi', desktopApi)

    const exposedValues = electronMock.exposeInMainWorld.mock.calls.map(([, value]) => value)
    expect(exposedValues).toEqual([desktopApi])
  })
})
