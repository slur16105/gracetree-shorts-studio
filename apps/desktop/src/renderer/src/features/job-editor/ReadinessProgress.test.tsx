import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ReadinessProgress } from './ReadinessProgress'
import type { ReadinessResult } from './readiness'

function makeReadiness(satisfiedCount: number): ReadinessResult {
  const roles = ['thumbnail', 'voice', 'bgm', 'script'] as const
  const labels = ['썸네일', '음성', 'BGM', '스크립트']
  const missingActions = [
    '썸네일 이미지를 등록하세요.',
    '음성 파일(voice.*)을 등록하세요.',
    'BGM 파일(bgm.*)을 등록하세요.',
    '스크립트 파일을 등록하세요.',
  ]
  const total = 4
  const slots = roles.map((role, i) => ({
    role,
    satisfied: i < satisfiedCount,
    label: labels[i],
    missingAction: missingActions[i],
  }))
  const percent = Math.round((satisfiedCount / total) * 100)
  const isReady = satisfiedCount === total
  const blockingReasons = slots.filter((s) => !s.satisfied).map((s) => s.missingAction)
  return {
    slots,
    satisfiedCount,
    total,
    percent,
    isReady,
    blockingReasons,
    nextAction: blockingReasons[0] ?? null,
    commonResourcesReady: true,
  }
}

describe('ReadinessProgress', () => {
  it('shows progressbar with aria-valuenow=100 and "준비 완료" text when fully ready', () => {
    render(<ReadinessProgress isParsing={false} readiness={makeReadiness(4)} />)

    const progressbar = screen.getByRole('progressbar')
    expect(progressbar).toHaveAttribute('aria-valuenow', '100')
    expect(progressbar).toHaveAttribute('aria-valuemin', '0')
    expect(progressbar).toHaveAttribute('aria-valuemax', '100')
    expect(screen.getByRole('status')).toHaveTextContent('준비 완료')
    expect(screen.getByText('필수 입력 4/4')).toBeVisible()
    expect(screen.getByText('100%')).toBeVisible()
  })

  it('shows progressbar with aria-valuenow=0 and counts when nothing is ready', () => {
    render(<ReadinessProgress isParsing={false} readiness={makeReadiness(0)} />)

    const progressbar = screen.getByRole('progressbar')
    expect(progressbar).toHaveAttribute('aria-valuenow', '0')
    expect(screen.getByText('필수 입력 0/4')).toBeVisible()
    expect(screen.getByText('0%')).toBeVisible()
  })

  it('shows parsing status text when isParsing is true', () => {
    render(<ReadinessProgress isParsing={true} readiness={makeReadiness(2)} />)

    expect(screen.getByRole('status')).toHaveTextContent('스크립트를 확인하고 있습니다…')
  })

  it('shows icon and text for each slot — not relying on color alone', () => {
    render(<ReadinessProgress isParsing={false} readiness={makeReadiness(2)} />)

    // 첫 2개 슬롯(썸네일, 음성)은 satisfied → ✓ 아이콘
    // 나머지 2개(BGM, 스크립트)는 unsatisfied → ✗ 아이콘
    const list = screen.getByRole('list')
    const items = list.querySelectorAll('li')
    expect(items).toHaveLength(4)

    // 슬롯 레이블 텍스트 확인 (색상 외 텍스트 존재)
    expect(screen.getByText('썸네일')).toBeVisible()
    expect(screen.getByText('음성')).toBeVisible()
    expect(screen.getByText('BGM')).toBeVisible()
    expect(screen.getByText('스크립트')).toBeVisible()
  })

  it('shows aria-live region while parsing the script', () => {
    render(<ReadinessProgress isParsing={true} readiness={makeReadiness(2)} />)

    // live region이 존재하는지 확인 (polite + atomic)
    const liveRegion = screen.getByText('스크립트를 확인하고 있습니다…').parentElement
    expect(liveRegion).toHaveAttribute('aria-live', 'polite')
    expect(liveRegion).toHaveAttribute('aria-atomic', 'true')
  })

  it('shows partial progress count correctly', () => {
    render(<ReadinessProgress isParsing={false} readiness={makeReadiness(3)} />)

    expect(screen.getByText('필수 입력 3/4')).toBeVisible()
    expect(screen.getByText('75%')).toBeVisible()
    const progressbar = screen.getByRole('progressbar')
    expect(progressbar).toHaveAttribute('aria-valuenow', '75')
  })
})
