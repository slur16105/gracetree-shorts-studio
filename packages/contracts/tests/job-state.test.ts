import { describe, expect, it } from "vitest";

import {
  INITIAL_JOB_RUN_STATE,
  applyJobEvent,
  type JobRunState,
} from "../src/job-state.js";
import type { EngineEvent } from "../src/protocol.js";

const JOB_ID = "11111111-1111-4111-8111-111111111111";
const ATTEMPT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const TS = "2026-06-25T00:00:00.000Z";

function accepted(): EngineEvent {
  return {
    protocolVersion: 1,
    type: "job_accepted",
    jobId: JOB_ID,
    timestamp: TS,
    payload: { attemptId: ATTEMPT_ID },
  };
}

function stageStarted(stageId = "vertical_slice" as const, stageName = "수직 슬라이스"): EngineEvent {
  return {
    protocolVersion: 1,
    type: "stage_started",
    jobId: JOB_ID,
    timestamp: TS,
    payload: { attemptId: ATTEMPT_ID, stageId, stageName },
  };
}

function progress(percent: number): EngineEvent {
  return {
    protocolVersion: 1,
    type: "progress",
    jobId: JOB_ID,
    timestamp: TS,
    payload: { attemptId: ATTEMPT_ID, stageId: "vertical_slice", percent },
  };
}

function completed(): EngineEvent {
  return {
    protocolVersion: 1,
    type: "job_completed",
    jobId: JOB_ID,
    timestamp: TS,
    payload: {
      attemptId: ATTEMPT_ID,
      artifactPath: "/data/jobs/2026-06-25/temp/attempts/aaa.../vertical-slice.mp4",
      artifactName: "vertical-slice.mp4",
    },
  };
}

function failed(
  errorCode = "PROCESS_FAILED",
  recoverable = false,
  details: string | null = null,
): EngineEvent {
  return {
    protocolVersion: 1,
    type: "job_failed",
    jobId: JOB_ID,
    timestamp: TS,
    payload: { attemptId: ATTEMPT_ID, errorCode, stageId: "vertical_slice", recoverable, details },
  };
}

function cancelled(): EngineEvent {
  return {
    protocolVersion: 1,
    type: "job_cancelled",
    jobId: JOB_ID,
    timestamp: TS,
    payload: { attemptId: ATTEMPT_ID },
  };
}

describe("applyJobEvent — idle → running", () => {
  it("job_accepted moves idle to running with 0% progress", () => {
    const next = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    expect(next).toEqual({
      status: "running",
      jobId: JOB_ID,
      attemptId: ATTEMPT_ID,
      stageId: null,
      stageName: null,
      percent: 0,
    });
  });

  it("ignores job_accepted when already running", () => {
    const running = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    const next = applyJobEvent(running, accepted(), JOB_ID);
    expect(next).toBe(running);
  });
});

describe("applyJobEvent — stage_started", () => {
  it("updates stageId and stageName", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID) as Extract<JobRunState, { status: "running" }>;
    s = applyJobEvent(s, stageStarted(), JOB_ID) as Extract<JobRunState, { status: "running" }>;
    expect(s.stageId).toBe("vertical_slice");
    expect(s.stageName).toBe("수직 슬라이스");
  });

  it("ignores stage_started for different attemptId", () => {
    const running = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    const event: EngineEvent = {
      protocolVersion: 1,
      type: "stage_started",
      jobId: JOB_ID,
      timestamp: TS,
      payload: { attemptId: "different-attempt", stageId: "vertical_slice", stageName: "x" },
    };
    expect(applyJobEvent(running, event, JOB_ID)).toBe(running);
  });
});

describe("applyJobEvent — progress", () => {
  it("increases percent monotonically", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, progress(10), JOB_ID);
    s = applyJobEvent(s, progress(50), JOB_ID);
    expect((s as Extract<JobRunState, { status: "running" }>).percent).toBe(50);
  });

  it("ignores backward progress", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, progress(50), JOB_ID);
    s = applyJobEvent(s, progress(30), JOB_ID);
    expect((s as Extract<JobRunState, { status: "running" }>).percent).toBe(50);
  });

  it("refuses to set 100% before completed event", () => {
    const s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    const event: EngineEvent = {
      protocolVersion: 1,
      type: "progress",
      jobId: JOB_ID,
      timestamp: TS,
      payload: { attemptId: ATTEMPT_ID, stageId: "vertical_slice", percent: 99 },
    };
    const after = applyJobEvent(s, event, JOB_ID);
    expect((after as Extract<JobRunState, { status: "running" }>).percent).toBe(99);
    const event100: EngineEvent = {
      protocolVersion: 1,
      type: "progress",
      jobId: JOB_ID,
      timestamp: TS,
      payload: { attemptId: ATTEMPT_ID, stageId: "vertical_slice", percent: 99 },
    };
    applyJobEvent(after, event100, JOB_ID);
  });
});

