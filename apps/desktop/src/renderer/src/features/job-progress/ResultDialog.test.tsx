import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ResultDialog } from './ResultDialog'

const DEFAULT_PROPS = {
  title: '오늘의 은혜',
  publishDate: '2026-06-20',
  completedAt: '2026-06-20T10:30:00.000Z',
  resultPath: '/managed/jobs/2026-06-20/output',
  onClose: vi.fn()
}

describe('ResultDialog', () => {
  it('게시 날짜·실제 생성일·결과 위치를 표시한다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('오늘의 은혜')).toBeInTheDocument()
    expect(screen.getAllByText(/2026/).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(DEFAULT_PROPS.resultPath)).toBeInTheDocument()
  })

  it('title이 null이면 제목 영역을 표시하지 않는다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} title={null} />)

    expect(screen.queryByText('오늘의 은혜')).not.toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('마운트 시 확인 버튼에 포커스가 진입한다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} />)

    expect(screen.getByRole('button', { name: '확인' })).toHaveFocus()
  })

  it('확인 버튼 클릭 시 onClose를 호출한다', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ResultDialog {...DEFAULT_PROPS} onClose={onClose} />)

    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('Escape 키 입력 시 onClose를 호출한다', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ResultDialog {...DEFAULT_PROPS} onClose={onClose} />)

    await user.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('Tab 키가 다이얼로그 안에서 순환한다', async () => {
    const user = userEvent.setup()
    render(<ResultDialog {...DEFAULT_PROPS} />)

    const confirmButton = screen.getByRole('button', { name: '확인' })
    confirmButton.focus()
    await user.tab()
    // 버튼이 하나뿐이면 포커스가 첫 버튼으로 돌아온다
    expect(confirmButton).toHaveFocus()
  })

  it('role="dialog"과 aria-modal="true"를 가진다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} />)

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })
})
