import { app, BrowserWindow } from 'electron'
import { join, resolve } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'
import { shouldBlockNavigation } from './navigation-policy'
import { createWindowOptions, enforceMinimumContentSize } from './window-options'
import { registerJobHandlers } from './ipc/register-job-handlers'
import { registerFileHandlers } from './ipc/register-file-handlers'
import { registerResourceHandlers } from './ipc/register-resource-handlers'
import { EngineClient } from './jobs/engine-client'
import { createManagedJobPaths } from './files/managed-paths'

const projectRoot = resolve(__dirname, '../../../..')
let engineClient: EngineClient | null = null

function createWindow(): void {
  const mainWindow = new BrowserWindow(
    createWindowOptions(join(__dirname, '../preload/index.js'), process.platform, icon)
  )

  mainWindow.on('ready-to-show', () => {
    enforceMinimumContentSize(mainWindow)
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  const preventBlockedNavigation = (event: Electron.Event, targetUrl: string): void => {
    if (shouldBlockNavigation(mainWindow.webContents.getURL(), targetUrl)) {
      event.preventDefault()
    }
  }

  mainWindow.webContents.on('will-navigate', preventBlockedNavigation)
  mainWindow.webContents.on('will-redirect', preventBlockedNavigation)

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.gracetree.shorts-studio')
  const userDataPath = app.getPath('userData')
  const managedRoot = createManagedJobPaths(userDataPath, '2000-01-01').managedRoot
  engineClient = new EngineClient(projectRoot, managedRoot)
  registerJobHandlers(userDataPath, (command) => {
    if (!engineClient) throw new Error('Python engine is unavailable')
    return engineClient.request(command)
  })
  registerFileHandlers(managedRoot, (command) => {
    if (!engineClient) throw new Error('Python engine is unavailable')
    return engineClient.request(command)
  })
  registerResourceHandlers(userDataPath, (command) => {
    if (!engineClient) throw new Error('Python engine is unavailable')
    return engineClient.request(command)
  })

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  createWindow()

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', () => {
  engineClient?.stop()
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.
