import type { EngineCommand, EngineEvent, StartJobCommand } from '@gracetree/contracts'
import { isEngineEvent } from '@gracetree/contracts'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { createInterface, type Interface } from 'node:readline'
import type { EngineSpawnConfig } from '../files/resource-paths'

interface PendingRequest {
  resolve: (event: EngineEvent) => void
  reject: (error: Error) => void
  timeout: NodeJS.Timeout
}

interface StreamListener {
  onEvent: (event: EngineEvent) => void
  resolve: () => void
  reject: (error: Error) => void
  timeout: NodeJS.Timeout
}

const DEFAULT_REQUEST_TIMEOUT_MS = 5_000
const INPUT_REGISTRATION_TIMEOUT_MS = 30 * 60 * 1_000
const GENERATION_TIMEOUT_MS = 10 * 60 * 1_000

export class EngineClient {
  private child: ChildProcessWithoutNullStreams | null = null
  private lines: Interface | null = null
  private readonly pending = new Map<string, PendingRequest>()
  private readonly streamListeners = new Map<string, StreamListener>()

  constructor(
    private readonly projectRoot: string,
    private readonly approvedManagedRoot: string,
    private readonly spawnConfig: EngineSpawnConfig = {
      command: process.env['PYTHON'] ?? 'python3',
      args: ['-m', 'gracetree_engine'],
    }
  ) {}

  async request(command: EngineCommand): Promise<EngineEvent> {
    if (this.pending.has(command.jobId)) {
      throw new Error(`Python engine request for job ${command.jobId} is already pending`)
    }
    this.ensureStarted()
    const child = this.child
    if (!child) throw new Error('Python engine did not start')

    return new Promise<EngineEvent>((resolve, reject) => {
      const timeoutMs =
        command.type === 'register_input_files' ||
        (command.type === 'manage_input' && command.payload.action === 'replace')
          ? INPUT_REGISTRATION_TIMEOUT_MS
          : DEFAULT_REQUEST_TIMEOUT_MS
      const timeout = setTimeout(() => {
        if (!this.pending.has(command.jobId)) return
        this.terminateChild(child, new Error('Python engine request timed out'))
      }, timeoutMs)
      this.pending.set(command.jobId, { resolve, reject, timeout })
      child.stdin.write(`${JSON.stringify(command)}\n`)
    })
  }

  streamJob(command: StartJobCommand, onEvent: (event: EngineEvent) => void): Promise<void> {
    if (this.streamListeners.has(command.jobId)) {
      throw new Error(`Python engine stream for job ${command.jobId} is already active`)
    }
    this.ensureStarted()
    const child = this.child
    if (!child) throw new Error('Python engine did not start')
    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (!this.streamListeners.has(command.jobId)) return
        this.streamListeners.delete(command.jobId)
        reject(new Error('start_job stream timed out'))
        this.terminateCurrentChild(new Error('start_job stream timed out'))
      }, GENERATION_TIMEOUT_MS)
      this.streamListeners.set(command.jobId, { onEvent, resolve, reject, timeout })
      child.stdin.write(`${JSON.stringify(command)}\n`)
    })
  }

  stop(): void {
    const child = this.child
    if (child) {
      this.terminateChild(child, new Error('Python engine stopped'))
      return
    }
    this.rejectPending(new Error('Python engine stopped'))
  }

  private ensureStarted(): void {
    if (this.child) return
    const { command, args } = this.spawnConfig
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      GRACETREE_MANAGED_ROOT: this.approvedManagedRoot,
    }
    // In dev mode (python -m gracetree_engine), provide the source tree on PYTHONPATH.
    // In packaged mode (PyInstaller bundle), PYTHONPATH is irrelevant and must not be set
    // to a source path that may not exist on the end user's machine.
    if (args.length > 0 && args[0] === '-m') {
      env['PYTHONPATH'] = `${this.projectRoot}/engine`
    }
    const child = spawn(command, args, {
      cwd: this.projectRoot,
      env,
      stdio: ['pipe', 'pipe', 'pipe']
    })
    this.child = child
    child.stderr.on('data', () => {
      // Diagnostics intentionally remain out of renderer-facing messages.
    })
    child.once('error', () => {
      this.handleChildFailure(child, new Error('Python engine failed to start'))
    })
    child.once('close', () => {
      this.handleChildFailure(child, new Error('Python engine exited unexpectedly'))
    })
    this.lines = createInterface({ input: child.stdout })
    this.lines.on('line', (line) => this.handleLine(line))
  }

  private handleLine(line: string): void {
    let value: unknown
    try {
      value = JSON.parse(line)
    } catch {
      this.terminateCurrentChild(new Error('Python engine emitted invalid JSON'))
      return
    }
    if (!isEngineEvent(value)) {
      this.terminateCurrentChild(new Error('Python engine emitted an invalid event'))
      return
    }
    const streamListener = this.streamListeners.get(value.jobId)
    if (streamListener) {
      streamListener.onEvent(value)
      if (
        value.type === 'job_completed' ||
        value.type === 'job_failed' ||
        value.type === 'job_cancelled'
      ) {
        clearTimeout(streamListener.timeout)
        this.streamListeners.delete(value.jobId)
        streamListener.resolve()
        // cancel_job IPC caller may be waiting in pending for this same event
        const cancelPending = this.pending.get(value.jobId)
        if (cancelPending) {
          clearTimeout(cancelPending.timeout)
          this.pending.delete(value.jobId)
          cancelPending.resolve(value)
        }
      }
      return
    }
    const pending = this.pending.get(value.jobId)
    if (!pending) return
    clearTimeout(pending.timeout)
    this.pending.delete(value.jobId)
    pending.resolve(value)
  }

  private terminateCurrentChild(error: Error): void {
    const child = this.child
    if (child) {
      this.terminateChild(child, error)
      return
    }
    this.rejectPending(error)
  }

  private terminateChild(child: ChildProcessWithoutNullStreams, error: Error): void {
    if (this.child !== child) return
    this.lines?.close()
    this.lines = null
    this.child = null
    child.stdin.destroy()
    child.kill()
    this.rejectPending(error)
  }

  private handleChildFailure(child: ChildProcessWithoutNullStreams, error: Error): void {
    if (this.child !== child) return
    this.lines?.close()
    this.lines = null
    this.child = null
    this.rejectPending(error)
  }

  private rejectPending(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout)
      pending.reject(error)
    }
    this.pending.clear()
    for (const listener of this.streamListeners.values()) {
      clearTimeout(listener.timeout)
      listener.reject(error)
    }
    this.streamListeners.clear()
  }
}
