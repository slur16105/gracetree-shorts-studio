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

describe('Studio Black tokens', () => {
  it('meet the target contrast ratios', () => {
    expect(contrast('#F4F5F5', '#0D0F0F')).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#9FA4A4', '#0D0F0F')).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#7DD3FC', '#080909')).toBeGreaterThanOrEqual(3)
    expect(contrast('#FF2F62', '#080909')).toBeGreaterThanOrEqual(3)
  })

  it('contains reduced-motion and scroll-safe zoom rules', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/renderer/src/styles/globals.css'), 'utf8')
    expect(css).toContain('@media (prefers-reduced-motion: reduce)')
    expect(css).toContain('overflow: auto')
  })
})
