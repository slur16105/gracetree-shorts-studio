import type { DesktopApi, JOB_GET_OR_CREATE_CHANNEL } from '@gracetree/contracts/desktop-api'
import { ipcRenderer } from 'electron'

const jobGetOrCreateChannel: typeof JOB_GET_OR_CREATE_CHANNEL = 'jobs:get-or-create-for-date'

export const desktopApi = Object.freeze({
  getOrCreateJobForDate: (publishDate: string) =>
    ipcRenderer.invoke(jobGetOrCreateChannel, publishDate)
}) satisfies DesktopApi
