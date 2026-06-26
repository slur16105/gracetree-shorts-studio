import {
  INITIAL_JOB_RUN_STATE,
  applyJobEvent,
  type JobRunState,
} from "@gracetree/contracts/job-state";
import type { EngineEvent } from "@gracetree/contracts";
import { useSyncExternalStore } from "react";

type StoreState = {
  currentJobId: string | null;
  runState: JobRunState;
};

let _state: StoreState = { currentJobId: null, runState: INITIAL_JOB_RUN_STATE };
const _listeners = new Set<() => void>();

function _notify(): void {
  for (const fn of _listeners) fn();
}

function _getRunState(): JobRunState {
  return _state.runState;
}

function _subscribe(listener: () => void): () => void {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

export function setCurrentJobId(jobId: string | null): void {
  if (_state.currentJobId === jobId) return;
  _state = { currentJobId: jobId, runState: INITIAL_JOB_RUN_STATE };
  _notify();
}

export function dispatchJobEvent(event: EngineEvent): void {
  const { currentJobId, runState } = _state;
  if (!currentJobId) return;
  const next = applyJobEvent(runState, event, currentJobId);
  if (next !== runState) {
    _state = { currentJobId, runState: next };
    _notify();
  }
}

export function resetJobProgress(): void {
  const next: StoreState = {
    currentJobId: _state.currentJobId,
    runState: INITIAL_JOB_RUN_STATE,
  };
  if (next.runState !== _state.runState) {
    _state = next;
    _notify();
  }
}

export function useJobRunState(): JobRunState {
  return useSyncExternalStore(_subscribe, _getRunState);
}

export function setJobCancelling(): void {
  const { currentJobId, runState } = _state;
  if (!currentJobId) return;
  if (runState.status !== "running") return;
  _state = {
    currentJobId,
    runState: {
      status: "cancelling",
      jobId: runState.jobId,
      attemptId: runState.attemptId,
    },
  };
  _notify();
}

export function revertJobCancellingToRunning(
  prevState: Extract<JobRunState, { status: "running" }>
): void {
  const { currentJobId, runState } = _state;
  if (!currentJobId) return;
  if (runState.status !== "cancelling") return;
  _state = { currentJobId, runState: prevState };
  _notify();
}

export function useIsRunning(): boolean {
  const state = useJobRunState();
  return state.status === "running" || state.status === "cancelling";
}
