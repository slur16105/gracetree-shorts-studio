import { describe, expect, it } from 'vitest'

import { shouldBlockNavigation } from './navigation-policy'

describe('navigation policy', () => {
  it('allows only the current document URL', () => {
    expect(shouldBlockNavigation('file:///app/index.html', 'file:///app/index.html')).toBe(false)
    expect(shouldBlockNavigation('file:///app/index.html', 'https://example.com')).toBe(true)
    expect(shouldBlockNavigation('http://localhost:5173/', 'http://localhost:5173/other')).toBe(
      true
    )
  })
})
