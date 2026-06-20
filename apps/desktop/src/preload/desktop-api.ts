import type {
  DesktopApi,
  INPUT_REGISTER_CHANNEL,
  INPUT_SELECT_CHANNEL,
  InputFileCandidate,
  JOB_GET_OR_CREATE_CHANNEL
} from '@gracetree/contracts/desktop-api'
import { ipcRenderer, webUtils } from 'electron'

const jobGetOrCreateChannel: typeof JOB_GET_OR_CREATE_CHANNEL = 'jobs:get-or-create-for-date'
const inputSelectChannel: typeof INPUT_SELECT_CHANNEL = 'inputs:select-files'
const inputRegisterChannel: typeof INPUT_REGISTER_CHANNEL = 'inputs:register-files'

export const desktopApi = Object.freeze({
  getOrCreateJobForDate: (publishDate: string) =>
    ipcRenderer.invoke(jobGetOrCreateChannel, publishDate),
  selectInputFiles: () => ipcRenderer.invoke(inputSelectChannel),
  registerInputFiles: (jobId: string, files: InputFileCandidate[]) => {
    const selected = files.map((file) => {
      let sourcePath = file.sourcePath ?? ''
      if (!sourcePath) {
        try {
          sourcePath = webUtils.getPathForFile(file as unknown as File)
        } catch {
          sourcePath = ''
        }
      }
      return { name: file.name, sourcePath }
    })
    return ipcRenderer.invoke(inputRegisterChannel, jobId, selected)
  }
}) satisfies DesktopApi
