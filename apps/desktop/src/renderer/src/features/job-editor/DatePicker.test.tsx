import type { JobDto } from '@gracetree/contracts'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DatePicker } from './DatePicker'

const job: JobDto = {
  id: '11111111-1111-4111-8111-111111111111',
  publishDate: '2026-06-20',
  status: 'draft',
  title: null,
  workPath: '/managed/jobs/2026-06-20',
  resultPath: '/managed/jobs/2026-06-20/output',
  createdAt: '2026-06-20T00:00:00.000Z',
  updatedAt: '2026-06-20T00:00:00.000Z',
  pathState: 'ready',
  inputMetadata: []
}

describe('DatePicker', () => {
  const getOrCreateJobForDate = vi.fn(async (publishDate: string) => ({
    ...job,
    publishDate
  }))

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date(2026, 5, 20, 9))
    getOrCreateJobForDate.mockClear()
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: { getOrCreateJobForDate }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads today by default and distinguishes today from the selection', async () => {
    render(<DatePicker />)

    expect(screen.getByRole('button', { name: /게시 날짜 2026-06-20 · Sat/ })).toBeVisible()
    expect(getOrCreateJobForDate).toHaveBeenCalledWith('2026-06-20')

    await userEvent
      .setup({ advanceTimers: vi.advanceTimersByTime })
      .click(screen.getByRole('button', { name: /게시 날짜/ }))
    const selected = screen.getByRole('gridcell', { name: '2026-06-20' })
    expect(selected).toHaveAttribute('aria-selected', 'true')
    expect(selected).toHaveAttribute('aria-current', 'date')
    expect(selected).toHaveAttribute('tabindex', '0')
  })

  it('supports arrows, Home/End and PageUp/PageDown with roving tabindex', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<DatePicker />)
    const trigger = screen.getByRole('button', { name: /게시 날짜/ })
    await user.click(trigger)

    await user.keyboard('{ArrowLeft}')
    expect(screen.getByRole('gridcell', { name: '2026-06-19' })).toHaveFocus()
    await user.keyboard('{ArrowUp}')
    expect(screen.getByRole('gridcell', { name: '2026-06-12' })).toHaveFocus()
    await user.keyboard('{ArrowDown}{ArrowRight}')
    expect(screen.getByRole('gridcell', { name: '2026-06-20' })).toHaveFocus()
    await user.keyboard('{Home}')
    expect(screen.getByRole('gridcell', { name: '2026-06-14' })).toHaveFocus()
    await user.keyboard('{End}')
    expect(screen.getByRole('gridcell', { name: '2026-06-20' })).toHaveFocus()
    await user.keyboard('{PageDown}')
    expect(screen.getByRole('gridcell', { name: '2026-07-20' })).toHaveFocus()
    await user.keyboard('{PageUp}')
    expect(screen.getByRole('gridcell', { name: '2026-06-20' })).toHaveFocus()
  })

  it('selects with Enter and closes with Escape while restoring trigger focus', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<DatePicker />)
    const trigger = screen.getByRole('button', { name: /게시 날짜/ })
    await user.click(trigger)
    await user.keyboard('{ArrowRight}{Enter}')

    expect(screen.queryByRole('dialog', { name: '게시 날짜 선택' })).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    expect(trigger).toHaveAccessibleName(/2026-06-21 · Sun/)
    expect(getOrCreateJobForDate).toHaveBeenLastCalledWith('2026-06-21')

    await user.click(trigger)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: '게시 날짜 선택' })).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('selects with Space and reports restored path inconsistency', async () => {
    getOrCreateJobForDate.mockResolvedValueOnce({ ...job, pathState: 'missing' })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<DatePicker />)

    expect(await screen.findByRole('status')).toHaveTextContent('관리 폴더 확인 필요')
    await user.click(screen.getByRole('button', { name: /게시 날짜/ }))
    await user.keyboard('{ArrowRight} ')
    expect(getOrCreateJobForDate).toHaveBeenLastCalledWith('2026-06-21')
  })
})
