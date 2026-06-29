import { describe, expect, it, vi } from 'vitest'

import { buildDownloadFileName, exportArtifactToDownloads } from './download-export'

describe('buildDownloadFileName', () => {
  it('formats the program name and zero-padded YYMMDDHHMM local timestamp', () => {
    // 2026-06-09 04:05 local time → GTS_2606090405.mp4
    const now = new Date(2026, 5, 9, 4, 5)
    expect(buildDownloadFileName(now, '.mp4')).toBe('GTS_2606090405.mp4')
  })

  it('uses two-minute-precision (no seconds) and the supplied extension', () => {
    const now = new Date(2026, 11, 31, 23, 59, 59)
    expect(buildDownloadFileName(now, '.mp4')).toBe('GTS_2612312359.mp4')
  })

  it('normalises an extension without a leading dot', () => {
    const now = new Date(2026, 5, 29, 14, 30)
    expect(buildDownloadFileName(now, 'mp4')).toBe('GTS_2606291430.mp4')
  })
})

describe('exportArtifactToDownloads', () => {
  const managedRoot = '/Users/test/AppData/GraceTreeData'
  const artifact = `${managedRoot}/jobs/2026-06-29/output/final.mp4`
  const downloads = '/Users/test/Downloads'
  const now = (): Date => new Date(2026, 5, 29, 14, 30)

  it('copies the artifact into Downloads with the GTS name', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    const exists = (p: string): boolean => p === artifact

    const dest = await exportArtifactToDownloads(artifact, managedRoot, downloads, {
      copy,
      exists,
      now
    })

    expect(dest).toBe('/Users/test/Downloads/GTS_2606291430.mp4')
    expect(copy).toHaveBeenCalledWith(artifact, '/Users/test/Downloads/GTS_2606291430.mp4')
  })

  it('appends a numeric suffix when the target name already exists', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    const taken = new Set([
      artifact,
      '/Users/test/Downloads/GTS_2606291430.mp4',
      '/Users/test/Downloads/GTS_2606291430_2.mp4'
    ])
    const exists = (p: string): boolean => taken.has(p)

    const dest = await exportArtifactToDownloads(artifact, managedRoot, downloads, {
      copy,
      exists,
      now
    })

    expect(dest).toBe('/Users/test/Downloads/GTS_2606291430_3.mp4')
    expect(copy).toHaveBeenCalledWith(artifact, '/Users/test/Downloads/GTS_2606291430_3.mp4')
  })

  it('refuses to copy an artifact outside the managed root', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    await expect(
      exportArtifactToDownloads('/etc/passwd', managedRoot, downloads, {
        copy,
        exists: () => true,
        now
      })
    ).rejects.toThrow(/outside managed root/)
    expect(copy).not.toHaveBeenCalled()
  })

  it('throws when the artifact does not exist', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    await expect(
      exportArtifactToDownloads(artifact, managedRoot, downloads, {
        copy,
        exists: () => false,
        now
      })
    ).rejects.toThrow(/does not exist/)
    expect(copy).not.toHaveBeenCalled()
  })
})
