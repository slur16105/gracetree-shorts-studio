import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('production CSP', () => {
  it('allows local assets without remote or unsafe sources', () => {
    const html = readFileSync(resolve(process.cwd(), 'src/renderer/index.html'), 'utf8')
    const content = html.match(/Content-Security-Policy"\s+content="([^"]+)"/)?.[1]

    expect(content).toContain("default-src 'self'")
    expect(content).not.toContain('http:')
    expect(content).not.toContain('https:')
    expect(content).not.toContain('unsafe-eval')
    expect(content).not.toContain('unsafe-inline')
    expect(content).not.toContain('*')
  })
})
