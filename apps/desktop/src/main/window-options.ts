import type { BrowserWindowConstructorOptions } from 'electron'

export const MINIMUM_CONTENT_SIZE = {
  width: 1180,
  height: 720
} as const

type ContentSizedWindow = Pick<
  Electron.BrowserWindow,
  'getContentSize' | 'getSize' | 'setContentSize' | 'setMinimumSize'
>

export function createWindowOptions(
  preload: string,
  platform: NodeJS.Platform,
  linuxIcon?: string
): BrowserWindowConstructorOptions {
  return {
    width: MINIMUM_CONTENT_SIZE.width,
    height: MINIMUM_CONTENT_SIZE.height,
    useContentSize: true,
    show: false,
    autoHideMenuBar: true,
    // Match the app base surface so there is no white flash before paint.
    backgroundColor: '#0a0a0b',
    // macOS: hide the native title bar but keep inset traffic lights, letting the
    // dark content reach the top edge for a native-app feel. The renderer reserves
    // space and a drag region in the sidebar.
    ...(platform === 'darwin'
      ? { titleBarStyle: 'hiddenInset' as const, trafficLightPosition: { x: 16, y: 14 } }
      : {}),
    ...(platform === 'linux' && linuxIcon ? { icon: linuxIcon } : {}),
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: false
    }
  }
}

export function enforceMinimumContentSize(window: ContentSizedWindow): void {
  const [contentWidth, contentHeight] = window.getContentSize()
  const [outerWidth, outerHeight] = window.getSize()
  const frameWidth = Math.max(0, outerWidth - contentWidth)
  const frameHeight = Math.max(0, outerHeight - contentHeight)

  window.setMinimumSize(
    MINIMUM_CONTENT_SIZE.width + frameWidth,
    MINIMUM_CONTENT_SIZE.height + frameHeight
  )

  if (contentWidth < MINIMUM_CONTENT_SIZE.width || contentHeight < MINIMUM_CONTENT_SIZE.height) {
    window.setContentSize(
      Math.max(contentWidth, MINIMUM_CONTENT_SIZE.width),
      Math.max(contentHeight, MINIMUM_CONTENT_SIZE.height)
    )
  }
}
