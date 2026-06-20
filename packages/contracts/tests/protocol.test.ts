import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  isCheckHealthCommand,
  isGetOrCreateJobCommand,
  isHealthCheckedEvent,
  isInputFilesRegisteredEvent,
  isJobLoadedEvent,
  isRegisterInputFilesCommand,
} from "../src/protocol.js";

function fixture(name: string): unknown {
  const url = new URL(`../fixtures/${name}`, import.meta.url);
  return JSON.parse(readFileSync(fileURLToPath(url), "utf8"));
}

describe("engine protocol schemas", () => {
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
});