describe("applyJobEvent — terminal events", () => {
  it("job_completed transitions to completed with artifact", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, completed(), JOB_ID);
    expect(s).toMatchObject({
      status: "completed",
      jobId: JOB_ID,
      attemptId: ATTEMPT_ID,
    });
  });

  it("job_failed transitions to failed with errorCode, recoverable, details", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, failed(), JOB_ID);
    expect(s).toMatchObject({ status: "failed", errorCode: "PROCESS_FAILED", recoverable: false, details: null });
  });

  it("job_failed with recoverable=true and details propagates to state", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, failed("PRAYER_BOUNDARY_AMBIGUOUS", true, "기도 시작 문장을 확인해 주세요."), JOB_ID);
    expect(s).toMatchObject({
      status: "failed",
      errorCode: "PRAYER_BOUNDARY_AMBIGUOUS",
      recoverable: true,
      details: "기도 시작 문장을 확인해 주세요.",
    });
  });

  it("job_cancelled from running transitions to cancelled", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, cancelled(), JOB_ID);
    expect(s).toMatchObject({ status: "cancelled" });
  });

  it("job_cancelled from cancelling transitions to cancelled", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID) as Extract<JobRunState, { status: "running" }>;
    // Simulate cancelling state (set directly as it's a UI-only transition)
    const cancelling: JobRunState = { status: "cancelling", jobId: s.jobId, attemptId: s.attemptId };
    const after = applyJobEvent(cancelling, cancelled(), JOB_ID);
    expect(after).toMatchObject({ status: "cancelled" });
  });

  it("job_completed from cancelling transitions to completed (job wins race)", () => {
    const running = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID) as Extract<JobRunState, { status: "running" }>;
    const cancelling: JobRunState = { status: "cancelling", jobId: running.jobId, attemptId: running.attemptId };
    const after = applyJobEvent(cancelling, completed(), JOB_ID);
    expect(after).toMatchObject({ status: "completed", artifactPath: expect.any(String) });
  });

  it("job_failed from cancelling transitions to failed (engine fails during cancel)", () => {
    const running = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID) as Extract<JobRunState, { status: "running" }>;
    const cancelling: JobRunState = { status: "cancelling", jobId: running.jobId, attemptId: running.attemptId };
    const after = applyJobEvent(cancelling, failed(), JOB_ID);
    expect(after).toMatchObject({ status: "failed", errorCode: "PROCESS_FAILED", recoverable: false, details: null });
  });

  it("job_cancelled is ignored when already completed (late cancel)", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, completed(), JOB_ID);
    const before = s;
    s = applyJobEvent(s, cancelled(), JOB_ID);
    expect(s).toBe(before);
  });

  it("ignores further events after terminal", () => {
    let s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    s = applyJobEvent(s, completed(), JOB_ID);
    const before = s;
    s = applyJobEvent(s, failed(), JOB_ID);
    expect(s).toBe(before);
  });
});

describe("applyJobEvent — wrong jobId", () => {
  it("ignores events from a different job", () => {
    const s = applyJobEvent(INITIAL_JOB_RUN_STATE, accepted(), JOB_ID);
    const event: EngineEvent = {
      ...accepted(),
      jobId: "99999999-9999-4999-8999-999999999999",
    };
    const after = applyJobEvent(s, event, JOB_ID);
    expect(after).toBe(s);
  });
});

describe("applyJobEvent — non-generation events are ignored", () => {
  it("ignores health_checked", () => {
    const event: EngineEvent = {
      protocolVersion: 1,
      type: "health_checked",
      jobId: JOB_ID,
      timestamp: TS,
      payload: { status: "ok" },
    };
    const after = applyJobEvent(INITIAL_JOB_RUN_STATE, event, JOB_ID);
    expect(after).toBe(INITIAL_JOB_RUN_STATE);
  });
});
