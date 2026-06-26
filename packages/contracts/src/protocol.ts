import { Ajv2020, type ErrorObject } from "ajv/dist/2020.js";
import * as addFormatsModule from "ajv-formats";
import type { FormatsPlugin } from "ajv-formats";

import commandSchema from "../schemas/engine-command.schema.json" with { type: "json" };
import eventSchema from "../schemas/engine-event.schema.json" with { type: "json" };

export const INPUT_ROLES = [
  "thumbnail",
  "voice",
  "bgm",
  "script",
  "unclassified",
] as const;
export type InputRole = (typeof INPUT_ROLES)[number];

export const INPUT_STATES = [
  "ready",
  "missing",
  "conflict",
  "unclassified",
  "invalid",
] as const;
export type InputState = (typeof INPUT_STATES)[number];

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
  role: InputRole;
  originalName: string;
  managedPath: string;
  status: Exclude<InputState, "missing">;
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

interface InputRegistrationResultBase {
  originalName: string;
  role: InputRole;
}

export interface RegisteredInputResult extends InputRegistrationResultBase {
  input: JobInputDto;
  managedPath: string;
  status: "registered";
  errorCode: null;
}

export interface RejectedInputResult extends InputRegistrationResultBase {
  managedPath: null;
  status: "rejected";
  errorCode:
    | "UNSUPPORTED_TYPE"
    | "SOURCE_UNREADABLE"
    | "SOURCE_INSIDE_MANAGED_ROOT"
    | "SYMLINK_NOT_ALLOWED"
    | "FILE_TOO_LARGE"
    | "COPY_FAILED";
}

export interface ConflictingInputResult extends InputRegistrationResultBase {
  managedPath: string;
  status: "conflict";
  errorCode: "NAME_CONFLICT";
}

export type InputRegistrationResult =
  | RegisteredInputResult
  | RejectedInputResult
  | ConflictingInputResult;

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
    inputs: JobInputDto[];
  };
}

export type ManageInputCommand = {
  protocolVersion: 1;
  type: "manage_input";
  jobId: string;
  timestamp: string;
  payload:
    | {
        action: "assign_role";
        inputId: string;
        role: InputRole;
        managedRoot: string;
      }
    | {
        action: "remove";
        inputId: string;
        managedRoot: string;
      }
    | {
        action: "replace";
        inputId: string;
        sourcePath: string;
        managedRoot: string;
      };
};

export interface InputStateChangedEvent {
  protocolVersion: 1;
  type: "input_state_changed";
  jobId: string;
  timestamp: string;
  payload: {
    inputs: JobInputDto[];
  };
}

export const SCRIPT_ERROR_CODES = [
  "FILE_UNREADABLE",
  "FILE_EMPTY",
  "SECTION_MISSING",
  "SECTION_EMPTY",
  "SECTION_DUPLICATE",
] as const;
export type ScriptErrorCode = (typeof SCRIPT_ERROR_CODES)[number];

export const SCRIPT_SECTIONS = ["title", "scripture", "prayer"] as const;
export type ScriptSection = (typeof SCRIPT_SECTIONS)[number];

export interface ScriptSectionError {
  code: ScriptErrorCode;
  section: ScriptSection | null;
  message: string;
}

export interface SubtitleBlockDto {
  index: number;
  text: string;
  lines: string[];
}

export interface ScriptAstDto {
  title: string;
  scripture: string;
  subtitleBlocks: SubtitleBlockDto[];
}

export interface ScriptValidationDto {
  inputId: string;
  inputVersion: string;
  status: "valid" | "invalid";
  oneLiner: string | null;
  sections: {
    title: string | null;
    scripture: string | null;
    prayer: string | null;
  };
  errors: ScriptSectionError[];
  ast?: ScriptAstDto | null;
}

export interface ValidateScriptCommand {
  protocolVersion: 1;
  type: "validate_script";
  jobId: string;
  timestamp: string;
  payload: {
    inputId: string;
    inputVersion: string;
    managedPath: string;
  };
}

export interface ScriptValidatedEvent {
  protocolVersion: 1;
  type: "script_validated";
  jobId: string;
  timestamp: string;
  payload: ScriptValidationDto;
}

