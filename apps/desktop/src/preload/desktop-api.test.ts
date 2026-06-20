import { describe, expect, it } from 'vitest'

import { desktopApi } from './desktop-api'

describe('desktopApi bridge surface', () => {
  it('is a frozen empty surface without privileged APIs', () => {
    expect(Object.isFrozen(desktopApi)).toBe(true)
    expect(Object.keys(desktopApi)).toEqual([])
    expect(desktopApi).not.toHaveProperty('ipcRenderer')
    expect(desktopApi).not.toHaveProperty('fs')
    expect(desktopApi).not.toHaveProperty('child_process')
  })
})
