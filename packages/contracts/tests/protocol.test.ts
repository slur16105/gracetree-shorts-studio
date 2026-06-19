import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { isCheckHealthCommand, isHealthCheckedEvent } from '../src/protocol.js'

function fixture(name: string): unknown {
  const url = new URL(`../fixtures/${name}`, import.meta.url)
  return JSON.parse(readFileSync(fileURLToPath(url), 'utf8'))
}

describe('engine protocol schemas', () => {
  it('accepts the valid command and event fixtures', () => {
    expect(isCheckHealthCommand(fixture('valid-check-health.json'))).toBe(true)
    expect(isHealthCheckedEvent(fixture('valid-health-checked.json'))).toBe(true)
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
})
