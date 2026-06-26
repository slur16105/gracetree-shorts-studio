/**
 * Story 2.13: Runtime resource path resolver for packaged vs dev mode.
 *
 * In dev mode the engine runs from source via `python3 -m gracetree_engine`;
 * in a packaged installer it uses the PyInstaller onedir bundle placed in
 * extraResources by electron-builder.
 *
 * Functions accept explicit `resourcesPath`, `isDev`, and `platform` parameters
 * instead of reading globals directly, making them fully unit-testable without
 * an Electron environment.
 */

import { join } from 'node:path'

export interface EngineSpawnConfig {
  command: string
  args: string[]
}

const EXE = (platform: string): string => (platform === 'win32' ? '.exe' : '')

/**
 * Return the command and args needed to spawn the Python engine.
 *
 * Packaged: `<resources>/engine/gracetree-engine/gracetree-engine[.exe]`  []
 * Dev:      `python3` (or %PYTHON%)  `['-m', 'gracetree_engine']`
 */
export function resolveEngineCommand(
  resourcesPath: string,
  isDev: boolean,
  platform: NodeJS.Platform | string = process.platform
): EngineSpawnConfig {
  if (isDev) {
    const python =
      process.env['PYTHON'] ?? (platform === 'win32' ? 'python' : 'python3')
    return { command: python, args: ['-m', 'gracetree_engine'] }
  }
  const exe = `gracetree-engine${EXE(platform)}`
  return {
    command: join(resourcesPath, 'engine', 'gracetree-engine', exe),
    args: [],
  }
}

/**
 * Return the path to the ffmpeg executable.
 *
 * Packaged: `<resources>/ffmpeg/ffmpeg[.exe]`
 * Dev:      `ffmpeg` (must be on PATH, or override via %FFMPEG_PATH%)
 */
export function resolveFfmpegPath(
  resourcesPath: string,
  isDev: boolean,
  platform: NodeJS.Platform | string = process.platform
): string {
  if (isDev) return process.env['FFMPEG_PATH'] ?? 'ffmpeg'
  return join(resourcesPath, 'ffmpeg', `ffmpeg${EXE(platform)}`)
}

/**
 * Return the path to the ffprobe executable.
 *
 * Packaged: `<resources>/ffmpeg/ffprobe[.exe]`
 * Dev:      `ffprobe` (must be on PATH, or override via %FFPROBE_PATH%)
 */
export function resolveFfprobePath(
  resourcesPath: string,
  isDev: boolean,
  platform: NodeJS.Platform | string = process.platform
): string {
  if (isDev) return process.env['FFPROBE_PATH'] ?? 'ffprobe'
  return join(resourcesPath, 'ffmpeg', `ffprobe${EXE(platform)}`)
}
