import { describe, expect, it } from 'vitest'

import { createWindowOptions } from './window-options'

describe('BrowserWindow options', () => {
  it('enforces the shell size and renderer security boundary', () => {
    const options = createWindowOptions('/tmp/preload.js', 'darwin')

    expect(options).toMatchObject({
      width: 1180,
      height: 720,
      minWidth: 1180,
      minHeight: 720,
      webPreferences: {
        preload: '/tmp/preload.js',
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webviewTag: false
      }
    })
  })
})