// ── Story 2.1: Generation vertical slice ─────────────────────────────────

export const GENERATION_STAGES = [
  "speech_alignment",
  "vertical_slice",
] as const;
export type GenerationStage = (typeof GENERATION_STAGES)[number];

export interface StartJobCommand {
  protocolVersion: 1;
  type: "start_job";
  jobId: string;
  timestamp: string;
  payload: {
    managedRoot: string;
    workPath: string;
  };
}

export interface JobAcceptedEvent {
  protocolVersion: 1;
  type: "job_accepted";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
  };
}

export interface StageStartedEvent {
  protocolVersion: 1;
  type: "stage_started";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
    stageId: GenerationStage;
    stageName: string;
  };
}

export interface ProgressEvent {
  protocolVersion: 1;
  type: "progress";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
    stageId: GenerationStage;
    percent: number;
  };
}

export interface ArtifactCreatedEvent {
  protocolVersion: 1;
  type: "artifact_created";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
    artifactPath: string;
    artifactName: string;
  };
}

export interface JobCompletedEvent {
  protocolVersion: 1;
  type: "job_completed";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
    artifactPath: string;
    artifactName: string;
  };
}

export interface JobFailedEvent {
  protocolVersion: 1;
  type: "job_failed";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
    errorCode: string;
    stageId: GenerationStage | null;
    recoverable: boolean;
    details: string | null;
  };
}

export interface CancelJobCommand {
  protocolVersion: 1;
  type: "cancel_job";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
  };
}

export interface JobCancelledEvent {
  protocolVersion: 1;
  type: "job_cancelled";
  jobId: string;
  timestamp: string;
  payload: {
    attemptId: string;
  };
}

export type EngineCommand =
  | CheckHealthCommand
  | GetOrCreateJobCommand
  | RegisterInputFilesCommand
  | ManageInputCommand
  | ValidateScriptCommand
  | GetResourcesCommand
  | UpdateResourceCommand
  | ListCompletedJobsCommand
  | StartJobCommand
  | CancelJobCommand;
export type EngineEvent =
  | HealthCheckedEvent
  | JobLoadedEvent
  | InputFilesRegisteredEvent
  | InputStateChangedEvent
  | ScriptValidatedEvent
  | ResourcesLoadedEvent
  | ResourceUpdatedEvent
  | CompletedJobsListedEvent
  | JobAcceptedEvent
  | StageStartedEvent
  | ProgressEvent
  | ArtifactCreatedEvent
  | JobCompletedEvent
  | JobFailedEvent
  | JobCancelledEvent;

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

export function isManageInputCommand(
  value: unknown,
): value is ManageInputCommand {
  return validateCommand(value) && value.type === "manage_input";
}

export function isInputStateChangedEvent(
  value: unknown,
): value is InputStateChangedEvent {
  return validateEvent(value) && value.type === "input_state_changed";
}

// ── Story 1.7: Common resources ──────────────────────────────────────────

export const RESOURCE_TYPES = [
  "title_scripture_video",
  "prayer_loop_video",
  "default_bgm",
  "subtitle_font",
] as const;
export type ResourceType = (typeof RESOURCE_TYPES)[number];

export const RESOURCE_STATUSES = ["ready", "missing", "invalid"] as const;
export type ResourceStatus = (typeof RESOURCE_STATUSES)[number];

export interface ResourceDto {
  type: ResourceType;
  managedPath: string | null;
  status: ResourceStatus;
  updatedAt: string;
}

export interface GetResourcesCommand {
  protocolVersion: 1;
  type: "get_resources";
  jobId: string;
  timestamp: string;
  payload: { managedRoot: string };
}

export interface UpdateResourceCommand {
  protocolVersion: 1;
  type: "update_resource";
  jobId: string;
  timestamp: string;
  payload: {
    resourceType: ResourceType;
    sourcePath: string;
    managedRoot: string;
  };
}

export interface ResourcesLoadedEvent {
  protocolVersion: 1;
  type: "resources_loaded";
  jobId: string;
  timestamp: string;
  payload: { resources: ResourceDto[] };
}

