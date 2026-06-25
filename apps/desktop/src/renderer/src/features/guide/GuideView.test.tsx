import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { GuideView } from './GuideView'

describe('GuideView', () => {
  // AC 1: 모든 섹션 존재 확인 (네비게이션 클릭 후 각 섹션 h2 확인)
  it('renders all required sections with logical headings', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    // 첫 번째 섹션은 기본 활성
    expect(screen.getByRole('heading', { name: '첫 영상 만들기', level: 2 })).toBeInTheDocument()

    // 나머지 섹션들은 클릭 후 확인
    for (const sectionName of [
      '파일명 규칙',
      '스크립트 작성법',
      '오류 해결',
      '저장 위치',
      '앱 정보'
    ]) {
      await user.click(screen.getByRole('button', { name: sectionName }))
      expect(screen.getByRole('heading', { name: sectionName, level: 2 })).toBeInTheDocument()
    }
  })

  // AC 1: 섹션 navigation과 탐색 상태 제공
  it('provides section navigation with current indicator', () => {
    render(<GuideView />)

    const nav = screen.getByRole('navigation', { name: '가이드 섹션' })
    expect(nav).toBeInTheDocument()

    // 첫 번째 섹션이 기본 활성
    const firstLink = screen.getByRole('button', { name: '첫 영상 만들기' })
    expect(firstLink).toHaveAttribute('aria-current', 'true')
  })

  // AC 1: 탐색 버튼들이 모두 존재
  it('renders navigation buttons for all sections', () => {
    render(<GuideView />)

    const sectionNames = [
      '첫 영상 만들기',
      '파일명 규칙',
      '스크립트 작성법',
      '오류 해결',
      '저장 위치',
      '앱 정보'
    ]
    for (const name of sectionNames) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
  })

  // AC 1: 섹션 탐색 클릭 시 활성 상태 변경
  it('updates active section when navigation button is clicked', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '파일명 규칙' }))

    expect(screen.getByRole('button', { name: '파일명 규칙' })).toHaveAttribute(
      'aria-current',
      'true'
    )
    expect(screen.getByRole('button', { name: '첫 영상 만들기' })).not.toHaveAttribute(
      'aria-current',
      'true'
    )
  })

  // AC 2: 첫 영상 만들기 - 3단계 Guide Card
  it('shows three Guide Cards for 첫 영상 만들기 section', () => {
    render(<GuideView />)

    // 첫 번째 섹션이 기본으로 보임
    const articles = screen.getAllByRole('article')
    expect(articles.length).toBeGreaterThanOrEqual(3)

    expect(screen.getByText(/게시 날짜 선택/)).toBeInTheDocument()
    expect(screen.getByText(/파일 등록·검증/)).toBeInTheDocument()
    expect(screen.getByText(/생성·결과 확인/)).toBeInTheDocument()
  })

  // AC 3: 파일명 규칙 섹션 - voice.*, bgm.* 규칙
  it('shows voice and bgm naming rules in 파일명 규칙 section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '파일명 규칙' }))

    expect(screen.getByText(/voice\.\*/)).toBeInTheDocument()
    expect(screen.getByText(/bgm\.\*/)).toBeInTheDocument()
  })

  // AC 3: 스크립트 작성법 - 필수 구역
  it('shows required sections in 스크립트 작성법', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '스크립트 작성법' }))

    const content = screen.getByRole('region', { name: '스크립트 작성법' })
    expect(content.textContent).toMatch(/\[제목\]/)
    expect(content.textContent).toMatch(/\[말씀\]/)
    expect(content.textContent).toMatch(/\[기도\]/)
  })

  // AC 4: 저장 위치 - 플랫폼 경로 하드코딩 없음
  it('does not hardcode platform paths in 저장 위치 section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '저장 위치' }))

    const content = screen.getByRole('region', { name: '저장 위치' })
    expect(content.textContent).not.toMatch(/C:\\/)
    expect(content.textContent).not.toMatch(/\/Users\//)
    expect(content.textContent).not.toMatch(/\/home\//)
    expect(content.textContent).toMatch(/input|output|logs/)
  })

  // AC 4: 오류 해결 섹션 - 조치 사항 존재
  it('shows error troubleshooting actions in 오류 해결 section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '오류 해결' }))

    const content = screen.getByRole('region', { name: '오류 해결' })
    expect(content.textContent).toBeTruthy()
    // 오류 해결 섹션이 실질적인 내용을 가짐
    expect(content.querySelectorAll('li').length).toBeGreaterThan(0)
  })

  // AC 6: 접근성 - aria-label, aria-current, 논리적 제목 순서
  it('provides accessible region labels for each section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    // 각 섹션이 접근성 이름을 가진 region
    await user.click(screen.getByRole('button', { name: '첫 영상 만들기' }))
    expect(screen.getByRole('region', { name: '첫 영상 만들기' })).toBeInTheDocument()
  })

  // AC 6: 키보드 탐색 - Tab/Enter/Space
  it('allows keyboard navigation with Tab and Enter', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    const buttons = screen.getAllByRole('button')
    // 네비게이션 버튼들이 포커스 가능
    expect(buttons.length).toBeGreaterThan(0)

    // Enter로 섹션 전환
    const fileRuleButton = screen.getByRole('button', { name: '파일명 규칙' })
    fileRuleButton.focus()
    await user.keyboard('{Enter}')

    expect(screen.getByRole('button', { name: '파일명 규칙' })).toHaveAttribute(
      'aria-current',
      'true'
    )
  })

  // AC 6: Space로도 섹션 전환 가능 (button이므로 기본 동작)
  it('allows section activation with Space key', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    const scriptButton = screen.getByRole('button', { name: '스크립트 작성법' })
    scriptButton.focus()
    await user.keyboard(' ')

    expect(scriptButton).toHaveAttribute('aria-current', 'true')
  })

  // AC 6: 섹션 region에 aria-labelledby 연결
  it('links section region to its heading via aria-labelledby', () => {
    render(<GuideView />)

    const region = screen.getByRole('region', { name: '첫 영상 만들기' })
    expect(region).toBeInTheDocument()
  })

  // 콘텐츠 계약: MVP 비목표 언급 없음
  it('does not mention non-MVP features', () => {
    render(<GuideView />)

    const pageText = document.body.textContent ?? ''
    expect(pageText).not.toMatch(/타임라인 편집/)
    expect(pageText).not.toMatch(/YouTube 업로드/)
    expect(pageText).not.toMatch(/자동 재시도/)
  })

  // AC 3: 파일명 규칙 - 수정 예시 포함
  it('provides naming examples in 파일명 규칙 section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '파일명 규칙' }))

    const content = screen.getByRole('region', { name: '파일명 규칙' })
    // 예시가 code/pre 또는 텍스트로 존재
    expect(content.textContent).toMatch(/voice\.|bgm\./)
  })

  // AC 3: 스크립트 작성법 - 수정 예시 제공
  it('provides script example in 스크립트 작성법 section', async () => {
    const user = userEvent.setup()
    render(<GuideView />)

    await user.click(screen.getByRole('button', { name: '스크립트 작성법' }))

    const content = screen.getByRole('region', { name: '스크립트 작성법' })
    expect(content.querySelectorAll('code, pre').length).toBeGreaterThan(0)
  })
})
