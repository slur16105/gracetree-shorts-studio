import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  isCheckHealthCommand,
  isGetOrCreateJobCommand,
  isHealthCheckedEvent,
  isJobLoadedEvent
} from '../src/protocol.js'

function fixture(name: string): unknown {
  const url = new URL(`../fixtures/${name}`, import.meta.url)
  return JSON.parse(readFileSync(fileURLToPath(url), 'utf8'))
}

describe('engine protocol schemas', () => {
  it('accepts the valid command and event fixtures', () => {
    expect(isCheckHealthCommand(fixture('valid-check-health.json'))).toBe(true)
    expect(isHealthCheckedEvent(fixture('valid-health-checked.json'))).toBe(true)
    expect(isGetOrCreateJobCommand(fixture('valid-get-or-create-job.json'))).toBe(true)
    expect(isJobLoadedEvent(fixture('valid-job-loaded.json'))).toBe(true)
  })

  it.each([
    'invalid-command-missing-job-id.json',
    'invalid-command-wrong-version.json',
    'invalid-command-unknown-type.json',
    'invalid-command-bad-timestamp.json',
    'invalid-command-non-utc-timestamp.json'
  ])('rejects %s', (name) => {
    expect(isCheckHealthCommand(fixture(name))).toBe(false)
  })

  it('rejects invalid dates and job IDs at the engine boundary', () => {
    const command = fixture('valid-get-or-create-job.json') as Record<string, unknown>
    expect(
      isGetOrCreateJobCommand({
        ...command,
        jobId: 'not-a-uuid'
      })
    ).toBe(false)
    expect(
      isGetOrCreateJobCommand({
        ...command,
        payload: {
          ...(command.payload as Record<string, unknown>),
          publishDate: '2026-02-30'
        }
      })
    ).toBe(false)
  })
})
