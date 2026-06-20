import type { InputRegistrationResult, JobDto } from "./protocol.js";

export const DESKTOP_API_KEY = "desktopApi" as const;

export const JOB_GET_OR_CREATE_CHANNEL = "jobs:get-or-create-for-date" as const;
export const INPUT_SELECT_CHANNEL = "inputs:select-files" as const;
export const INPUT_REGISTER_CHANNEL = "inputs:register-files" as const;

export interface SelectedInputFile {
  name: string;
  sourcePath: string;
}

export interface InputFileCandidate {
  name: string;
  sourcePath?: string;
}

export interface DesktopApi {
  getOrCreateJobForDate(publishDate: string): Promise<JobDto>;
  selectInputFiles(): Promise<SelectedInputFile[]>;
  registerInputFiles(
    jobId: string,
    files: InputFileCandidate[],
  ): Promise<InputRegistrationResult[]>;
}