export interface ResourceUpdatedEvent {
  protocolVersion: 1;
  type: "resource_updated";
  jobId: string;
  timestamp: string;
  payload: {
    resources: ResourceDto[];
    error: {
      resourceType: ResourceType;
      code: string;
      message: string;
    } | null;
  };
}

// ── Story 4.1: Completed jobs list ───────────────────────────────────────

export interface CompletedJobDto {
  id: string;
  publishDate: string;
  title: string | null;
  completedAt: string;
  resultPath: string;
}

export interface ListCompletedJobsCommand {
  protocolVersion: 1;
  type: "list_completed_jobs";
  jobId: string;
  timestamp: string;
  payload: { managedRoot: string };
}

export interface CompletedJobsListedEvent {
  protocolVersion: 1;
  type: "completed_jobs_listed";
  jobId: string;
  timestamp: string;
  payload: { jobs: CompletedJobDto[] };
}

export function isValidateScriptCommand(
  value: unknown,
): value is ValidateScriptCommand {
  return validateCommand(value) && value.type === "validate_script";
}

export function isScriptValidatedEvent(
  value: unknown,
): value is ScriptValidatedEvent {
  return validateEvent(value) && value.type === "script_validated";
}

export function isGetResourcesCommand(
  value: unknown,
): value is GetResourcesCommand {
  return validateCommand(value) && value.type === "get_resources";
}

export function isUpdateResourceCommand(
  value: unknown,
): value is UpdateResourceCommand {
  return validateCommand(value) && value.type === "update_resource";
}

export function isResourcesLoadedEvent(
  value: unknown,
): value is ResourcesLoadedEvent {
  return validateEvent(value) && value.type === "resources_loaded";
}

export function isResourceUpdatedEvent(
  value: unknown,
): value is ResourceUpdatedEvent {
  return validateEvent(value) && value.type === "resource_updated";
}

export function isListCompletedJobsCommand(
  value: unknown,
): value is ListCompletedJobsCommand {
  return validateCommand(value) && value.type === "list_completed_jobs";
}

export function isCompletedJobsListedEvent(
  value: unknown,
): value is CompletedJobsListedEvent {
  return validateEvent(value) && value.type === "completed_jobs_listed";
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

// ── Story 2.1: Generation event guards ───────────────────────────────────

export function isStartJobCommand(value: unknown): value is StartJobCommand {
  return validateCommand(value) && value.type === "start_job";
}

export function isCancelJobCommand(value: unknown): value is CancelJobCommand {
  return validateCommand(value) && value.type === "cancel_job";
}

export function isJobAcceptedEvent(value: unknown): value is JobAcceptedEvent {
  return validateEvent(value) && value.type === "job_accepted";
}

export function isStageStartedEvent(value: unknown): value is StageStartedEvent {
  return validateEvent(value) && value.type === "stage_started";
}

export function isProgressEvent(value: unknown): value is ProgressEvent {
  return validateEvent(value) && value.type === "progress";
}

export function isArtifactCreatedEvent(value: unknown): value is ArtifactCreatedEvent {
  return validateEvent(value) && value.type === "artifact_created";
}

export function isJobCompletedEvent(value: unknown): value is JobCompletedEvent {
  return validateEvent(value) && value.type === "job_completed";
}

export function isJobFailedEvent(value: unknown): value is JobFailedEvent {
  return validateEvent(value) && value.type === "job_failed";
}

export function isJobCancelledEvent(value: unknown): value is JobCancelledEvent {
  return validateEvent(value) && value.type === "job_cancelled";
}

export function isGenerationEvent(
  value: unknown,
): value is JobAcceptedEvent | StageStartedEvent | ProgressEvent | ArtifactCreatedEvent | JobCompletedEvent | JobFailedEvent | JobCancelledEvent {
  if (!isEngineEvent(value)) return false;
  return (
    value.type === "job_accepted" ||
    value.type === "stage_started" ||
    value.type === "progress" ||
    value.type === "artifact_created" ||
    value.type === "job_completed" ||
    value.type === "job_failed" ||
    value.type === "job_cancelled"
  );
}
