import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App shell', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getOrCreateJobForDate: vi.fn(async (publishDate: string) => ({
          id: '11111111-1111-4111-8111-111111111111',
          publishDate,
          status: 'draft',
          title: null,
          workPath: `/managed/jobs/${publishDate}`,
          resultPath: `/managed/jobs/${publishDate}/output`,
          createdAt: '2026-06-20T00:00:00.000Z',
          updatedAt: '2026-06-20T00:00:00.000Z',
          pathState: 'ready',
          inputMetadata: [],
        })),
        getResources: vi.fn(async () => []),
        listCompletedJobs: vi.fn(async () => []),
        startJob: vi.fn(async () => {}),
        onJobEvent: vi.fn(() => () => {}),
      },
    })
  })

  it('provides named global entry points and switches the active view', async () => {
    const user = userEvent.setup()
    render(<App />)

    const home = screen.getByRole('button', { name: '홈' })
    const guide = screen.getByRole('button', { name: '사용 가이드' })
    const settings = screen.getByRole('button', { name: '공통 리소스 설정' })

    expect(home).toHaveAttribute('aria-current', 'page')
    expect(guide).not.toHaveAttribute('aria-current')
    expect(settings).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('region', { name: '입력' })).toBeVisible()
    expect(screen.getByRole('complementary', { name: '완료 목록' })).toBeVisible()

    await user.click(guide)

    expect(guide).toHaveAttribute('aria-current', 'page')
    expect(home).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('heading', { name: '사용 가이드' })).toBeVisible()
  })

  it('supports native Enter and Space button activation', async () => {
    const user = userEvent.setup()
    render(<App />)

    const guide = screen.getByRole('button', { name: '사용 가이드' })
    guide.focus()
    await user.keyboard('{Enter}')
    expect(guide).toHaveAttribute('aria-current', 'page')

    const home = screen.getByRole('button', { name: '홈' })
    home.focus()
    await user.keyboard(' ')
    expect(home).toHaveAttribute('aria-current', 'page')
  })

  it('follows the global Home, Guide, Settings tab order', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.tab()
    expect(screen.getByRole('button', { name: '홈' })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: '사용 가이드' })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: '공통 리소스 설정' })).toHaveFocus()
  })

  it('preserves job-editor date and slot state when navigating to guide and back', async () => {
    const user = userEvent.setup()
    render(<App />)

    // 홈 뷰에서 DatePicker 날짜 버튼이 표시됨 (초기 로딩 대기)
    const dateTrigger = await screen.findByRole('button', { name: /게시 날짜/ })
    const initialLabel = dateTrigger.getAttribute('aria-label')

    // 가이드로 이동
    await user.click(screen.getByRole('button', { name: '사용 가이드' }))
    expect(screen.getByRole('navigation', { name: '가이드 섹션' })).toBeVisible()

    // 홈으로 복귀
    await user.click(screen.getByRole('button', { name: '홈' }))

    // 날짜 상태가 보존되어야 함
    const restoredTrigger = screen.getByRole('button', { name: /게시 날짜/ })
    expect(restoredTrigger.getAttribute('aria-label')).toBe(initialLabel)
    // 파일 선택 슬롯도 보존
    expect(screen.getByRole('button', { name: '파일 선택' })).toBeVisible()
  })

  it('traps dialog focus, closes with Escape, and restores trigger focus', async () => {
    const user = userEvent.setup()
    render(<App />)

    const trigger = screen.getByRole('button', { name: '공통 리소스 설정' })
    await user.click(trigger)

    const dialog = screen.getByRole('dialog', { name: '공통 리소스 설정' })
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(dialog).toBeVisible()

    // 다이얼로그가 열리면 첫 번째 파일 선택 버튼에 초기 포커스
    const firstSelectButton = screen.getByRole('button', { name: '제목·말씀 영상 파일 선택' })
    expect(firstSelectButton).toHaveFocus()

    // Escape로 닫기
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveFocus()
  })
})
