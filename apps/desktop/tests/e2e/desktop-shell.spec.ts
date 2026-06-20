import { createRequire } from 'node:module'
import { resolve } from 'node:path'

import { _electron as electron, expect, test, type Page } from '@playwright/test'

const require = createRequire(__filename)
const executablePath = require('electron') as string
const appRoot = resolve(__dirname, '../..')

async function expectScrollableAndUnclipped(page: Page, selector: string): Promise<void> {
  const locator = page.locator(selector)
  await locator.scrollIntoViewIfNeeded()
  await expect(locator).toBeVisible()
  await expect
    .poll(() =>
      locator.evaluate((element) => ({
        clippedHorizontally: element.scrollWidth > element.clientWidth,
        clippedVertically: element.scrollHeight > element.clientHeight
      }))
    )
    .toEqual({ clippedHorizontally: false, clippedVertically: false })
}

test('loads the secure shell offline and remains usable at 200% zoom', async () => {
  const electronApp = await electron.launch({
    executablePath,
    args: ['out/main/index.js'],
    cwd: appRoot
  })

  try {
    const remoteRequests: string[] = []
    const context = electronApp.context()
    await context.route(/^https?:\/\//, async (route) => {
      remoteRequests.push(route.request().url())
      await route.abort('internetdisconnected')
    })
    const page = await electronApp.firstWindow()

    await expect(page).toHaveTitle('GraceTree Shorts Studio')
    await expect(page.getByRole('button', { name: '홈' })).toBeVisible()
    await expect(page.getByRole('button', { name: '사용 가이드' })).toBeVisible()
    await expect(page.getByRole('button', { name: '공통 리소스 설정' })).toBeVisible()

    const windowDimensions = await electronApp.evaluate(({ BrowserWindow }) => {
      const window = BrowserWindow.getAllWindows()[0]
      return {
        minimumSize: window?.getMinimumSize(),
        contentSize: window?.getContentSize()
      }
    })
    expect(windowDimensions.minimumSize?.[0]).toBeGreaterThanOrEqual(1180)
    expect(windowDimensions.minimumSize?.[1]).toBeGreaterThanOrEqual(720)
    expect(windowDimensions.contentSize?.[0]).toBeGreaterThanOrEqual(1180)
    expect(windowDimensions.contentSize?.[1]).toBeGreaterThanOrEqual(720)

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
    const zoomFactor = await electronApp.evaluate(({ BrowserWindow }) => {
      return BrowserWindow.getAllWindows()[0]?.webContents.getZoomFactor()
    })
    expect(zoomFactor).toBe(2)

    for (const name of ['홈', '사용 가이드', '공통 리소스 설정']) {
      const button = page.getByRole('button', { name })
      await button.scrollIntoViewIfNeeded()
      await expect(button).toBeVisible()
    }

    await expectScrollableAndUnclipped(page, 'h1#home-title')
    await expectScrollableAndUnclipped(page, 'footer span:nth-child(2)')
    await expectScrollableAndUnclipped(page, 'footer span:nth-child(3)')

    await page.getByRole('button', { name: '사용 가이드' }).click()
    await expectScrollableAndUnclipped(page, 'h1#guide-title')
    await expect(page.getByRole('button', { name: '사용 가이드' })).toHaveAttribute(
      'aria-current',
      'page'
    )

    await page.getByRole('button', { name: '공통 리소스 설정' }).click()
    const dialog = page.getByRole('dialog', { name: '공통 리소스 설정' })
    await dialog.scrollIntoViewIfNeeded()
    await expect(dialog).toBeVisible()
    await expect(
      dialog.getByText(
        '제목·말씀 영상, 기도 영상, 기본 배경음악과 자막 폰트 설정은 이후 단계에서 제공됩니다.'
      )
    ).toBeVisible()
    const closeButton = dialog.getByRole('button', { name: '설정 닫기' })
    await expect(closeButton).toBeFocused()
    await closeButton.click()
    await expect(dialog).toBeHidden()
    await expect(page.getByRole('button', { name: '공통 리소스 설정' })).toBeFocused()

    const overlap = await page.evaluate(() => {
      const elements = [
        document.querySelector('[aria-label="홈"]'),
        document.querySelector('[aria-label="사용 가이드"]'),
        document.querySelector('[aria-label="공통 리소스 설정"]'),
        ...document.querySelectorAll('footer span')
      ].filter((element): element is Element => element !== null)
      const rectangles = elements.map((element) => element.getBoundingClientRect())

      return rectangles.some((rectangle, index) =>
        rectangles
          .slice(index + 1)
          .some(
            (other) =>
              rectangle.left < other.right &&
              rectangle.right > other.left &&
              rectangle.top < other.bottom &&
              rectangle.bottom > other.top
          )
      )
    })
    expect(overlap).toBe(false)

    const originalUrl = page.url()
    const navigationAttempt = electronApp.evaluate(({ BrowserWindow }) => {
      const webContents = BrowserWindow.getAllWindows()[0]?.webContents
      if (!webContents) throw new Error('Main window is missing')

      return new Promise<{ attemptedUrl: string; currentUrl: string; prevented: boolean }>(
        (resolveAttempt) => {
          webContents.once('will-navigate', (event, attemptedUrl) => {
            setImmediate(() => {
              resolveAttempt({
                attemptedUrl,
                currentUrl: webContents.getURL(),
                prevented: event.defaultPrevented
              })
            })
          })
        }
      )
    })
    await page.evaluate(() => {
      window.location.href = 'https://example.com/'
    })
    await expect(navigationAttempt).resolves.toEqual({
      attemptedUrl: 'https://example.com/',
      currentUrl: originalUrl,
      prevented: true
    })

    await page.reload()
    await expect(page).toHaveTitle('GraceTree Shorts Studio')
    expect(remoteRequests).toEqual([])
  } finally {
    await electronApp.close()
  }
})
