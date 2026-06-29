import { copyFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { extname, join, resolve, sep } from 'node:path'

/** Short program name used as the Downloads copy prefix (GraceTree Shorts Studio). */
const DOWNLOAD_NAME_PREFIX = 'GTS'

function pad2(value: number): string {
  return value < 10 ? `0${value}` : String(value)
}

/**
 * Build the user-facing copy name: `GTS_YYMMDDHHMM(.ext)` from local completion time.
 * Minute precision (no seconds) is intentional; same-minute collisions are handled by the caller.
 */
export function buildDownloadFileName(now: Date, extension: string): string {
  const stamp =
    pad2(now.getFullYear() % 100) +
    pad2(now.getMonth() + 1) +
    pad2(now.getDate()) +
    pad2(now.getHours()) +
    pad2(now.getMinutes())
  const ext = extension ? (extension.startsWith('.') ? extension : `.${extension}`) : ''
  return `${DOWNLOAD_NAME_PREFIX}_${stamp}${ext}`
}

/**
 * Pick a destination path in `dir` for `fileName`, appending `_2`, `_3`, … until a free name
 * is found. Keeps existing Downloads copies intact instead of overwriting them.
 */
function resolveNonCollidingPath(
  dir: string,
  fileName: string,
  exists: (path: string) => boolean
): string {
  const ext = extname(fileName)
  const stem = ext ? fileName.slice(0, -ext.length) : fileName
  let candidate = join(dir, fileName)
  let counter = 2
  while (exists(candidate)) {
    candidate = join(dir, `${stem}_${counter}${ext}`)
    counter += 1
  }
  return candidate
}

export interface ExportArtifactDeps {
  exists?: (path: string) => boolean
  copy?: (src: string, dest: string) => Promise<void>
  now?: () => Date
}

/**
 * Copy a completed render artifact into the user's Downloads folder as `GTS_YYMMDDHHMM.mp4`.
 *
 * The managed-root artifact remains the source of truth; this is a best-effort convenience copy.
 * `artifactPath` is re-validated against the managed root (defence in depth) before any file I/O.
 * Returns the absolute destination path.
 */
export async function exportArtifactToDownloads(
  artifactPath: string,
  managedRoot: string,
  downloadsDir: string,
  deps: ExportArtifactDeps = {}
): Promise<string> {
  const exists = deps.exists ?? existsSync
  const copy = deps.copy ?? copyFile
  const now = deps.now ?? ((): Date => new Date())

  // Only ever copy artifacts that live inside the managed root.
  const canonicalManaged = resolve(managedRoot)
  const canonicalArtifact = resolve(artifactPath)
  if (!canonicalArtifact.startsWith(canonicalManaged + sep)) {
    throw new Error(`Artifact path is outside managed root: ${artifactPath}`)
  }
  if (!exists(canonicalArtifact)) {
    throw new Error(`Artifact does not exist: ${artifactPath}`)
  }

  const fileName = buildDownloadFileName(now(), extname(canonicalArtifact))
  const dest = resolveNonCollidingPath(downloadsDir, fileName, exists)
  await copy(canonicalArtifact, dest)
  return dest
}
