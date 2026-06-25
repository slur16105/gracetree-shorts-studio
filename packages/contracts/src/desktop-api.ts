import type {
  InputRegistrationResult,
  InputRole,
  JobDto,
  JobInputDto,
} from "./protocol.js";

export const DESKTOP_API_KEY = "desktopApi" as const;

export const JOB_GET_OR_CREATE_CHANNEL = "jobs:get-or-create-for-date" as const;
export const INPUT_SELECT_CHANNEL = "inputs:select-files" as const;
export const INPUT_REGISTER_CHANNEL = "inputs:register-files" as const;
export const INPUT_ASSIGN_ROLE_CHANNEL = "inputs:assign-role" as const;
export const INPUT_REMOVE_CHANNEL = "inputs:remove" as const;
export const INPUT_REPLACE_CHANNEL = "inputs:replace" as const;

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
}
