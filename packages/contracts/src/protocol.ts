import { Ajv2020, type ErrorObject } from 'ajv/dist/2020.js'
import * as addFormatsModule from 'ajv-formats'
import type { FormatsPlugin } from 'ajv-formats'

import commandSchema from '../schemas/engine-command.schema.json' with { type: 'json' }
import eventSchema from '../schemas/engine-event.schema.json' with { type: 'json' }

export interface CheckHealthCommand {
  protocolVersion: 1
  type: 'check_health'
  jobId: string
  timestamp: string
  payload: Record<string, never>
}

export interface HealthCheckedEvent {
  protocolVersion: 1
  type: 'health_checked'
  jobId: string
  timestamp: string
  payload: {
    status: 'ok'
  }
}

const ajv = new Ajv2020({ allErrors: true, strict: true })
const addFormats = (addFormatsModule.default ?? addFormatsModule) as unknown as FormatsPlugin
addFormats(ajv)

const validateCommand = ajv.compile<CheckHealthCommand>(commandSchema)
const validateEvent = ajv.compile<HealthCheckedEvent>(eventSchema)

export function isCheckHealthCommand(value: unknown): value is CheckHealthCommand {
  return validateCommand(value)
}

export function isHealthCheckedEvent(value: unknown): value is HealthCheckedEvent {
  return validateEvent(value)
}

export function commandValidationErrors(): ErrorObject[] | null | undefined {
  return validateCommand.errors
}

export function eventValidationErrors(): ErrorObject[] | null | undefined {
  return validateEvent.errors
}
