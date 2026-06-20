import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

function luminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((value) => Number.parseInt(value, 16) / 255)
    .map((value) => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrast(foreground: string, background: string): number {
  const light = Math.max(luminance(foreground), luminance(background))
  const dark = Math.min(luminance(foreground), luminance(background))
  return (light + 0.05) / (dark + 0.05)
}

function readColorTokens(): Record<string, string> {
  const css = readFileSync(resolve(process.cwd(), 'src/renderer/src/styles/tokens.css'), 'utf8')
  return Object.fromEntries(
    [...css.matchAll(/--(color-[\w-]+):\s*(#[\da-f]{6})\s*;/gi)].map((match) => [
      match[1],
      match[2]
    ])
  )
}

describe('Studio Black tokens', () => {
  it('meet the target contrast ratios', () => {
    const tokens = readColorTokens()

    expect(contrast(tokens['color-text-primary'], tokens['color-panel'])).toBeGreaterThanOrEqual(
      4.5
    )
    expect(contrast(tokens['color-text-secondary'], tokens['color-panel'])).toBeGreaterThanOrEqual(
      4.5
    )
    expect(contrast(tokens['color-focus'], tokens['color-base'])).toBeGreaterThanOrEqual(3)
    expect(contrast(tokens['color-brand'], tokens['color-base'])).toBeGreaterThanOrEqual(3)
  })

  it('contains reduced-motion and scroll-safe zoom rules', () => {
    const globalCss = readFileSync(
      resolve(process.cwd(), 'src/renderer/src/styles/globals.css'),
      'utf8'
    )
    const appCss = readFileSync(
      resolve(process.cwd(), 'src/renderer/src/styles/App.module.css'),
      'utf8'
    )

    expect(globalCss).toContain('@media (prefers-reduced-motion: reduce)')
    expect(appCss).toMatch(/\.main\s*\{[^}]*overflow:\s*auto/s)
  })
})
