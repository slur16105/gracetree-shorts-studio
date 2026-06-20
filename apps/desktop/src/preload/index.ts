import type { DESKTOP_API_KEY } from '@gracetree/contracts/desktop-api'
import { contextBridge } from 'electron'

import { desktopApi } from './desktop-api'

const desktopApiKey: typeof DESKTOP_API_KEY = 'desktopApi'

contextBridge.exposeInMainWorld(desktopApiKey, desktopApi)
