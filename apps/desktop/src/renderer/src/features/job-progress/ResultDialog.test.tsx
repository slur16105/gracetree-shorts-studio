import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ResultDialog } from './ResultDialog'

const DEFAULT_PROPS = {
  title: '오늘의 은혜',
  publishDate: '2026-06-20',
  onOpenFolder: vi.fn(),
  onClose: vi.fn()
}

describe('ResultDialog', () => {
  it('제목과 게시 날짜를 표시하고 폴더 열기 동작을 제공한다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('오늘의 은혜')).toBeInTheDocument()
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '폴더 열기' })).toBeInTheDocument()
  })

  it('폴더 열기 버튼 클릭 시 onOpenFolder를 호출한다', async () => {
    const user = userEvent.setup()
    const onOpenFolder = vi.fn()
    render(<ResultDialog {...DEFAULT_PROPS} onOpenFolder={onOpenFolder} />)

    await user.click(screen.getByRole('button', { name: '폴더 열기' }))

    expect(onOpenFolder).toHaveBeenCalledOnce()
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
    const openButton = screen.getByRole('button', { name: '폴더 열기' })
    confirmButton.focus()
    await user.tab()
    // 마지막 버튼(확인)에서 Tab 시 첫 버튼(폴더 열기)으로 순환한다
    expect(openButton).toHaveFocus()
  })

  it('role="dialog"과 aria-modal="true"를 가진다', () => {
    render(<ResultDialog {...DEFAULT_PROPS} />)

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })
})
