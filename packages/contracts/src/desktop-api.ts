import type { JobDto } from './protocol.js'

export const DESKTOP_API_KEY = 'desktopApi' as const

export const JOB_GET_OR_CREATE_CHANNEL = 'jobs:get-or-create-for-date' as const

export interface DesktopApi {
  getOrCreateJobForDate(publishDate: string): Promise<JobDto>
}
