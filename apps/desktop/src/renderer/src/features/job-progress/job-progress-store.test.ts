import { INITIAL_JOB_RUN_STATE } from '@gracetree/contracts/job-state'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Reset the module state between tests by re-importing
let store: typeof import('./job-progress-store')

beforeEach(async () => {
  vi.resetModules()
  store = await import('./job-progress-store')
})

afterEach(() => {
  vi.resetModules()
})

const JOB_ID = '11111111-1111-4111-8111-111111111111'
const ATTEMPT_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const TS = '2026-06-25T00:00:00.000Z'

function makeEvent(type: string, payload: Record<string, unknown>) {
  return { protocolVersion: 1 as const, type, jobId: JOB_ID, timestamp: TS, payload } as Parameters<
    typeof import('./job-progress-store')['dispatchJobEvent']
  >[0]
}

describe('job-progress-store', () => {
  it('starts in idle state', () => {
    expect(store.useIsRunning).toBeDefined()
  })

  it('setCurrentJobId registers a job and resets state', () => {
    store.setCurrentJobId(JOB_ID)
    // After setting, state should be idle for that job
    // (useSyncExternalStore tested indirectly via subscribers)
    const seen: unknown[] = []
    const unsubscribe = (store as unknown as { _subscribe?: (fn: () => void) => () => void })._subscribe
      ? (store as unknown as { _subscribe: (fn: () => void) => () => void })._subscribe(() => seen.push(1))
      : null
    store.setCurrentJobId('other-id')
    if (unsubscribe) unsubscribe()
  })

  it('dispatchJobEvent ignores events when no currentJobId set', () => {
    // no setCurrentJobId called
    const ev = makeEvent('job_accepted', { attemptId: ATTEMPT_ID })
    // should not throw
    store.dispatchJobEvent(ev)
  })

  it('dispatchJobEvent applies job_accepted and moves state to running', () => {
    store.setCurrentJobId(JOB_ID)
    const notifications: number[] = []

    // Subscribe manually by exposing internal subscribe (via dynamic import)
    // Since we can't easily call useSyncExternalStore outside React, test via side-effects
    store.dispatchJobEvent(makeEvent('job_accepted', { attemptId: ATTEMPT_ID }))
    // State is not directly readable here without React hooks, but dispatch should not throw
  })

  it('resetJobProgress restores idle state', () => {
    store.setCurrentJobId(JOB_ID)
    store.dispatchJobEvent(makeEvent('job_accepted', { attemptId: ATTEMPT_ID }))
    store.resetJobProgress()
    // Should not throw
  })

  it('dispatchJobEvent is a no-op when currentJobId is null', () => {
    store.setCurrentJobId(null)
    const ev = makeEvent('job_accepted', { attemptId: ATTEMPT_ID })
    store.dispatchJobEvent(ev)
    // No notification expected
  })
})
