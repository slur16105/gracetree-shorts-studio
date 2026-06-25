import type { JobInputDto, ResourceDto } from '@gracetree/contracts'
import type { ScriptValidationDto } from '@gracetree/contracts/desktop-api'

export interface ReadinessSlot {
  role: 'thumbnail' | 'voice' | 'bgm' | 'script'
  satisfied: boolean
  label: string
  missingAction: string
}

export interface ReadinessResult {
  slots: ReadinessSlot[]
  satisfiedCount: number
  total: number
  percent: number
  isReady: boolean
  blockingReasons: string[]
  nextAction: string | null
  commonResourcesReady: boolean
}

function buildScriptMissingAction(
  inputs: JobInputDto[],
  scriptValidation: ScriptValidationDto | null,
): string {
  const hasScriptFile = inputs.some((i) => i.role === 'script' && i.status === 'ready')
  if (!hasScriptFile) {
    return '스크립트 파일을 등록하세요.'
  }
  if (scriptValidation === null) {
    return '스크립트를 확인하고 있습니다…'
  }
  return '스크립트 내용을 확인하세요. [제목], [말씀], [기도] 구역이 필요합니다.'
}

export function computeReadiness(
  inputs: JobInputDto[],
  scriptValidation: ScriptValidationDto | null,
  resources: ResourceDto[] = [],
): ReadinessResult {
  const thumbnailSatisfied = inputs.some((i) => i.role === 'thumbnail' && i.status === 'ready')
  const voiceSatisfied = inputs.some((i) => i.role === 'voice' && i.status === 'ready')
  const perJobBgmSatisfied = inputs.some((i) => i.role === 'bgm' && i.status === 'ready')
  const defaultBgmReady = resources.find((r) => r.type === 'default_bgm')?.status === 'ready'
  const bgmSatisfied = perJobBgmSatisfied || defaultBgmReady
  const scriptFileSatisfied = inputs.some((i) => i.role === 'script' && i.status === 'ready')
  const scriptSatisfied = scriptFileSatisfied && scriptValidation?.status === 'valid'

  const slots: ReadinessSlot[] = [
    {
      role: 'thumbnail',
      satisfied: thumbnailSatisfied,
      label: '썸네일',
      missingAction: '썸네일 이미지를 등록하세요.',
    },
    {
      role: 'voice',
      satisfied: voiceSatisfied,
      label: '음성',
      missingAction: '음성 파일(voice.*)을 등록하세요.',
    },
    {
      role: 'bgm',
      satisfied: bgmSatisfied,
      label: 'BGM',
      missingAction: 'BGM 파일(bgm.*)을 등록하세요.',
    },
    {
      role: 'script',
      satisfied: scriptSatisfied,
      label: '스크립트',
      missingAction: buildScriptMissingAction(inputs, scriptValidation),
    },
  ]

  const satisfiedCount = slots.filter((s) => s.satisfied).length
  const total = 4
  const percent = Math.round((satisfiedCount / total) * 100)
  const isReady = satisfiedCount === total
  const blockingReasons = slots.filter((s) => !s.satisfied).map((s) => s.missingAction)
  const nextAction = blockingReasons[0] ?? null

  const COMMON_RESOURCE_TYPES = ['title_scripture_video', 'prayer_loop_video', 'subtitle_font'] as const
  const commonResourcesReady = COMMON_RESOURCE_TYPES.every(
    (type) => resources.find((r) => r.type === type)?.status === 'ready',
  )

  return {
    slots,
    satisfiedCount,
    total,
    percent,
    isReady,
    blockingReasons,
    nextAction,
    commonResourcesReady,
  }
}
