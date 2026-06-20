import type { BrowserWindowConstructorOptions } from 'electron'

export function createWindowOptions(
  preload: string,
  platform: NodeJS.Platform,
  linuxIcon?: string
): BrowserWindowConstructorOptions {
  return {
    width: 1180,
    height: 720,
    minWidth: 1180,
    minHeight: 720,
    show: false,
    autoHideMenuBar: true,
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
