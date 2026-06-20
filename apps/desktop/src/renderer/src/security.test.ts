import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

type CspDirectives = Map<string, string[]>

function readCspTemplate(): string {
  const html = readFileSync(resolve(process.cwd(), 'src/renderer/index.html'), 'utf8')
  const content = html.match(
    /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"\s*\/?>/i
  )?.[1]

  if (!content) {
    throw new Error('Content-Security-Policy meta tag is missing')
  }

  return content
}

function renderPolicy(template: string, environment: 'development' | 'production'): string {
  return template
    .replace('%VITE_CSP_STYLE_EXTRA%', environment === 'development' ? "'unsafe-inline'" : '')
    .replace(
      '%VITE_CSP_CONNECT_EXTRA%',
      environment === 'development' ? 'ws://localhost:* ws://127.0.0.1:*' : ''
    )
}

function parseDirectives(policy: string): CspDirectives {
  const directives: CspDirectives = new Map()

  for (const segment of policy.split(';')) {
    const [name, ...sources] = segment.trim().split(/\s+/)
    if (!name) continue
    if (directives.has(name)) {
      throw new Error(`Duplicate CSP directive: ${name}`)
    }
    directives.set(name, sources)
  }

  return directives
}

describe('production CSP', () => {
  it('parses into a strict local-only policy with explicit object and base defenses', () => {
    const directives = parseDirectives(renderPolicy(readCspTemplate(), 'production'))

    expect(Object.fromEntries(directives)).toEqual({
      'default-src': ["'self'"],
      'base-uri': ["'none'"],
      'object-src': ["'none'"],
      'script-src': ["'self'"],
      'style-src': ["'self'"],
      'img-src': ["'self'", 'data:'],
      'font-src': ["'self'"],
      'connect-src': ["'self'"]
    })

    const allSources = [...directives.values()].flat()
    expect(allSources).not.toContain("'unsafe-eval'")
    expect(allSources).not.toContain("'unsafe-inline'")
    expect(allSources.some((source) => /^https?:|^wss?:/i.test(source))).toBe(false)
    expect(allSources.some((source) => source === '*' || source.includes('*'))).toBe(false)
  })

  it('limits Vite development relaxations to inline styles and HMR WebSockets', () => {
    const directives = parseDirectives(renderPolicy(readCspTemplate(), 'development'))

    expect(directives.get('style-src')).toEqual(["'self'", "'unsafe-inline'"])
    expect(directives.get('connect-src')).toEqual([
      "'self'",
      'ws://localhost:*',
      'ws://127.0.0.1:*'
    ])
    expect(directives.get('script-src')).toEqual(["'self'"])
    expect(directives.get('object-src')).toEqual(["'none'"])
  })
})
