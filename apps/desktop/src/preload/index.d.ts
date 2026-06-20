import type { DesktopApi } from '@gracetree/contracts/desktop-api'

declare global {
  interface Window {
    desktopApi: DesktopApi
  }
}
