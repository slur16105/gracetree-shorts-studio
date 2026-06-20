import { describe, expect, it } from 'vitest'

import { shouldBlockNavigation } from './navigation-policy'

describe('navigation policy', () => {
  it('allows the current document and same-document fragment changes', () => {
    expect(shouldBlockNavigation('file:///app/index.html', 'file:///app/index.html')).toBe(false)
    expect(shouldBlockNavigation('file:///app/index.html', 'file:///app/index.html#settings')).toBe(
      false
    )
    expect(
      shouldBlockNavigation('file:///app/index.html#home', 'file:///app/index.html#settings')
    ).toBe(false)
  })

  it('allows equivalent normalized URLs', () => {
    expect(shouldBlockNavigation('http://localhost:5173', 'http://localhost:5173/')).toBe(false)
    expect(
      shouldBlockNavigation('http://localhost:80/index.html', 'http://LOCALHOST/index.html')
    ).toBe(false)
  })

  it('blocks navigation to another document or an invalid target', () => {
    expect(shouldBlockNavigation('file:///app/index.html', 'https://example.com')).toBe(true)
    expect(shouldBlockNavigation('http://localhost:5173/', 'http://localhost:5173/other')).toBe(
      true
    )
    expect(shouldBlockNavigation('file:///app/index.html', 'not a valid URL')).toBe(true)
  })
})
