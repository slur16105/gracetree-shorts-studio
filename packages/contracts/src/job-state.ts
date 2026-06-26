import { isGenerationEvent } from "./protocol.js";
import type { EngineEvent } from "./protocol.js";

export type JobRunState =
  | { status: "idle" }
  | {
      status: "running";
      jobId: string;
      attemptId: string;
      stageId: string | null;
      stageName: string | null;
      percent: number;
    }
  | {
      status: "cancelling";
      jobId: string;
      attemptId: string;
    }
  | {
      status: "completed";
      jobId: string;
      attemptId: string;
      artifactPath: string;
      artifactName: string;
    }
  | {
      status: "failed";
      jobId: string;
      attemptId: string;
      errorCode: string;
      stageId: string | null;
      recoverable: boolean;
      details: string | null;
    }
  | {
      status: "cancelled";
      jobId: string;
      attemptId: string;
    };

export const INITIAL_JOB_RUN_STATE: JobRunState = { status: "idle" };

export function applyJobEvent(
  state: JobRunState,
  event: EngineEvent,
  currentJobId: string,
): JobRunState {
  if (!isGenerationEvent(event)) return state;
  if (event.jobId !== currentJobId) return state;

  switch (event.type) {
    case "job_accepted": {
      if (
        state.status !== "idle" &&
        state.status !== "completed" &&
        state.status !== "failed" &&
        state.status !== "cancelled"
      ) return state;
      return {
        status: "running",
        jobId: event.jobId,
        attemptId: event.payload.attemptId,
        stageId: null,
        stageName: null,
        percent: 0,
      };
    }

    case "stage_started": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      if (state.status !== "running") return state;
      return {
        ...state,
        stageId: event.payload.stageId,
        stageName: event.payload.stageName,
      };
    }

    case "progress": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      if (state.status !== "running") return state;
      const incoming = event.payload.percent;
      if (incoming < state.percent) return state;
      if (incoming >= 100) return state;
      return { ...state, percent: incoming };
    }

    case "artifact_created": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      return state;
    }

    case "job_completed": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      return {
        status: "completed",
        jobId: event.jobId,
        attemptId: event.payload.attemptId,
        artifactPath: event.payload.artifactPath,
        artifactName: event.payload.artifactName,
      };
    }

    case "job_failed": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      return {
        status: "failed",
        jobId: event.jobId,
        attemptId: event.payload.attemptId,
        errorCode: event.payload.errorCode,
        stageId: event.payload.stageId,
        recoverable: event.payload.recoverable,
        details: event.payload.details,
      };
    }

    case "job_cancelled": {
      if (state.status !== "running" && state.status !== "cancelling") return state;
      if (state.attemptId !== event.payload.attemptId) return state;
      return {
        status: "cancelled",
        jobId: event.jobId,
        attemptId: event.payload.attemptId,
      };
    }
  }
}

export function resetJobRunState(): JobRunState {
  return { status: "idle" };
}
