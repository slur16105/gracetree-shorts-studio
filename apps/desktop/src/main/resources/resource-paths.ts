import { join } from 'node:path'

export function getResourcesPath(managedRoot: string): string {
  return join(managedRoot, 'resources')
}

export function getResourceFilePath(managedRoot: string, resourceType: string, ext: string): string {
  return join(getResourcesPath(managedRoot), `${resourceType}${ext}`)
}
