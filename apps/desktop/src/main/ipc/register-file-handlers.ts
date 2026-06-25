import type {
  EngineEvent,
  InputRegistrationResult,
  InputRole,
  JobInputDto,
  ManageInputCommand,
  RegisterInputFilesCommand,
  ScriptValidationDto,
  ValidateScriptCommand
} from '@gracetree/contracts'
import {
  INPUT_ROLES,
  isInputFilesRegisteredEvent,
  isInputStateChangedEvent,
  isScriptValidatedEvent
} from '@gracetree/contracts'
import {
  INPUT_ASSIGN_ROLE_CHANNEL,
  INPUT_REGISTER_CHANNEL,
  INPUT_REMOVE_CHANNEL,
  INPUT_REPLACE_CHANNEL,
  INPUT_SELECT_CHANNEL,
  SCRIPT_VALIDATE_CHANNEL,
  type InputRegistrationBatch,
  type SelectedInputFile
} from '@gracetree/contracts/desktop-api'
import { ipcMain } from 'electron'
import { isAbsolute } from 'node:path'

import { isValidJobId } from '../files/managed-paths'
import { selectInputFiles } from '../files/file-dialogs'

type RequestEngine = (command: RegisterInputFilesCommand) => Promise<EngineEvent>
type ManageRequestEngine = (command: ManageInputCommand) => Promise<EngineEvent>
type ValidateScriptRequestEngine = (command: ValidateScriptCommand) => Promise<EngineEvent>
type ManageInputRequest =
  | { action: 'assign_role'; inputId: string; role: InputRole }
  | { action: 'remove'; inputId: string }
  | { action: 'replace'; inputId: string; sourcePath: string }

export function createRegisterInputFilesHandler(
  managedRoot: string,
  requestEngine: RequestEngine
): (jobId: string, files: SelectedInputFile[]) => Promise<InputRegistrationBatch> {
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
    if (validPaths.length === 0) {
      return { results: results.filter(Boolean) as InputRegistrationResult[], inputs: null }
    }
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
    return { results: results as InputRegistrationResult[], inputs: event.payload.inputs }
  }
}

export function createManageInputHandler(
  managedRoot: string,
  requestEngine: ManageRequestEngine
): (jobId: string, request: ManageInputRequest) => Promise<JobInputDto[]> {
  return async (jobId, request) => {
    if (!isValidJobId(jobId)) throw new Error('Job ID is invalid')
    if (!isValidJobId(request.inputId)) throw new Error('Input ID is invalid')
    if (request.action === 'assign_role' && !INPUT_ROLES.includes(request.role)) {
      throw new Error('Input role is invalid')
    }
    if (request.action === 'replace' && !isAbsolute(request.sourcePath)) {
      throw new Error('Replacement path is invalid')
    }
    const command: ManageInputCommand = {
      protocolVersion: 1,
      type: 'manage_input',
      jobId,
      timestamp: new Date().toISOString(),
      payload: { ...request, managedRoot }
    }
    const event = await requestEngine(command)
    if (!isInputStateChangedEvent(event) || event.jobId !== jobId) {
      throw new Error('Python engine response is invalid')
    }
    return event.payload.inputs
  }
}

export function createValidateScriptHandler(
  requestEngine: ValidateScriptRequestEngine
): (jobId: string, inputId: string, inputVersion: string, managedPath: string) => Promise<ScriptValidationDto> {
  return async (jobId, inputId, inputVersion, managedPath) => {
    if (!isValidJobId(jobId)) throw new Error('Job ID is invalid')
    if (!isValidJobId(inputId)) throw new Error('Input ID is invalid')
    const command: ValidateScriptCommand = {
      protocolVersion: 1,
      type: 'validate_script',
      jobId,
      timestamp: new Date().toISOString(),
      payload: { inputId, inputVersion, managedPath }
    }
    const event = await requestEngine(command)
    if (!isScriptValidatedEvent(event) || event.jobId !== jobId) {
      throw new Error('Python engine response is invalid')
    }
    return event.payload
  }
}

export function registerFileHandlers(
  managedRoot: string,
  requestEngine: RequestEngine & ManageRequestEngine & ValidateScriptRequestEngine
): void {
  const register = createRegisterInputFilesHandler(managedRoot, requestEngine)
  const manage = createManageInputHandler(managedRoot, requestEngine)
  const validateScript = createValidateScriptHandler(requestEngine)
  ipcMain.handle(INPUT_SELECT_CHANNEL, () => selectInputFiles())
  ipcMain.handle(INPUT_REGISTER_CHANNEL, (_event, jobId: unknown, files: unknown) => {
    if (typeof jobId !== 'string' || !Array.isArray(files)) {
      throw new Error('Input registration request is invalid')
    }
    return register(jobId, files as SelectedInputFile[])
  })
  ipcMain.handle(
    INPUT_ASSIGN_ROLE_CHANNEL,
    (_event, jobId: unknown, inputId: unknown, role: unknown) => {
      if (typeof jobId !== 'string' || typeof inputId !== 'string' || typeof role !== 'string') {
        throw new Error('Input role request is invalid')
      }
      return manage(jobId, { action: 'assign_role', inputId, role: role as InputRole })
    }
  )
  ipcMain.handle(INPUT_REMOVE_CHANNEL, (_event, jobId: unknown, inputId: unknown) => {
    if (typeof jobId !== 'string' || typeof inputId !== 'string') {
      throw new Error('Input remove request is invalid')
    }
    return manage(jobId, { action: 'remove', inputId })
  })
  ipcMain.handle(
    INPUT_REPLACE_CHANNEL,
    (_event, jobId: unknown, inputId: unknown, file: unknown) => {
      if (
        typeof jobId !== 'string' ||
        typeof inputId !== 'string' ||
        typeof (file as SelectedInputFile | undefined)?.sourcePath !== 'string'
      ) {
        throw new Error('Input replacement request is invalid')
      }
      return manage(jobId, {
        action: 'replace',
        inputId,
        sourcePath: (file as SelectedInputFile).sourcePath
      })
    }
  )
  ipcMain.handle(
    SCRIPT_VALIDATE_CHANNEL,
    (_event, jobId: unknown, inputId: unknown, inputVersion: unknown, managedPath: unknown) => {
      if (
        typeof jobId !== 'string' ||
        typeof inputId !== 'string' ||
        typeof inputVersion !== 'string' ||
        typeof managedPath !== 'string'
      ) {
        throw new Error('Script validation request is invalid')
      }
      return validateScript(jobId, inputId, inputVersion, managedPath)
    }
  )
}
