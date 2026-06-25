import type { EngineEvent, StartJobCommand } from '@gracetree/contracts'
import type { EngineClient } from './engine-client'

export type GenerationEventCallback = (event: EngineEvent) => void

export class EngineProcess {
  constructor(private readonly client: EngineClient) {}

  streamGeneration(command: StartJobCommand, onEvent: GenerationEventCallback): Promise<void> {
    return this.client.streamJob(command, onEvent)
  }
}
