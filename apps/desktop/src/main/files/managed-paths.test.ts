import { describe, expect, it } from 'vitest'

import { createManagedJobPaths, isValidJobId, isValidPublishDate } from './managed-paths'

describe('managed job paths', () => {
  it('creates canonical paths below the approved root', () => {
    expect(createManagedJobPaths('/Users/test/AppData', '2026-06-20')).toEqual({
      managedRoot: '/Users/test/AppData/GraceTreeData',
      databasePath: '/Users/test/AppData/GraceTreeData/studio.db',
      workPath: '/Users/test/AppData/GraceTreeData/jobs/2026-06-20'
    })
  })

  it.each(['2026-02-30', '2026/06/20', '../../escape', ''])('rejects invalid date %s', (value) => {
    expect(isValidPublishDate(value)).toBe(false)
    expect(() => createManagedJobPaths('/Users/test/AppData', value)).toThrow()
  })

  it('validates canonical UUID job IDs', () => {
    expect(isValidJobId('11111111-1111-4111-8111-111111111111')).toBe(true)
    expect(isValidJobId('not-a-uuid')).toBe(false)
  })
})
