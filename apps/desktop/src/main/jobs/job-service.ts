import type { WebContents } from 'electron'
import type { StartJobCommand } from '@gracetree/contracts'
import { isJobCompletedEvent } from '@gracetree/contracts'
import { JOB_EVENT_CHANNEL } from '@gracetree/contracts/desktop-api'
import type { EngineProcess } from './engine-process'

/**
 * Best-effort hook fired when a job completes, used to copy the final render into the
 * user's Downloads folder. Failures here must never block job completion or event delivery.
 */
export type CompletedArtifactHandler = (artifactPath: string, managedRoot: string) => void

export class JobService {
  constructor(
    private readonly engineProcess: EngineProcess,
    private readonly onCompletedArtifact?: CompletedArtifactHandler
  ) {}

  startJob(
    webContents: WebContents,
    jobId: string,
    managedRoot: string,
    workPath: string,
    regenerate = false
  ): Promise<void> {
    const command: StartJobCommand = {
      protocolVersion: 1,
      type: 'start_job',
      jobId,
      timestamp: new Date().toISOString(),
      payload: regenerate ? { managedRoot, workPath, regenerate: true } : { managedRoot, workPath }
    }
    return this.engineProcess.streamGeneration(command, (event) => {
      if (this.onCompletedArtifact && isJobCompletedEvent(event)) {
        this.onCompletedArtifact(event.payload.artifactPath, managedRoot)
      }
      if (!webContents.isDestroyed()) {
        webContents.send(JOB_EVENT_CHANNEL, event)
      }
    })
  }
}
