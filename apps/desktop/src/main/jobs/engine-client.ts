import type { EngineCommand, EngineEvent } from '@gracetree/contracts'
import { isEngineEvent } from '@gracetree/contracts'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { createInterface, type Interface } from 'node:readline'

interface PendingRequest {
  resolve: (event: EngineEvent) => void
  reject: (error: Error) => void
  timeout: NodeJS.Timeout
}

const DEFAULT_REQUEST_TIMEOUT_MS = 5_000
const INPUT_REGISTRATION_TIMEOUT_MS = 30 * 60 * 1_000

export class EngineClient {
  private child: ChildProcessWithoutNullStreams | null = null
  private lines: Interface | null = null
  private readonly pending = new Map<string, PendingRequest>()

  constructor(
    private readonly projectRoot: string,
    private readonly approvedManagedRoot: string,
    private readonly pythonExecutable = process.env['PYTHON'] ?? 'python3'
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
    const engineRoot = `${this.projectRoot}/engine`
    const child = spawn(this.pythonExecutable, ['-m', 'gracetree_engine'], {
      cwd: this.projectRoot,
      env: {
        ...process.env,
        PYTHONPATH: engineRoot,
        GRACETREE_MANAGED_ROOT: this.approvedManagedRoot
      },
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
  }
}
