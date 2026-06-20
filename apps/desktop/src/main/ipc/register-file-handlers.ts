import type {
  EngineEvent,
  InputRegistrationResult,
  RegisterInputFilesCommand
} from '@gracetree/contracts'
import { isInputFilesRegisteredEvent } from '@gracetree/contracts'
import {
  INPUT_REGISTER_CHANNEL,
  INPUT_SELECT_CHANNEL,
  type SelectedInputFile
} from '@gracetree/contracts/desktop-api'
import { ipcMain } from 'electron'
import { isAbsolute } from 'node:path'

import { isValidJobId } from '../files/managed-paths'
import { selectInputFiles } from '../files/file-dialogs'

type RequestEngine = (command: RegisterInputFilesCommand) => Promise<EngineEvent>

export function createRegisterInputFilesHandler(
  managedRoot: string,
  requestEngine: RequestEngine
): (jobId: string, files: SelectedInputFile[]) => Promise<InputRegistrationResult[]> {
  return async (jobId, files) => {
    if (!isValidJobId(jobId)) throw new Error('Job ID is invalid')
    if (!Array.isArray(files) || files.length === 0 || files.length > 100) {
      throw new Error('Input batch must contain between 1 and 100 files')
    }
    const results: Array<InputRegistrationResult | undefined> = new Array(files.length)
    const validPaths: string[] = []
    const validIndexes: number[] = []
    files.forEach((file, index) => {
      if (
        typeof file?.name !== 'string' ||
        typeof file?.sourcePath !== 'string' ||
        !isAbsolute(file.sourcePath)
      ) {
        results[index] = {
          originalName: typeof file?.name === 'string' ? file.name : '알 수 없는 파일',
          managedPath: null,
          role: 'unclassified',
          status: 'rejected',
          errorCode: 'SOURCE_UNREADABLE'
        }
      } else {
        validPaths.push(file.sourcePath)
        validIndexes.push(index)
      }
    })
    if (validPaths.length === 0) return results.filter(Boolean) as InputRegistrationResult[]
    const command: RegisterInputFilesCommand = {
      protocolVersion: 1,
      type: 'register_input_files',
      jobId,
      timestamp: new Date().toISOString(),
      payload: { sourcePaths: validPaths, managedRoot }
    }
    const event = await requestEngine(command)
    if (!isInputFilesRegisteredEvent(event) || event.jobId !== jobId) {
      throw new Error('Python engine response is invalid')
    }
    if (event.payload.results.length !== validPaths.length) {
      throw new Error('Python engine returned a mismatched batch')
    }
    event.payload.results.forEach((result, index) => {
      const targetIndex = validIndexes[index]
      if (targetIndex !== undefined) results[targetIndex] = result
    })
    if (results.some((result) => result === undefined)) {
      throw new Error('Python engine returned an incomplete batch')
    }
    return results as InputRegistrationResult[]
  }
}

export function registerFileHandlers(managedRoot: string, requestEngine: RequestEngine): void {
  const register = createRegisterInputFilesHandler(managedRoot, requestEngine)
  ipcMain.handle(INPUT_SELECT_CHANNEL, () => selectInputFiles())
  ipcMain.handle(INPUT_REGISTER_CHANNEL, (_event, jobId: unknown, files: unknown) => {
    if (typeof jobId !== 'string' || !Array.isArray(files)) {
      throw new Error('Input registration request is invalid')
    }
    return register(jobId, files as SelectedInputFile[])
  })
}
