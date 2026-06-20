import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { InputDropZone } from './InputDropZone'

const jobId = '11111111-1111-4111-8111-111111111111'

describe('InputDropZone', () => {
  const selectInputFiles = vi.fn()
  const registerInputFiles = vi.fn()

  beforeEach(() => {
    selectInputFiles.mockReset()
    registerInputFiles.mockReset()
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getOrCreateJobForDate: vi.fn(),
        selectInputFiles,
        registerInputFiles
      }
    })
  })

  it('uses the same registration API for click and drop batches', async () => {
    const user = userEvent.setup()
    selectInputFiles.mockResolvedValue([{ name: 'voice.mp3', sourcePath: '/voice.mp3' }])
    registerInputFiles.mockResolvedValue([
      {
        originalName: 'voice.mp3',
        managedPath: '/managed/voice.mp3',
        role: 'unclassified',
        status: 'registered',
        errorCode: null
      }
    ])
    render(<InputDropZone jobId={jobId} />)

    await user.click(screen.getByRole('button', { name: '파일 선택' }))
    expect(registerInputFiles).toHaveBeenCalledWith(jobId, [
      { name: 'voice.mp3', sourcePath: '/voice.mp3' }
    ])

    const dropped = new File(['script'], 'script.txt', { type: 'text/plain' })
    fireEvent.drop(screen.getByText(/파일을 한 번에 놓으세요/).parentElement!, {
      dataTransfer: { files: [dropped] }
    })
    expect(registerInputFiles).toHaveBeenLastCalledWith(jobId, [dropped])
  })

  it('announces one batch summary and links each error to its file', async () => {
    const user = userEvent.setup()
    selectInputFiles.mockResolvedValue([
      { name: 'voice.mp3', sourcePath: '/voice.mp3' },
      { name: 'bad.exe', sourcePath: '/bad.exe' }
    ])
    registerInputFiles.mockResolvedValue([
      {
        originalName: 'voice.mp3',
        managedPath: '/managed/voice.mp3',
        role: 'unclassified',
        status: 'registered',
        errorCode: null
      },
      {
        originalName: 'bad.exe',
        managedPath: null,
        role: 'unclassified',
        status: 'rejected',
        errorCode: 'UNSUPPORTED_TYPE'
      }
    ])
    render(<InputDropZone jobId={jobId} />)

    await user.click(screen.getByRole('button', { name: '파일 선택' }))

    expect(screen.getByText('파일 등록 완료: 성공 1개, 거부 1개')).toBeVisible()
    const rejected = screen.getByText('bad.exe').closest('li')
    expect(rejected).toHaveAttribute('aria-describedby')
    expect(screen.getByText('지원하지 않는 파일 형식입니다.')).toBeVisible()
    expect(screen.getByRole('button', { name: '파일 다시 선택' })).toBeVisible()
  })

  it('keeps selection disabled until a job is available', () => {
    render(<InputDropZone jobId={null} />)
    expect(screen.getByRole('button', { name: '파일 선택' })).toBeDisabled()
  })
})
