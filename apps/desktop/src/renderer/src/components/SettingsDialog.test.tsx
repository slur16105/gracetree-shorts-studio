import type { ResourceDto } from '@gracetree/contracts'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SettingsDialog } from './SettingsDialog'

const MANAGED_ROOT = '/managed'

function makeResource(
  type: ResourceDto['type'],
  status: ResourceDto['status'] = 'ready',
  managedPath: string | null = null,
): ResourceDto {
  return {
    type,
    managedPath: managedPath ?? (status === 'ready' ? `/managed/resources/${type}.file` : null),
    status,
    updatedAt: '2026-06-25T00:00:00.000Z',
  }
}

const ALL_RESOURCES: ResourceDto[] = [
  makeResource('title_scripture_video', 'ready', '/managed/resources/title_scripture_video.mp4'),
  makeResource('prayer_loop_video', 'missing'),
  makeResource('default_bgm', 'ready', '/managed/resources/default_bgm.mp3'),
  makeResource('subtitle_font', 'invalid'),
]

describe('SettingsDialog', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    mockOnClose.mockReset()
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getResources: vi.fn(async () => ALL_RESOURCES),
        selectResourceFile: vi.fn(async () => null),
        updateResource: vi.fn(async () => ({ resources: ALL_RESOURCES, error: null })),
      },
    })
  })

  it('열릴 때 getResources를 managedRoot로 호출함', async () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await waitFor(() => {
      expect(window.desktopApi.getResources).toHaveBeenCalledWith(MANAGED_ROOT)
    })
  })

  it('각 행에 리소스 이름과 상태 텍스트를 표시함', async () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    // 리소스 이름 확인
    expect(screen.getByText('제목·말씀 영상')).toBeVisible()
    expect(screen.getByText('기도 영상')).toBeVisible()
    expect(screen.getByText('기본 BGM')).toBeVisible()
    expect(screen.getByText('자막 폰트')).toBeVisible()

    // 로드 후 상태 확인
    await waitFor(() => {
      // ready: 파일명 표시
      expect(screen.getByText('title_scripture_video.mp4')).toBeVisible()
      // missing: 미등록 표시
      expect(screen.getAllByText('미등록').length).toBeGreaterThan(0)
      // invalid: 오류 표시
      expect(screen.getByText('오류')).toBeVisible()
    })
  })

  it('ready 상태 행에 ✓ 아이콘을 표시함', async () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await waitFor(() => {
      const readyRow = screen.getByRole('listitem', { name: /제목·말씀 영상 — 준비/ })
      expect(readyRow).toBeInTheDocument()
    })
  })

  it('missing 상태 행에 ✗ 아이콘을 표시함', async () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await waitFor(() => {
      const missingRow = screen.getByRole('listitem', { name: /기도 영상 — 미등록/ })
      expect(missingRow).toBeInTheDocument()
    })
  })

  it('invalid 상태 행에 ⚠ 아이콘을 표시함', async () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await waitFor(() => {
      const invalidRow = screen.getByRole('listitem', { name: /자막 폰트 — 오류/ })
      expect(invalidRow).toBeInTheDocument()
    })
  })

  it('파일 선택 버튼 클릭 시 selectResourceFile을 호출함', async () => {
    const user = userEvent.setup()
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    const selectButton = screen.getByRole('button', { name: '제목·말씀 영상 파일 선택' })
    await user.click(selectButton)

    expect(window.desktopApi.selectResourceFile).toHaveBeenCalledWith('title_scripture_video')
  })

  it('파일 선택 후 성공 시 updateResource를 호출하고 행 상태를 갱신함', async () => {
    const user = userEvent.setup()
    const selectedFile = { name: 'new-title.mp4', sourcePath: '/source/new-title.mp4' }
    const updatedResources: ResourceDto[] = [
      makeResource('title_scripture_video', 'ready', '/managed/resources/title_scripture_video.mp4'),
      makeResource('prayer_loop_video', 'ready', '/managed/resources/prayer_loop_video.mp4'),
      makeResource('default_bgm', 'ready', '/managed/resources/default_bgm.mp3'),
      makeResource('subtitle_font', 'ready', '/managed/resources/subtitle_font.ttf'),
    ]

    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getResources: vi.fn(async () => ALL_RESOURCES),
        selectResourceFile: vi.fn(async () => selectedFile),
        updateResource: vi.fn(async () => ({ resources: updatedResources, error: null })),
      },
    })

    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    const selectButton = screen.getByRole('button', { name: '기도 영상 파일 선택' })
    await user.click(selectButton)

    await waitFor(() => {
      expect(window.desktopApi.updateResource).toHaveBeenCalledWith(
        'prayer_loop_video',
        '/source/new-title.mp4',
        MANAGED_ROOT,
      )
    })

    await waitFor(() => {
      // 모든 행이 ready → 파일명 표시
      expect(screen.getByText('prayer_loop_video.mp4')).toBeVisible()
    })
  })

  it('오류 응답 시 해당 행에 에러 메시지를 표시함', async () => {
    const user = userEvent.setup()
    const selectedFile = { name: 'bad-file.mp4', sourcePath: '/source/bad-file.mp4' }

    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getResources: vi.fn(async () => []),
        selectResourceFile: vi.fn(async () => selectedFile),
        updateResource: vi.fn(async () => ({
          resources: [],
          error: {
            resourceType: 'title_scripture_video',
            code: 'UNSUPPORTED_FORMAT',
            message: '지원하지 않는 파일 형식입니다.',
          },
        })),
      },
    })

    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    const selectButton = screen.getByRole('button', { name: '제목·말씀 영상 파일 선택' })
    await user.click(selectButton)

    await waitFor(() => {
      expect(screen.getByText('지원하지 않는 파일 형식입니다.')).toBeVisible()
    })
  })

  it('Escape 키로 다이얼로그를 닫음', async () => {
    const user = userEvent.setup()
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await user.keyboard('{Escape}')

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('aria-modal 속성이 설정되어 있음', () => {
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    const dialog = screen.getByRole('dialog', { name: '공통 리소스 설정' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('Tab 포커스 트랩이 파일 선택 버튼들과 닫기 버튼을 순환함', async () => {
    const user = userEvent.setup()
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    // 첫 번째 버튼에 초기 포커스
    const firstSelectButton = screen.getByRole('button', { name: '제목·말씀 영상 파일 선택' })
    expect(firstSelectButton).toHaveFocus()

    // Tab 순환
    await user.tab()
    expect(screen.getByRole('button', { name: '기도 영상 파일 선택' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('button', { name: '기본 BGM 파일 선택' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('button', { name: '자막 폰트 파일 선택' })).toHaveFocus()

    const closeButton = screen.getByRole('button', { name: '설정 닫기' })
    await user.tab()
    expect(closeButton).toHaveFocus()

    // 마지막에서 Tab → 처음으로
    await user.tab()
    expect(firstSelectButton).toHaveFocus()

    // Shift+Tab: 처음에서 → 마지막으로
    await user.tab({ shift: true })
    expect(closeButton).toHaveFocus()
  })

  it('닫기 버튼 클릭 시 onClose를 호출함', async () => {
    const user = userEvent.setup()
    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await user.click(screen.getByRole('button', { name: '설정 닫기' }))

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('파일 선택을 취소하면 updateResource를 호출하지 않음', async () => {
    const user = userEvent.setup()

    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getResources: vi.fn(async () => []),
        selectResourceFile: vi.fn(async () => null), // 취소
        updateResource: vi.fn(async () => ({ resources: [], error: null })),
      },
    })

    render(<SettingsDialog managedRoot={MANAGED_ROOT} onClose={mockOnClose} />)

    await user.click(screen.getByRole('button', { name: '기도 영상 파일 선택' }))

    expect(window.desktopApi.updateResource).not.toHaveBeenCalled()
  })
})
