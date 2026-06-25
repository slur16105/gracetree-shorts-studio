import type { WebContents } from 'electron'
import type { StartJobCommand } from '@gracetree/contracts'
import { JOB_EVENT_CHANNEL } from '@gracetree/contracts/desktop-api'
import type { EngineProcess } from './engine-process'

export class JobService {
  constructor(private readonly engineProcess: EngineProcess) {}

  startJob(
    webContents: WebContents,
    jobId: string,
    managedRoot: string,
    workPath: string
  ): Promise<void> {
    const command: StartJobCommand = {
      protocolVersion: 1,
      type: 'start_job',
      jobId,
      timestamp: new Date().toISOString(),
      payload: { managedRoot, workPath }
    }
    return this.engineProcess.streamGeneration(command, (event) => {
      if (!webContents.isDestroyed()) {
        webContents.send(JOB_EVENT_CHANNEL, event)
      }
    })
  }
}
