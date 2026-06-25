import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  INPUT_ROLES,
  INPUT_STATES,
  isCheckHealthCommand,
  isCompletedJobsListedEvent,
  isGetOrCreateJobCommand,
  isGetResourcesCommand,
  isHealthCheckedEvent,
  isInputFilesRegisteredEvent,
  isInputStateChangedEvent,
  isJobLoadedEvent,
  isListCompletedJobsCommand,
  isManageInputCommand,
  isRegisterInputFilesCommand,
  isResourceUpdatedEvent,
  isResourcesLoadedEvent,
  isScriptValidatedEvent,
  isUpdateResourceCommand,
  isValidateScriptCommand,
} from "../src/protocol.js";

function fixture(name: string): unknown {
  const url = new URL(`../fixtures/${name}`, import.meta.url);
  return JSON.parse(readFileSync(fileURLToPath(url), "utf8"));
}

describe("engine protocol schemas", () => {
  it("exports explicit input role and state enums", () => {
    expect(INPUT_ROLES).toEqual([
      "thumbnail",
      "voice",
      "bgm",
      "script",
      "unclassified",
    ]);
    expect(INPUT_STATES).toEqual([
      "ready",
      "missing",
      "conflict",
      "unclassified",
      "invalid",
    ]);
  });

  it("accepts the valid command and event fixtures", () => {
    expect(isCheckHealthCommand(fixture("valid-check-health.json"))).toBe(true);
    expect(isHealthCheckedEvent(fixture("valid-health-checked.json"))).toBe(
      true,
    );
    expect(
      isGetOrCreateJobCommand(fixture("valid-get-or-create-job.json")),
    ).toBe(true);
    expect(isJobLoadedEvent(fixture("valid-job-loaded.json"))).toBe(true);
    expect(
      isRegisterInputFilesCommand(fixture("valid-register-input-files.json")),
    ).toBe(true);
    expect(
      isInputFilesRegisteredEvent(fixture("valid-input-files-registered.json")),
    ).toBe(true);
  });

  it.each([
    "invalid-command-missing-job-id.json",
    "invalid-command-wrong-version.json",
    "invalid-command-unknown-type.json",
    "invalid-command-bad-timestamp.json",
    "invalid-command-non-utc-timestamp.json",
  ])("rejects %s", (name) => {
    expect(isCheckHealthCommand(fixture(name))).toBe(false);
  });

  it("rejects invalid dates and job IDs at the engine boundary", () => {
    const command = fixture("valid-get-or-create-job.json") as Record<
      string,
      unknown
    >;
    expect(
      isGetOrCreateJobCommand({
        ...command,
        jobId: "not-a-uuid",
      }),
    ).toBe(false);
    expect(
      isGetOrCreateJobCommand({
        ...command,
        payload: {
          ...(command.payload as Record<string, unknown>),
          publishDate: "2026-02-30",
        },
      }),
    ).toBe(false);
  });

  it("rejects contradictory input registration result states", () => {
    const event = fixture("valid-input-files-registered.json") as Record<
      string,
      unknown
    >;
    const payload = event.payload as {
      results: Array<Record<string, unknown>>;
    };
    const base = payload.results[0];

    expect(
      isInputFilesRegisteredEvent({
        ...event,
        payload: {
          results: [
            {
              ...base,
              status: "registered",
              managedPath: null,
              errorCode: "COPY_FAILED",
            },
          ],
        },
      }),
    ).toBe(false);
    expect(
      isInputFilesRegisteredEvent({
        ...event,
        payload: {
          results: [
            {
              ...base,
              status: "conflict",
              managedPath: "/managed/script.txt",
              errorCode: null,
            },
          ],
        },
      }),
    ).toBe(false);
  });

  it("accepts input management commands and state events", () => {
    const base = {
      protocolVersion: 1,
      type: "manage_input",
      jobId: "11111111-1111-4111-8111-111111111111",
      timestamp: "2026-06-20T00:00:00.000Z",
    };
    expect(
      isManageInputCommand({
        ...base,
        payload: {
          action: "assign_role",
          inputId: "22222222-2222-4222-8222-222222222222",
          role: "voice",
          managedRoot: "/managed",
        },
      }),
    ).toBe(true);
    expect(
      isManageInputCommand({
        ...base,
        payload: {
          action: "remove",
          inputId: "22222222-2222-4222-8222-222222222222",
          managedRoot: "/managed",
        },
      }),
    ).toBe(true);
    expect(
      isManageInputCommand({
        ...base,
        payload: {
          action: "replace",
          inputId: "22222222-2222-4222-8222-222222222222",
          sourcePath: "/source/voice.mp3",
          managedRoot: "/managed",
        },
      }),
    ).toBe(true);
    expect(
      isInputStateChangedEvent({
        protocolVersion: 1,
        type: "input_state_changed",
        jobId: base.jobId,
        timestamp: base.timestamp,
        payload: { inputs: [] },
      }),
    ).toBe(true);
  });

  it("rejects incomplete input management actions", () => {
    expect(
      isManageInputCommand({
        protocolVersion: 1,
        type: "manage_input",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          action: "replace",
          inputId: "22222222-2222-4222-8222-222222222222",
          managedRoot: "/managed",
        },
      }),
    ).toBe(false);
  });

  it("accepts a valid validate_script command", () => {
    expect(
      isValidateScriptCommand({
        protocolVersion: 1,
        type: "validate_script",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          inputId: "22222222-2222-4222-8222-222222222222",
          inputVersion: "abc123",
          managedPath: "/managed/script.txt",
        },
      }),
    ).toBe(true);
  });

  it("rejects validate_script command with missing payload fields", () => {
    expect(
      isValidateScriptCommand({
        protocolVersion: 1,
        type: "validate_script",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          inputId: "22222222-2222-4222-8222-222222222222",
          // inputVersion and managedPath are missing
        },
      }),
    ).toBe(false);
  });

  it("accepts a valid script_validated event", () => {
    expect(
      isScriptValidatedEvent({
        protocolVersion: 1,
        type: "script_validated",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          inputId: "22222222-2222-4222-8222-222222222222",
          inputVersion: "abc123",
          status: "valid",
          oneLiner: "주님의 은혜",
          sections: { title: "제목", scripture: "성경", prayer: "기도" },
          errors: [],
        },
      }),
    ).toBe(true);
  });

  it("accepts a valid get_resources command", () => {
    expect(
      isGetResourcesCommand({
        protocolVersion: 1,
        type: "get_resources",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: { managedRoot: "/managed" },
      }),
    ).toBe(true);
  });

  it("rejects get_resources command with missing managedRoot", () => {
    expect(
      isGetResourcesCommand({
        protocolVersion: 1,
        type: "get_resources",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {},
      }),
    ).toBe(false);
  });

  it("accepts a valid update_resource command", () => {
    expect(
      isUpdateResourceCommand({
        protocolVersion: 1,
        type: "update_resource",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resourceType: "default_bgm",
          sourcePath: "/source/bgm.mp3",
          managedRoot: "/managed",
        },
      }),
    ).toBe(true);
  });

  it("rejects update_resource command with unknown resource type", () => {
    expect(
      isUpdateResourceCommand({
        protocolVersion: 1,
        type: "update_resource",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resourceType: "unknown_type",
          sourcePath: "/source/bgm.mp3",
          managedRoot: "/managed",
        },
      }),
    ).toBe(false);
  });

  it("accepts a valid resources_loaded event", () => {
    expect(
      isResourcesLoadedEvent({
        protocolVersion: 1,
        type: "resources_loaded",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resources: [
            {
              type: "default_bgm",
              managedPath: "/managed/resources/default_bgm.mp3",
              status: "ready",
              updatedAt: "2026-06-20T00:00:00.000Z",
            },
          ],
        },
      }),
    ).toBe(true);
  });

  it("accepts a resources_loaded event with empty resources array", () => {
    expect(
      isResourcesLoadedEvent({
        protocolVersion: 1,
        type: "resources_loaded",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: { resources: [] },
      }),
    ).toBe(true);
  });

  it("accepts a valid resource_updated event with no error", () => {
    expect(
      isResourceUpdatedEvent({
        protocolVersion: 1,
        type: "resource_updated",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resources: [],
          error: null,
        },
      }),
    ).toBe(true);
  });

  it("accepts a valid resource_updated event with an error", () => {
    expect(
      isResourceUpdatedEvent({
        protocolVersion: 1,
        type: "resource_updated",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resources: [],
          error: {
            resourceType: "default_bgm",
            code: "SOURCE_UNREADABLE",
            message: "파일을 읽을 수 없습니다",
          },
        },
      }),
    ).toBe(true);
  });

  it("rejects resource_updated event with unknown resource type in error", () => {
    expect(
      isResourceUpdatedEvent({
        protocolVersion: 1,
        type: "resource_updated",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          resources: [],
          error: {
            resourceType: "unknown_type",
            code: "SOURCE_UNREADABLE",
            message: "오류",
          },
        },
      }),
    ).toBe(false);
  });

  it("rejects script_validated event with invalid error code", () => {
    expect(
      isScriptValidatedEvent({
        protocolVersion: 1,
        type: "script_validated",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-20T00:00:00.000Z",
        payload: {
          inputId: "22222222-2222-4222-8222-222222222222",
          inputVersion: "abc123",
          status: "invalid",
          oneLiner: null,
          sections: { title: null, scripture: null, prayer: null },
          errors: [
            {
              code: "UNKNOWN_CODE",
              section: "title",
              message: "오류 메시지",
            },
          ],
        },
      }),
    ).toBe(false);
  });

  it("accepts a valid list_completed_jobs command", () => {
    expect(
      isListCompletedJobsCommand({
        protocolVersion: 1,
        type: "list_completed_jobs",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: { managedRoot: "/managed" },
      }),
    ).toBe(true);
  });

  it("rejects list_completed_jobs command with missing managedRoot", () => {
    expect(
      isListCompletedJobsCommand({
        protocolVersion: 1,
        type: "list_completed_jobs",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: {},
      }),
    ).toBe(false);
  });

  it("accepts a valid completed_jobs_listed event with jobs", () => {
    expect(
      isCompletedJobsListedEvent({
        protocolVersion: 1,
        type: "completed_jobs_listed",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: {
          jobs: [
            {
              id: "22222222-2222-4222-8222-222222222222",
              publishDate: "2026-06-15",
              title: "주님의 은혜",
              completedAt: "2026-06-15T10:00:00.000Z",
              resultPath: "/managed/jobs/2026-06-15/output",
            },
          ],
        },
      }),
    ).toBe(true);
  });

  it("accepts a valid completed_jobs_listed event with empty jobs array", () => {
    expect(
      isCompletedJobsListedEvent({
        protocolVersion: 1,
        type: "completed_jobs_listed",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: { jobs: [] },
      }),
    ).toBe(true);
  });

  it("accepts a completed_jobs_listed event with null title", () => {
    expect(
      isCompletedJobsListedEvent({
        protocolVersion: 1,
        type: "completed_jobs_listed",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: {
          jobs: [
            {
              id: "22222222-2222-4222-8222-222222222222",
              publishDate: "2026-06-15",
              title: null,
              completedAt: "2026-06-15T10:00:00.000Z",
              resultPath: "/managed/jobs/2026-06-15/output",
            },
          ],
        },
      }),
    ).toBe(true);
  });

  it("rejects completed_jobs_listed event with missing required job field", () => {
    expect(
      isCompletedJobsListedEvent({
        protocolVersion: 1,
        type: "completed_jobs_listed",
        jobId: "11111111-1111-4111-8111-111111111111",
        timestamp: "2026-06-25T00:00:00.000Z",
        payload: {
          jobs: [
            {
              id: "22222222-2222-4222-8222-222222222222",
              publishDate: "2026-06-15",
              title: null,
              // completedAt is missing
              resultPath: "/managed/jobs/2026-06-15/output",
            },
          ],
        },
      }),
    ).toBe(false);
  });
});
