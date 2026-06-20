import type { EngineCommand, EngineEvent } from '@gracetree/contracts'
import { isEngineEvent } from '@gracetree/contracts'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { createInterface, type Interface } from 'node:readline'

interface PendingRequest {
  resolve: (event: EngineEvent) => void
  reject: (error: Error) => void
  timeout: NodeJS.Timeout
}

export class EngineClient {
  private child: ChildProcessWithoutNullStreams | null = null
  private lines: Interface | null = null
  private readonly pending = new Map<string, PendingRequest>()

  constructor(
    private readonly projectRoot: string,
    private readonly pythonExecutable = process.env['PYTHON'] ?? 'python3'
  ) {}

  async request(command: EngineCommand): Promise<EngineEvent> {
    this.ensureStarted()
    if (!this.child) throw new Error('Python engine did not start')

    return new Promise<EngineEvent>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(command.jobId)
        reject(new Error('Python engine request timed out'))
      }, 5000)
      this.pending.set(command.jobId, { resolve, reject, timeout })
      this.child?.stdin.write(`${JSON.stringify(command)}\n`)
    })
  }

  stop(): void {
    this.lines?.close()
    this.lines = null
    this.child?.stdin.end()
    this.child?.kill()
    this.child = null
    this.rejectPending(new Error('Python engine stopped'))
  }

  private ensureStarted(): void {
    if (this.child) return
    const engineRoot = `${this.projectRoot}/engine`
    this.child = spawn(this.pythonExecutable, ['-m', 'gracetree_engine'], {
      cwd: this.projectRoot,
      env: { ...process.env, PYTHONPATH: engineRoot },
      stdio: ['pipe', 'pipe', 'pipe']
    })
    this.child.stderr.on('data', () => {
      // Diagnostics intentionally remain out of renderer-facing messages.
    })
    this.child.once('error', () => {
      this.rejectPending(new Error('Python engine failed to start'))
      this.child = null
    })
    this.child.once('close', () => {
      this.rejectPending(new Error('Python engine exited unexpectedly'))
      this.child = null
    })
    this.lines = createInterface({ input: this.child.stdout })
    this.lines.on('line', (line) => this.handleLine(line))
  }

  private handleLine(line: string): void {
    let value: unknown
    try {
      value = JSON.parse(line)
    } catch {
      this.rejectPending(new Error('Python engine emitted invalid JSON'))
      return
    }
    if (!isEngineEvent(value)) {
      this.rejectPending(new Error('Python engine emitted an invalid event'))
      return
    }
    const pending = this.pending.get(value.jobId)
    if (!pending) return
    clearTimeout(pending.timeout)
    this.pending.delete(value.jobId)
    pending.resolve(value)
  }

  private rejectPending(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout)
      pending.reject(error)
    }
    this.pending.clear()
  }
}
