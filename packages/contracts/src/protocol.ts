import { Ajv2020, type ErrorObject } from "ajv/dist/2020.js";
import * as addFormatsModule from "ajv-formats";
import type { FormatsPlugin } from "ajv-formats";

import commandSchema from "../schemas/engine-command.schema.json" with { type: "json" };
import eventSchema from "../schemas/engine-event.schema.json" with { type: "json" };

export interface CheckHealthCommand {
  protocolVersion: 1;
  type: "check_health";
  jobId: string;
  timestamp: string;
  payload: Record<string, never>;
}

export interface HealthCheckedEvent {
  protocolVersion: 1;
  type: "health_checked";
  jobId: string;
  timestamp: string;
  payload: {
    status: "ok";
  };
}

export interface JobDto {
  id: string;
  publishDate: string;
  status:
    | "draft"
    | "running"
    | "completed"
    | "failed"
    | "cancelled"
    | "interrupted";
  title: string | null;
  workPath: string;
  resultPath: string;
  createdAt: string;
  updatedAt: string;
  pathState: "ready" | "missing";
  inputMetadata: JobInputDto[];
}

export interface JobInputDto {
  id: string;
  jobId: string;
  role: "unclassified";
  originalName: string;
  managedPath: string;
  status: "registered" | "conflict";
  createdAt: string;
  updatedAt: string;
}

export interface GetOrCreateJobCommand {
  protocolVersion: 1;
  type: "get_or_create_job";
  jobId: string;
  timestamp: string;
  payload: {
    publishDate: string;
    managedRoot: string;
    workPath: string;
  };
}

export interface JobLoadedEvent {
  protocolVersion: 1;
  type: "job_loaded";
  jobId: string;
  timestamp: string;
  payload: {
    job: JobDto;
  };
}

export type InputRegistrationStatus = "registered" | "rejected" | "conflict";

export interface InputRegistrationResult {
  input?: JobInputDto;
  originalName: string;
  managedPath: string | null;
  role: "unclassified";
  status: InputRegistrationStatus;
  errorCode:
    | "UNSUPPORTED_TYPE"
    | "SOURCE_UNREADABLE"
    | "SOURCE_INSIDE_MANAGED_ROOT"
    | "SYMLINK_NOT_ALLOWED"
    | "FILE_TOO_LARGE"
    | "NAME_CONFLICT"
    | "COPY_FAILED"
    | null;
}

export interface RegisterInputFilesCommand {
  protocolVersion: 1;
  type: "register_input_files";
  jobId: string;
  timestamp: string;
  payload: {
    sourcePaths: string[];
    managedRoot: string;
  };
}

export interface InputFilesRegisteredEvent {
  protocolVersion: 1;
  type: "input_files_registered";
  jobId: string;
  timestamp: string;
  payload: {
    results: InputRegistrationResult[];
  };
}

export type EngineCommand =
  | CheckHealthCommand
  | GetOrCreateJobCommand
  | RegisterInputFilesCommand;
export type EngineEvent =
  | HealthCheckedEvent
  | JobLoadedEvent
  | InputFilesRegisteredEvent;

const ajv = new Ajv2020({ allErrors: true, strict: true });
const addFormats = (addFormatsModule.default ??
  addFormatsModule) as unknown as FormatsPlugin;
addFormats(ajv);

const validateCommand = ajv.compile<EngineCommand>(commandSchema);
const validateEvent = ajv.compile<EngineEvent>(eventSchema);

export function isCheckHealthCommand(
  value: unknown,
): value is CheckHealthCommand {
  return validateCommand(value) && value.type === "check_health";
}

export function isHealthCheckedEvent(
  value: unknown,
): value is HealthCheckedEvent {
  return validateEvent(value) && value.type === "health_checked";
}

export function isGetOrCreateJobCommand(
  value: unknown,
): value is GetOrCreateJobCommand {
  return validateCommand(value) && value.type === "get_or_create_job";
}

export function isJobLoadedEvent(value: unknown): value is JobLoadedEvent {
  return validateEvent(value) && value.type === "job_loaded";
}

export function isRegisterInputFilesCommand(
  value: unknown,
): value is RegisterInputFilesCommand {
  return validateCommand(value) && value.type === "register_input_files";
}

export function isInputFilesRegisteredEvent(
  value: unknown,
): value is InputFilesRegisteredEvent {
  return validateEvent(value) && value.type === "input_files_registered";
}

export function isEngineEvent(value: unknown): value is EngineEvent {
  return validateEvent(value);
}

export function commandValidationErrors(): ErrorObject[] | null | undefined {
  return validateCommand.errors;
}

export function eventValidationErrors(): ErrorObject[] | null | undefined {
  return validateEvent.errors;
}
