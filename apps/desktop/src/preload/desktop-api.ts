import type {
  DesktopApi,
  EngineEvent,
  INPUT_ASSIGN_ROLE_CHANNEL,
  INPUT_REGISTER_CHANNEL,
  INPUT_REMOVE_CHANNEL,
  INPUT_REPLACE_CHANNEL,
  INPUT_SELECT_CHANNEL,
  InputFileCandidate,
  JOB_CANCEL_CHANNEL,
  JOB_EVENT_CHANNEL,
  JOB_GET_OR_CREATE_CHANNEL,
  JOB_START_CHANNEL,
  JOBS_LIST_COMPLETED_CHANNEL,
  JOBS_OPEN_LOG_CHANNEL,
  JOBS_OPEN_RESULT_CHANNEL,
  RESOURCE_GET_CHANNEL,
  RESOURCE_SELECT_FILE_CHANNEL,
  RESOURCE_UPDATE_CHANNEL,
  SCRIPT_VALIDATE_CHANNEL
} from '@gracetree/contracts/desktop-api'
import { ipcRenderer, type IpcRendererEvent, webUtils } from 'electron'

const jobGetOrCreateChannel: typeof JOB_GET_OR_CREATE_CHANNEL = 'jobs:get-or-create-for-date'
const jobStartChannel: typeof JOB_START_CHANNEL = 'jobs:start'
const jobCancelChannel: typeof JOB_CANCEL_CHANNEL = 'jobs:cancel'
const jobEventChannel: typeof JOB_EVENT_CHANNEL = 'jobs:event'
const inputSelectChannel: typeof INPUT_SELECT_CHANNEL = 'inputs:select-files'
const inputRegisterChannel: typeof INPUT_REGISTER_CHANNEL = 'inputs:register-files'
const inputAssignRoleChannel: typeof INPUT_ASSIGN_ROLE_CHANNEL = 'inputs:assign-role'
const inputRemoveChannel: typeof INPUT_REMOVE_CHANNEL = 'inputs:remove'
const inputReplaceChannel: typeof INPUT_REPLACE_CHANNEL = 'inputs:replace'
const scriptValidateChannel: typeof SCRIPT_VALIDATE_CHANNEL = 'script:validate'
const resourceGetChannel: typeof RESOURCE_GET_CHANNEL = 'resources:get'
const resourceUpdateChannel: typeof RESOURCE_UPDATE_CHANNEL = 'resources:update'
const resourceSelectFileChannel: typeof RESOURCE_SELECT_FILE_CHANNEL = 'resources:select-file'
const jobsListCompletedChannel: typeof JOBS_LIST_COMPLETED_CHANNEL = 'jobs:list-completed'
const jobsOpenResultChannel: typeof JOBS_OPEN_RESULT_CHANNEL = 'jobs:open-result'
const jobsOpenLogChannel: typeof JOBS_OPEN_LOG_CHANNEL = 'jobs:open-log'

function toSelectedFile(file: InputFileCandidate): { name: string; sourcePath: string } {
  let sourcePath = file.sourcePath ?? ''
  if (!sourcePath) {
    try {
      sourcePath = webUtils.getPathForFile(file as unknown as File)
    } catch {
      throw new Error('파일 경로를 읽을 수 없습니다.')
    }
  }
  return { name: file.name, sourcePath }
}

export const desktopApi = Object.freeze({
  getOrCreateJobForDate: (publishDate: string) =>
    ipcRenderer.invoke(jobGetOrCreateChannel, publishDate),
  selectInputFiles: () => ipcRenderer.invoke(inputSelectChannel),
  registerInputFiles: (jobId: string, files: InputFileCandidate[]) => {
    const selected = files.map(toSelectedFile)
    return ipcRenderer.invoke(inputRegisterChannel, jobId, selected)
  },
  assignInputRole: (jobId, inputId, role) =>
    ipcRenderer.invoke(inputAssignRoleChannel, jobId, inputId, role),
  removeInput: (jobId, inputId) => ipcRenderer.invoke(inputRemoveChannel, jobId, inputId),
  replaceInput: (jobId, inputId, file) =>
    ipcRenderer.invoke(inputReplaceChannel, jobId, inputId, toSelectedFile(file)),
  validateScript: (jobId, inputId, inputVersion, managedPath) =>
    ipcRenderer.invoke(scriptValidateChannel, jobId, inputId, inputVersion, managedPath),
  getResources: (managedRoot) => ipcRenderer.invoke(resourceGetChannel, managedRoot),
  updateResource: (resourceType, sourcePath, managedRoot) =>
    ipcRenderer.invoke(resourceUpdateChannel, resourceType, sourcePath, managedRoot),
  selectResourceFile: (resourceType) => ipcRenderer.invoke(resourceSelectFileChannel, resourceType),
  listCompletedJobs: (managedRoot) => ipcRenderer.invoke(jobsListCompletedChannel, managedRoot),
  openResultFolder: (jobId) =>
    ipcRenderer.invoke(jobsOpenResultChannel, jobId),
  openLogFolder: (jobId, attemptId) =>
    ipcRenderer.invoke(jobsOpenLogChannel, jobId, attemptId),
  startJob: (jobId, managedRoot, workPath, regenerate) =>
    ipcRenderer.invoke(jobStartChannel, jobId, managedRoot, workPath, regenerate),
  cancelJob: (jobId, attemptId) => ipcRenderer.invoke(jobCancelChannel, jobId, attemptId),
  onJobEvent: (listener) => {
    const wrapper = (_: IpcRendererEvent, event: EngineEvent) => listener(event)
    ipcRenderer.on(jobEventChannel, wrapper)
    return () => ipcRenderer.off(jobEventChannel, wrapper)
  }
}) satisfies DesktopApi
