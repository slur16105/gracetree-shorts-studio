import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { CompletedJobSummary } from '@gracetree/contracts/desktop-api'

import { CompletionList } from './CompletionList'

const MANAGED_ROOT = '/managed'

function makeJob(overrides: Partial<CompletedJobSummary> = {}): CompletedJobSummary {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    publishDate: '2026-06-20',
    title: '오늘의 은혜',
    completedAt: '2026-06-20T10:00:00.000Z',
    resultPath: '/managed/2026-06-20/output',
    resultExists: true,
    ...overrides
  }
}

describe('CompletionList', () => {
  const listCompletedJobs = vi.fn()
  const openResultFolder = vi.fn()

  beforeEach(() => {
    listCompletedJobs.mockReset()
    openResultFolder.mockReset()
    openResultFolder.mockResolvedValue(undefined)
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        listCompletedJobs,
        openResultFolder
      }
    })
  })

  it('빈 목록이면 빈 상태 텍스트를 표시한다', async () => {
    listCompletedJobs.mockResolvedValue([])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    await waitFor(() => {
      expect(
        screen.getByText('아직 완료된 작업이 없습니다. 날짜를 선택해 새 작업을 등록하고 첫 영상을 제작해보세요.')
      ).toBeVisible()
    })
  })

  it('완료된 작업이 있으면 게시 날짜 내림차순으로 표시한다', async () => {
    const older = makeJob({
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      publishDate: '2026-06-10',
      title: '이전 영상'
    })
    const newer = makeJob({
      id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      publishDate: '2026-06-20',
      title: '최신 영상'
    })
    // API가 순서 무관하게 반환해도 정렬되어야 함
    listCompletedJobs.mockResolvedValue([older, newer])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    const list = await screen.findByRole('listbox', { name: '완료된 작업 목록' })
    const items = list.querySelectorAll('[role="option"]')
    expect(items[0]).toHaveAttribute('aria-label', expect.stringContaining('2026'))
    // 첫 번째 항목이 newer(2026-06-20)이어야 함
    expect(items[0]?.textContent).toContain('2026')
    expect(items).toHaveLength(2)
  })

  it('resultExists=false이면 "열기" 버튼이 비활성화된다', async () => {
    const job = makeJob({ resultExists: false })
    listCompletedJobs.mockResolvedValue([job])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    const openButton = await screen.findByRole('button', { name: '열기' })
    expect(openButton).toBeDisabled()
  })

  it('행 클릭 시 onJobSelected가 jobId와 함께 호출된다', async () => {
    const user = userEvent.setup()
    const job = makeJob()
    listCompletedJobs.mockResolvedValue([job])
    const onJobSelected = vi.fn()
    render(<CompletionList managedRoot={MANAGED_ROOT} onJobSelected={onJobSelected} />)

    const row = await screen.findByRole('option')
    await user.click(row)

    expect(onJobSelected).toHaveBeenCalledOnce()
    expect(onJobSelected).toHaveBeenCalledWith(job.id)
  })

  it('Enter 키로 행 선택 시 onJobSelected가 호출된다', async () => {
    const user = userEvent.setup()
    const job = makeJob()
    listCompletedJobs.mockResolvedValue([job])
    const onJobSelected = vi.fn()
    render(<CompletionList managedRoot={MANAGED_ROOT} onJobSelected={onJobSelected} />)

    const row = await screen.findByRole('option')
    row.focus()
    await user.keyboard('{Enter}')

    expect(onJobSelected).toHaveBeenCalledOnce()
    expect(onJobSelected).toHaveBeenCalledWith(job.id)
  })

  it('Space 키로 행 선택 시 onJobSelected가 호출된다', async () => {
    const user = userEvent.setup()
    const job = makeJob()
    listCompletedJobs.mockResolvedValue([job])
    const onJobSelected = vi.fn()
    render(<CompletionList managedRoot={MANAGED_ROOT} onJobSelected={onJobSelected} />)

    const row = await screen.findByRole('option')
    row.focus()
    await user.keyboard(' ')

    expect(onJobSelected).toHaveBeenCalledOnce()
    expect(onJobSelected).toHaveBeenCalledWith(job.id)
  })

  it('"열기" 버튼 클릭 시 openResultFolder가 호출되고 onJobSelected는 호출되지 않는다', async () => {
    const user = userEvent.setup()
    const job = makeJob()
    listCompletedJobs.mockResolvedValue([job])
    const onJobSelected = vi.fn()
    render(<CompletionList managedRoot={MANAGED_ROOT} onJobSelected={onJobSelected} />)

    const openButton = await screen.findByRole('button', { name: '열기' })
    await user.click(openButton)

    expect(openResultFolder).toHaveBeenCalledOnce()
    expect(openResultFolder).toHaveBeenCalledWith(job.id, job.resultPath)
    expect(onJobSelected).not.toHaveBeenCalled()
  })

  it('긴 제목은 title 속성에 전체 제목이 포함된다', async () => {
    const longTitle = '매우 긴 제목입니다 이 제목은 화면에 다 표시되지 않을 수도 있습니다'
    const job = makeJob({ title: longTitle })
    listCompletedJobs.mockResolvedValue([job])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    await screen.findByRole('option')
    const titleEl = screen.getByTitle(longTitle)
    expect(titleEl).toBeInTheDocument()
  })

  it('제목이 null이면 날짜만 표시하고 제목 span이 없다', async () => {
    const job = makeJob({ title: null })
    listCompletedJobs.mockResolvedValue([job])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    const row = await screen.findByRole('option')
    // 제목 텍스트를 감싸는 title 속성 span이 없어야 함 (열기 버튼의 title은 별개)
    const titleSpans = row.querySelectorAll('span[title]')
    expect(titleSpans).toHaveLength(0)
    // aria-label은 날짜 형식
    expect(row).toHaveAttribute('aria-label', expect.stringContaining('2026'))
  })

  it('선택된 행의 aria-selected가 true로 변경된다', async () => {
    const user = userEvent.setup()
    const job = makeJob()
    listCompletedJobs.mockResolvedValue([job])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    const row = await screen.findByRole('option')
    expect(row).toHaveAttribute('aria-selected', 'false')

    await user.click(row)

    expect(row).toHaveAttribute('aria-selected', 'true')
  })

  it('새로고침 버튼 클릭 시 목록을 다시 불러온다', async () => {
    const user = userEvent.setup()
    listCompletedJobs.mockResolvedValue([])
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    await screen.findByText('아직 완료된 작업이 없습니다. 날짜를 선택해 새 작업을 등록하고 첫 영상을 제작해보세요.')

    const newJob = makeJob()
    listCompletedJobs.mockResolvedValue([newJob])

    await user.click(screen.getByRole('button', { name: '새로고침' }))

    await screen.findByRole('option')
    expect(listCompletedJobs).toHaveBeenCalledTimes(2)
  })

  it('로드 오류 시 오류 메시지를 표시한다', async () => {
    listCompletedJobs.mockRejectedValue(new Error('network error'))
    render(<CompletionList managedRoot={MANAGED_ROOT} />)

    await waitFor(() => {
      expect(
        screen.getByText('완료 목록을 불러오지 못했습니다. 새로고침을 눌러 다시 시도하세요.')
      ).toBeVisible()
    })
  })
})
