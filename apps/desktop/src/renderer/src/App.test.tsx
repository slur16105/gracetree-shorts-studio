import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App shell', () => {
  it('provides named global entry points and switches the active view', async () => {
    const user = userEvent.setup()
    render(<App />)

    const home = screen.getByRole('button', { name: '홈' })
    const guide = screen.getByRole('button', { name: '사용 가이드' })
    const settings = screen.getByRole('button', { name: '공통 리소스 설정' })

    expect(home).toHaveAttribute('aria-current', 'page')
    expect(guide).not.toHaveAttribute('aria-current')
    expect(settings).not.toHaveAttribute('aria-current')

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

  it('traps dialog focus, closes with Escape, and restores trigger focus', async () => {
    const user = userEvent.setup()
    render(<App />)

    const trigger = screen.getByRole('button', { name: '공통 리소스 설정' })
    await user.click(trigger)

    const dialog = screen.getByRole('dialog', { name: '공통 리소스 설정' })
    const close = screen.getByRole('button', { name: '설정 닫기' })
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(dialog).toBeVisible()
    expect(close).toHaveFocus()

    await user.tab()
    expect(close).toHaveFocus()
    await user.tab({ shift: true })
    expect(close).toHaveFocus()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveFocus()
  })
})
