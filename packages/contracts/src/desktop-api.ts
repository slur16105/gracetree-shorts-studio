import type {
  CompletedJobDto,
  EngineEvent,
  InputRegistrationResult,
  InputRole,
  JobDto,
  JobInputDto,
  ResourceDto,
  ResourceType,
  ScriptValidationDto,
} from "./protocol.js";

export const DESKTOP_API_KEY = "desktopApi" as const;

export const JOB_GET_OR_CREATE_CHANNEL = "jobs:get-or-create-for-date" as const;
export const JOB_START_CHANNEL = "jobs:start" as const;
export const JOB_CANCEL_CHANNEL = "jobs:cancel" as const;
export const JOB_EVENT_CHANNEL = "jobs:event" as const;
export const INPUT_SELECT_CHANNEL = "inputs:select-files" as const;
export const INPUT_REGISTER_CHANNEL = "inputs:register-files" as const;
export const INPUT_ASSIGN_ROLE_CHANNEL = "inputs:assign-role" as const;
export const INPUT_REMOVE_CHANNEL = "inputs:remove" as const;
export const INPUT_REPLACE_CHANNEL = "inputs:replace" as const;
export const SCRIPT_VALIDATE_CHANNEL = "script:validate" as const;
export const RESOURCE_GET_CHANNEL = "resources:get" as const;
export const RESOURCE_UPDATE_CHANNEL = "resources:update" as const;
export const RESOURCE_SELECT_FILE_CHANNEL = "resources:select-file" as const;
export const JOBS_LIST_COMPLETED_CHANNEL = "jobs:list-completed" as const;
export const JOBS_OPEN_RESULT_CHANNEL = "jobs:open-result" as const;

export interface SelectedInputFile {
  name: string;
  sourcePath: string;
}

export interface InputFileCandidate {
  name: string;
  sourcePath?: string;
}

export interface InputRegistrationBatch {
  results: InputRegistrationResult[];
  inputs: JobInputDto[] | null;
}

export interface DesktopApi {
  getOrCreateJobForDate(publishDate: string): Promise<JobDto>;
  selectInputFiles(): Promise<SelectedInputFile[]>;
  registerInputFiles(
    jobId: string,
    files: InputFileCandidate[],
  ): Promise<InputRegistrationBatch>;
  assignInputRole(
    jobId: string,
    inputId: string,
    role: InputRole,
  ): Promise<JobInputDto[]>;
  removeInput(jobId: string, inputId: string): Promise<JobInputDto[]>;
  replaceInput(
    jobId: string,
    inputId: string,
    file: InputFileCandidate,
  ): Promise<JobInputDto[]>;
  validateScript(
    jobId: string,
    inputId: string,
    inputVersion: string,
    managedPath: string,
  ): Promise<ScriptValidationDto>;
  getResources(managedRoot: string): Promise<ResourceDto[]>;
  updateResource(
    resourceType: ResourceType,
    sourcePath: string,
    managedRoot: string,
  ): Promise<ResourceUpdateResult>;
  selectResourceFile(resourceType: ResourceType): Promise<SelectedInputFile | null>;
  listCompletedJobs(managedRoot: string): Promise<CompletedJobSummary[]>;
  openResultFolder(jobId: string, resultPath: string): Promise<void>;
  startJob(jobId: string, managedRoot: string, workPath: string): Promise<void>;
  cancelJob(jobId: string, attemptId: string): Promise<void>;
  onJobEvent(listener: (event: EngineEvent) => void): () => void;
}

export interface ResourceUpdateResult {
  resources: ResourceDto[];
  error: { resourceType: ResourceType; code: string; message: string } | null;
}

export interface CompletedJobSummary extends CompletedJobDto {
  resultExists: boolean;
}

export type { ScriptValidationDto, ResourceDto, ResourceType, CompletedJobDto, EngineEvent };
