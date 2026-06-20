import { isAbsolute, join, resolve } from 'node:path'

export interface ManagedJobPaths {
  managedRoot: string
  databasePath: string
  workPath: string
}

export function isValidPublishDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const [year, month, day] = value.split('-').map(Number)
  const parsed = new Date(Date.UTC(year, month - 1, day))
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  )
}

export function isValidJobId(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
}

export function createManagedJobPaths(userDataPath: string, publishDate: string): ManagedJobPaths {
  if (!isAbsolute(userDataPath)) {
    throw new Error('User data path must be absolute')
  }
  if (!isValidPublishDate(publishDate)) {
    throw new Error('Publish date must be a valid YYYY-MM-DD date')
  }

  const managedRoot = resolve(userDataPath, 'GraceTreeData')
  const workPath = resolve(managedRoot, 'jobs', publishDate)
  if (!workPath.startsWith(`${managedRoot}${process.platform === 'win32' ? '\\' : '/'}`)) {
    throw new Error('Job path escapes the managed root')
  }

  return {
    managedRoot,
    databasePath: join(managedRoot, 'studio.db'),
    workPath
  }
}
