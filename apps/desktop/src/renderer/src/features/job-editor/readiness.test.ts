import type { JobInputDto, ResourceDto } from '@gracetree/contracts'
import type { ScriptValidationDto } from '@gracetree/contracts/desktop-api'
import { describe, expect, it } from 'vitest'

import { computeReadiness } from './readiness'

const JOB_ID = '11111111-1111-4111-8111-111111111111'

function makeInput(
  id: string,
  role: JobInputDto['role'],
  status: JobInputDto['status'] = 'ready',
): JobInputDto {
  return {
    id,
    jobId: JOB_ID,
    role,
    originalName: `${role}-${id}.file`,
    managedPath: `/managed/${role}-${id}.file`,
    status,
    createdAt: '2026-06-25T00:00:00.000Z',
    updatedAt: '2026-06-25T00:00:00.000Z',
  }
}

function makeValidation(
  status: 'valid' | 'invalid',
  inputId = 'script-1',
): ScriptValidationDto {
  return {
    inputId,
    inputVersion: '2026-06-25T00:00:00.000Z',
    status,
    oneLiner: status === 'valid' ? '오늘의 말씀 — 요한복음 3:16' : null,
    sections: {
      title: status === 'valid' ? '오늘의 말씀' : null,
      scripture: status === 'valid' ? '요한복음 3:16' : null,
      prayer: status === 'valid' ? '기도 내용' : null,
    },
    errors:
      status === 'invalid'
        ? [{ code: 'SECTION_MISSING', section: 'title', message: '[제목] 구역이 없습니다.' }]
        : [],
  }
}

function makeResource(
  type: ResourceDto['type'],
  status: ResourceDto['status'] = 'ready',
): ResourceDto {
  return {
    type,
    managedPath: status === 'ready' ? `/managed/resources/${type}.file` : null,
    status,
    updatedAt: '2026-06-25T00:00:00.000Z',
  }
}

