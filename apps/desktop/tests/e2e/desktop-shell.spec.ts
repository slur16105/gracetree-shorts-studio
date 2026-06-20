import { createRequire } from 'node:module'
import { resolve } from 'node:path'

import { _electron as electron, expect, test } from '@playwright/test'

const require = createRequire(__filename)
const executablePath = require('electron') as string
const appRoot = resolve(__dirname, '../..')

test('loads the secure shell offline and remains usable at 200% zoom', async () => {
  const electronApp = await electron.launch({
    executablePath,
    args: ['out/main/index.js'],
    cwd: appRoot
  })

  try {
    const page = await electronApp.firstWindow()
    const remoteRequests: string[] = []
    page.on('request', (request) => {
      if (/^https?:/.test(request.url())) {
        remoteRequests.push(request.url())
      }
    })

    await expect(page).toHaveTitle('GraceTree Shorts Studio')
    await expect(page.getByRole('button', { name: '홈' })).toBeVisible()
    await expect(page.getByRole('button', { name: '사용 가이드' })).toBeVisible()
    await expect(page.getByRole('button', { name: '공통 리소스 설정' })).toBeVisible()

    const minimumSize = await electronApp.evaluate(({ BrowserWindow }) => {
      return BrowserWindow.getAllWindows()[0]?.getMinimumSize()
    })
    expect(minimumSize).toEqual([1180, 720])

    const bridgeSurface = await page.evaluate(() => ({
      desktopApiKeys: Object.keys(window.desktopApi),
      hasNodeProcess: 'process' in window,
      hasNodeRequire: 'require' in window
    }))
    expect(bridgeSurface).toEqual({
      desktopApiKeys: [],
      hasNodeProcess: false,
      hasNodeRequire: false
    })

    await electronApp.evaluate(({ BrowserWindow }) => {
      BrowserWindow.getAllWindows()[0]?.webContents.setZoomFactor(2)
    })
    for (const name of ['홈', '사용 가이드', '공통 리소스 설정']) {
      const button = page.getByRole('button', { name })
      await button.scrollIntoViewIfNeeded()
      await expect(button).toBeVisible()
    }

    await page.reload()
    expect(remoteRequests).toEqual([])

    const originalUrl = page.url()
    await page.evaluate(() => {
      window.location.href = 'https://example.com/'
    })
    await page.waitForTimeout(250)
    expect(page.url()).toBe(originalUrl)
  } finally {
    await electronApp.close()
  }
})
