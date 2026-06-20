import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { InputDropZone } from './InputDropZone'

const jobId = '11111111-1111-4111-8111-111111111111'
const nextJobId = '22222222-2222-4222-8222-222222222222'

function registeredResult(name: string): {
  originalName: string
  managedPath: string
  role: 'unclassified'
  status: 'registered'
  errorCode: null
  input: {
    id: string
    jobId: string
    role: 'unclassified'
    originalName: string
    managedPath: string
    status: 'registered'
    createdAt: string
    updatedAt: string
  }
} {
  return {
    originalName: name,
    managedPath: `/managed/${name}`,
    role: 'unclassified' as const,
    status: 'registered' as const,
    errorCode: null,
    input: {
      id: '33333333-3333-4333-8333-333333333333',
      jobId,
      role: 'unclassified' as const,
      originalName: name,
      managedPath: `/managed/${name}`,
      status: 'registered' as const,
      createdAt: '2026-06-20T00:00:00.000Z',
      updatedAt: '2026-06-20T00:00:00.000Z'
    }
  }
}

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
    registerInputFiles.mockResolvedValue([registeredResult('voice.mp3')])
    render(<InputDropZone jobId={jobId} />)

    await user.click(screen.getByRole('button', { name: '파일 선택' }))
    expect(registerInputFiles).toHaveBeenCalledWith(jobId, [
      { name: 'voice.mp3', sourcePath: '/voice.mp3' }
    ])

    const dropped = new File(['script'], 'script.txt', { type: 'text/plain' })
    fireEvent.drop(screen.getByText(/파일을 한 번에 놓으세요/).parentElement!, {
      dataTransfer: { files: [dropped] }
    })
    await waitFor(() => expect(registerInputFiles).toHaveBeenLastCalledWith(jobId, [dropped]))
  })

  it('announces one batch summary and links each error to its file', async () => {
    const user = userEvent.setup()
    selectInputFiles.mockResolvedValue([
      { name: 'voice.mp3', sourcePath: '/voice.mp3' },
      { name: 'bad.exe', sourcePath: '/bad.exe' }
    ])
    registerInputFiles.mockResolvedValue([
      registeredResult('voice.mp3'),
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

  it('queues additional drops and displays per-file processing state', async () => {
    let resolveFirst: ((value: ReturnType<typeof registeredResult>[]) => void) | undefined
    registerInputFiles
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve
          })
      )
      .mockResolvedValueOnce([registeredResult('second.txt')])
    render(<InputDropZone jobId={jobId} />)
    const zone = screen.getByText(/파일을 한 번에 놓으세요/).parentElement!
    const first = new File(['first'], 'first.txt')
    const second = new File(['second'], 'second.txt')

    fireEvent.drop(zone, { dataTransfer: { files: [first] } })
    fireEvent.drop(zone, { dataTransfer: { files: [second] } })

    expect(screen.getByRole('list', { name: '파일 등록 처리 상태' })).toHaveTextContent(
      'first.txt등록 중'
    )
    expect(screen.getByRole('list', { name: '파일 등록 처리 상태' })).toHaveTextContent(
      'second.txt등록 중'
    )
    await waitFor(() => expect(registerInputFiles).toHaveBeenCalledTimes(1))

    resolveFirst?.([registeredResult('first.txt')])
    await waitFor(() => expect(registerInputFiles).toHaveBeenCalledTimes(2))
  })

  it('clears old results and ignores stale completion after the job changes', async () => {
    let resolveRegistration: ((value: ReturnType<typeof registeredResult>[]) => void) | undefined
    selectInputFiles.mockResolvedValue([{ name: 'voice.mp3', sourcePath: '/voice.mp3' }])
    registerInputFiles.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRegistration = resolve
        })
    )
    const { rerender } = render(<InputDropZone jobId={jobId} />)

    await userEvent.setup().click(screen.getByRole('button', { name: '파일 선택' }))
    rerender(<InputDropZone jobId={nextJobId} />)
    resolveRegistration?.([registeredResult('voice.mp3')])

    await waitFor(() => expect(screen.queryByText('voice.mp3')).not.toBeInTheDocument())
    expect(screen.queryByText(/파일 등록 완료/)).not.toBeInTheDocument()
  })

  it('reports file-picker failures', async () => {
    selectInputFiles.mockRejectedValue(new Error('dialog failed'))
    render(<InputDropZone jobId={jobId} />)

    await userEvent.setup().click(screen.getByRole('button', { name: '파일 선택' }))

    expect(screen.getByText('파일 선택을 완료하지 못했습니다. 다시 시도해주세요.')).toBeVisible()
  })

  it('provides drag-entry feedback', () => {
    render(<InputDropZone jobId={jobId} />)
    const zone = screen.getByText(/파일을 한 번에 놓으세요/).parentElement!

    fireEvent.dragEnter(zone)
    expect(zone).toHaveAttribute('data-drag-active', 'true')
    fireEvent.dragLeave(zone)
    expect(zone).not.toHaveAttribute('data-drag-active')
  })

  it('replaces the live region for identical consecutive summaries', async () => {
    selectInputFiles.mockResolvedValue([{ name: 'voice.mp3', sourcePath: '/voice.mp3' }])
    registerInputFiles.mockResolvedValue([registeredResult('voice.mp3')])
    render(<InputDropZone jobId={jobId} />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: '파일 선택' }))
    const firstAnnouncement = screen.getByText('파일 등록 완료: 성공 1개, 거부 0개')
    await user.click(screen.getByRole('button', { name: '파일 선택' }))

    await waitFor(() => {
      expect(screen.getByText('파일 등록 완료: 성공 1개, 거부 0개')).not.toBe(firstAnnouncement)
    })
  })
})
