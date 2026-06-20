import { describe, expect, it, vi } from 'vitest'

import {
  createWindowOptions,
  enforceMinimumContentSize,
  MINIMUM_CONTENT_SIZE
} from './window-options'

describe('BrowserWindow options', () => {
  it('enforces the shell size and renderer security boundary', () => {
    const options = createWindowOptions('/tmp/preload.js', 'darwin')

    expect(options).toMatchObject({
      width: 1180,
      height: 720,
      useContentSize: true,
      webPreferences: {
        preload: '/tmp/preload.js',
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webviewTag: false
      }
    })
  })

  it('converts the required content minimum into native outer-window dimensions', () => {
    const window = {
      getContentSize: vi.fn(() => [1180, 720] as [number, number]),
      getSize: vi.fn(() => [1196, 759] as [number, number]),
      setContentSize: vi.fn(),
      setMinimumSize: vi.fn()
    }

    enforceMinimumContentSize(window)

    expect(window.setMinimumSize).toHaveBeenCalledWith(1196, 759)
    expect(window.setContentSize).not.toHaveBeenCalled()
  })

  it('grows undersized content before the window is shown', () => {
    const window = {
      getContentSize: vi.fn(() => [1100, 680] as [number, number]),
      getSize: vi.fn(() => [1116, 719] as [number, number]),
      setContentSize: vi.fn(),
      setMinimumSize: vi.fn()
    }

    enforceMinimumContentSize(window)

    expect(window.setMinimumSize).toHaveBeenCalledWith(
      MINIMUM_CONTENT_SIZE.width + 16,
      MINIMUM_CONTENT_SIZE.height + 39
    )
    expect(window.setContentSize).toHaveBeenCalledWith(1180, 720)
  })
})