describe('computeReadiness', () => {
  it('returns isReady=true and percent=100 when all 4 slots are satisfied', () => {
    const inputs = [
      makeInput('1', 'thumbnail'),
      makeInput('2', 'voice'),
      makeInput('3', 'bgm'),
      makeInput('4', 'script'),
    ]
    const validation = makeValidation('valid', '4')
    const result = computeReadiness(inputs, validation, [])

    expect(result.isReady).toBe(true)
    expect(result.percent).toBe(100)
    expect(result.satisfiedCount).toBe(4)
    expect(result.blockingReasons).toHaveLength(0)
    expect(result.nextAction).toBeNull()
  })

  it('returns isReady=false and percent=0 when no slots are satisfied', () => {
    const result = computeReadiness([], null, [])

    expect(result.isReady).toBe(false)
    expect(result.percent).toBe(0)
    expect(result.satisfiedCount).toBe(0)
    expect(result.blockingReasons).toHaveLength(4)
    expect(result.nextAction).toBe('썸네일 이미지를 등록하세요.')
  })

  it('returns percent=50 when 2 of 4 slots are satisfied', () => {
    const inputs = [makeInput('1', 'thumbnail'), makeInput('2', 'voice')]
    const result = computeReadiness(inputs, null, [])

    expect(result.percent).toBe(50)
    expect(result.satisfiedCount).toBe(2)
    expect(result.isReady).toBe(false)
  })

  it('does not count script as satisfied when file is ready but validation is null', () => {
    const inputs = [makeInput('1', 'script', 'ready')]
    const result = computeReadiness(inputs, null, [])

    const scriptSlot = result.slots.find((s) => s.role === 'script')!
    expect(scriptSlot.satisfied).toBe(false)
    expect(scriptSlot.missingAction).toBe('스크립트를 확인하고 있습니다…')
  })

  it('counts script as satisfied when file is ready and validation.status is valid', () => {
    const inputs = [makeInput('script-1', 'script', 'ready')]
    const validation = makeValidation('valid', 'script-1')
    const result = computeReadiness(inputs, validation, [])

    const scriptSlot = result.slots.find((s) => s.role === 'script')!
    expect(scriptSlot.satisfied).toBe(true)
  })

  it('does not count script as satisfied when file is ready but validation.status is invalid', () => {
    const inputs = [makeInput('script-1', 'script', 'ready')]
    const validation = makeValidation('invalid', 'script-1')
    const result = computeReadiness(inputs, validation, [])

    const scriptSlot = result.slots.find((s) => s.role === 'script')!
    expect(scriptSlot.satisfied).toBe(false)
    expect(scriptSlot.missingAction).toContain('[제목]')
  })

  it('satisfies thumbnail slot when one of multiple thumbnail inputs is ready', () => {
    const inputs = [
      makeInput('t1', 'thumbnail', 'conflict'),
      makeInput('t2', 'thumbnail', 'ready'),
    ]
    const result = computeReadiness(inputs, null, [])

    const thumbnailSlot = result.slots.find((s) => s.role === 'thumbnail')!
    expect(thumbnailSlot.satisfied).toBe(true)
  })

  it('does not satisfy thumbnail slot when all thumbnails are in conflict state', () => {
    const inputs = [
      makeInput('t1', 'thumbnail', 'conflict'),
      makeInput('t2', 'thumbnail', 'conflict'),
    ]
    const result = computeReadiness(inputs, null, [])

    const thumbnailSlot = result.slots.find((s) => s.role === 'thumbnail')!
    expect(thumbnailSlot.satisfied).toBe(false)
    expect(thumbnailSlot.missingAction).toBe('썸네일 이미지를 등록하세요.')
  })

  it('uses the correct missing action when script file does not exist', () => {
    const result = computeReadiness([], null, [])

    const scriptSlot = result.slots.find((s) => s.role === 'script')!
    expect(scriptSlot.missingAction).toBe('스크립트 파일을 등록하세요.')
  })

  it('exposes slots in order: thumbnail, voice, bgm, script', () => {
    const result = computeReadiness([], null, [])

    expect(result.slots.map((s) => s.role)).toEqual(['thumbnail', 'voice', 'bgm', 'script'])
  })

  it('returns total=4 always', () => {
    expect(computeReadiness([], null, []).total).toBe(4)
  })

  it('uses correct labels for each slot', () => {
    const result = computeReadiness([], null, [])
    const labels = result.slots.map((s) => s.label)
    expect(labels).toEqual(['썸네일', '음성', 'BGM', '스크립트'])
  })

  describe('BGM slot with default_bgm resource fallback', () => {
    it('satisfies bgm slot when per-job BGM is absent but default_bgm resource is ready', () => {
      const inputs = [makeInput('1', 'thumbnail'), makeInput('2', 'voice')]
      const resources = [makeResource('default_bgm', 'ready')]
      const result = computeReadiness(inputs, null, resources)

      const bgmSlot = result.slots.find((s) => s.role === 'bgm')!
      expect(bgmSlot.satisfied).toBe(true)
    })

    it('does not satisfy bgm slot when per-job BGM is absent and default_bgm is missing', () => {
      const inputs = [makeInput('1', 'thumbnail'), makeInput('2', 'voice')]
      const resources = [makeResource('default_bgm', 'missing')]
      const result = computeReadiness(inputs, null, resources)

      const bgmSlot = result.slots.find((s) => s.role === 'bgm')!
      expect(bgmSlot.satisfied).toBe(false)
    })

    it('satisfies bgm slot when per-job BGM is ready regardless of default_bgm status', () => {
      const inputs = [makeInput('1', 'bgm', 'ready')]
      const resources = [makeResource('default_bgm', 'missing')]
      const result = computeReadiness(inputs, null, resources)

      const bgmSlot = result.slots.find((s) => s.role === 'bgm')!
      expect(bgmSlot.satisfied).toBe(true)
    })

    it('does not satisfy bgm slot when no per-job BGM and no resources at all', () => {
      const result = computeReadiness([], null, [])

      const bgmSlot = result.slots.find((s) => s.role === 'bgm')!
      expect(bgmSlot.satisfied).toBe(false)
    })
  })

  describe('commonResourcesReady', () => {
    it('is true when title_scripture_video, prayer_loop_video, and subtitle_font are all ready', () => {
      const resources = [
        makeResource('title_scripture_video', 'ready'),
        makeResource('prayer_loop_video', 'ready'),
        makeResource('default_bgm', 'ready'),
        makeResource('subtitle_font', 'ready'),
      ]
      const result = computeReadiness([], null, resources)
      expect(result.commonResourcesReady).toBe(true)
    })

    it('is true when only the three required resources are ready (default_bgm not needed for gate)', () => {
      const resources = [
        makeResource('title_scripture_video', 'ready'),
        makeResource('prayer_loop_video', 'ready'),
        makeResource('subtitle_font', 'ready'),
      ]
      const result = computeReadiness([], null, resources)
      expect(result.commonResourcesReady).toBe(true)
    })

    it('is false when title_scripture_video is missing', () => {
      const resources = [
        makeResource('title_scripture_video', 'missing'),
        makeResource('prayer_loop_video', 'ready'),
        makeResource('subtitle_font', 'ready'),
      ]
      const result = computeReadiness([], null, resources)
      expect(result.commonResourcesReady).toBe(false)
    })

    it('is false when prayer_loop_video is missing', () => {
      const resources = [
        makeResource('title_scripture_video', 'ready'),
        makeResource('prayer_loop_video', 'missing'),
        makeResource('subtitle_font', 'ready'),
      ]
      const result = computeReadiness([], null, resources)
      expect(result.commonResourcesReady).toBe(false)
    })

    it('is false when subtitle_font is missing', () => {
      const resources = [
        makeResource('title_scripture_video', 'ready'),
        makeResource('prayer_loop_video', 'ready'),
        makeResource('subtitle_font', 'missing'),
      ]
      const result = computeReadiness([], null, resources)
      expect(result.commonResourcesReady).toBe(false)
    })

    it('is false when no resources are provided', () => {
      const result = computeReadiness([], null, [])
      expect(result.commonResourcesReady).toBe(false)
    })
  })
})
