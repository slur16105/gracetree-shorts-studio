import { describe, it, expect } from 'vitest'
import {
  resolveEngineCommand,
  resolveFfmpegPath,
  resolveFfprobePath,
} from './resource-paths'

const WIN_RESOURCES = 'C:\\Users\\User\\AppData\\Local\\Programs\\GraceTree\\resources'
const MAC_RESOURCES = '/Applications/GraceTree Shorts Studio.app/Contents/Resources'

describe('resolveEngineCommand — packaged mode', () => {
  it('returns bundled exe on Windows', () => {
    const { command, args, isDev } = resolveEngineCommand(WIN_RESOURCES, false, 'win32')
    expect(command).toContain('gracetree-engine.exe')
    expect(command).toContain('engine')
    expect(args).toEqual([])
    expect(isDev).toBe(false)
  })

  it('returns bundled binary on macOS (no .exe)', () => {
    const { command, args, isDev } = resolveEngineCommand(MAC_RESOURCES, false, 'darwin')
    expect(command).toContain('gracetree-engine')
    expect(command).not.toContain('.exe')
    expect(args).toEqual([])
    expect(isDev).toBe(false)
  })

  it('command uses args array (spaces in path work correctly)', () => {
    const resourcesWithSpaces = 'C:\\Program Files\\GraceTree Studios\\resources'
    const { command, args } = resolveEngineCommand(resourcesWithSpaces, false, 'win32')
    // The command contains the full path (including spaces); args is empty
    // spawn(command, args) handles this safely without shell interpolation
    expect(command).toContain('Program Files')
    expect(args).toEqual([])
  })

  it('command handles non-ASCII path segments', () => {
    const resourcesNonAscii = '/Users/김철수/앱/GraceTree.app/Contents/Resources'
    const { command, args } = resolveEngineCommand(resourcesNonAscii, false, 'darwin')
    expect(command).toContain('김철수')
    expect(args).toEqual([])
  })
})

describe('resolveEngineCommand — dev mode', () => {
  it('uses python command with -m flag and isDev=true', () => {
    const { args, isDev } = resolveEngineCommand('/project/resources', true, 'darwin')
    expect(args).toContain('-m')
    expect(args).toContain('gracetree_engine')
    expect(isDev).toBe(true)
  })

  it('does not reference resources path in dev mode', () => {
    const { command, args } = resolveEngineCommand('/irrelevant/path', true, 'win32')
    expect(command).not.toContain('irrelevant')
    expect(args.join(' ')).not.toContain('irrelevant')
  })
})

describe('resolveFfmpegPath', () => {
  it('returns bundled ffmpeg.exe on Windows in packaged mode', () => {
    const p = resolveFfmpegPath(WIN_RESOURCES, false, 'win32')
    expect(p).toContain('ffmpeg.exe')
    expect(p).toContain('ffmpeg')
  })

  it('returns bundled ffmpeg (no .exe) on macOS in packaged mode', () => {
    const p = resolveFfmpegPath(MAC_RESOURCES, false, 'darwin')
    expect(p).toContain('ffmpeg')
    expect(p).not.toContain('.exe')
  })

  it('returns "ffmpeg" fallback in dev mode', () => {
    const p = resolveFfmpegPath('/any', true, 'darwin')
    expect(p).toBe('ffmpeg')
  })
})

describe('resolveFfprobePath', () => {
  it('returns bundled ffprobe.exe on Windows in packaged mode', () => {
    const p = resolveFfprobePath(WIN_RESOURCES, false, 'win32')
    expect(p).toContain('ffprobe.exe')
  })

  it('returns "ffprobe" fallback in dev mode', () => {
    const p = resolveFfprobePath('/any', true, 'win32')
    expect(p).toBe('ffprobe')
  })
})
