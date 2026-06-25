import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  INPUT_ROLES,
  INPUT_STATES,
  isCheckHealthCommand,
  isGetOrCreateJobCommand,
  isHealthCheckedEvent,
  isInputFilesRegisteredEvent,
  isInputStateChangedEvent,
  isJobLoadedEvent,
  isManageInputCommand,
  isRegisterInputFilesCommand,
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
});
