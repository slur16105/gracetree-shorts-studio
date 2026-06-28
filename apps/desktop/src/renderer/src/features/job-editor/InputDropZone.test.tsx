import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type {
  InputRegistrationResult,
  JobInputDto,
  RegisteredInputResult
} from '@gracetree/contracts'
import type { InputRegistrationBatch } from '@gracetree/contracts/desktop-api'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { InputDropZone } from './InputDropZone'
import { showToast } from '../../components/toast-store'

vi.mock('../../components/toast-store', () => ({ showToast: vi.fn() }))

const jobId = '11111111-1111-4111-8111-111111111111'
const nextJobId = '22222222-2222-4222-8222-222222222222'

function registeredResult(name: string): RegisteredInputResult {
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
      status: 'ready' as const,
      createdAt: '2026-06-20T00:00:00.000Z',
      updatedAt: '2026-06-20T00:00:00.000Z'
    }
  }
}

function batch(results: InputRegistrationResult[]): InputRegistrationBatch {
  return {
    results,
    inputs: results.flatMap((result) => ('input' in result && result.input ? [result.input] : []))
  }
}

function inputDto(
  name: string,
  role: 'thumbnail' | 'voice' | 'bgm' | 'script' | 'unclassified',
  status: 'ready' | 'conflict' | 'unclassified' | 'invalid' = 'ready'
): JobInputDto {
  return {
    id: '33333333-3333-4333-8333-333333333333',
    jobId,
    role,
    originalName: name,
    managedPath: `/managed/${name}`,
    status,
    createdAt: '2026-06-20T00:00:00.000Z',
    updatedAt: '2026-06-20T00:00:00.000Z'
  }
}

describe('InputDropZone', () => {
  const selectInputFiles = vi.fn()
  const registerInputFiles = vi.fn()
  const assignInputRole = vi.fn()
  const removeInput = vi.fn()
  const replaceInput = vi.fn()

  beforeEach(() => {
    selectInputFiles.mockReset()
    registerInputFiles.mockReset()
    assignInputRole.mockReset()
    removeInput.mockReset()
    replaceInput.mockReset()
    vi.mocked(showToast).mockClear()
    Object.defineProperty(window, 'desktopApi', {
      configurable: true,
      value: {
        getOrCreateJobForDate: vi.fn(),
        selectInputFiles,
        registerInputFiles,
        assignInputRole,
        removeInput,
        replaceInput
      }
    })
  })

  it('uses the same registration API for click and drop batches', async () => {
    const user = userEvent.setup()
    selectInputFiles.mockResolvedValue([{ name: 'voice.mp3', sourcePath: '/voice.mp3' }])
    registerInputFiles.mockResolvedValue(batch([registeredResult('voice.mp3')]))
    render(<InputDropZone jobId={jobId} />)

    await user.click(screen.getByRole('button', { name: '파일 선택' }))
    expect(registerInputFiles).toHaveBeenCalledWith(jobId, [
      { name: 'voice.mp3', sourcePath: '/voice.mp3' }
    ])

    const dropped = new File(['script'], 'script.txt', { type: 'text/plain' })
    fireEvent.drop(screen.getByTestId('dropzone'), {
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
    registerInputFiles.mockResolvedValue(
      batch([
        registeredResult('voice.mp3'),
        {
          originalName: 'bad.exe',
          managedPath: null,
          role: 'unclassified',
          status: 'rejected',
          errorCode: 'UNSUPPORTED_TYPE'
        }
      ])
    )
    render(<InputDropZone jobId={jobId} />)

    await user.click(screen.getByRole('button', { name: '파일 선택' }))

    const rejected = (await screen.findByText('bad.exe')).closest('li')
    expect(rejected).toHaveAttribute('aria-describedby')
    expect(screen.getByText('지원하지 않는 파일 형식입니다.')).toBeVisible()
    expect(screen.getByRole('button', { name: '파일 다시 선택' })).toBeVisible()
  })

  it('keeps selection disabled until a job is available', () => {
    render(<InputDropZone jobId={null} />)
    expect(screen.getByRole('button', { name: '파일 선택' })).toBeDisabled()
  })

  it('queues additional drops and displays per-file processing state', async () => {
    let resolveFirst: ((value: ReturnType<typeof batch>) => void) | undefined
    registerInputFiles
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve
          })
      )
      .mockResolvedValueOnce(batch([registeredResult('second.txt')]))
    render(<InputDropZone jobId={jobId} />)
    const zone = screen.getByTestId('dropzone')
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

    resolveFirst?.(batch([registeredResult('first.txt')]))
    await waitFor(() => expect(registerInputFiles).toHaveBeenCalledTimes(2))
  })

  it('clears old results and ignores stale completion after the job changes', async () => {
    let resolveRegistration: ((value: ReturnType<typeof batch>) => void) | undefined
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
    resolveRegistration?.(batch([registeredResult('voice.mp3')]))

    await waitFor(() => expect(screen.queryByText('voice.mp3')).not.toBeInTheDocument())
    expect(showToast).not.toHaveBeenCalled()
  })

  it('reports file-picker failures', async () => {
    selectInputFiles.mockRejectedValue(new Error('dialog failed'))
    render(<InputDropZone jobId={jobId} />)

    await userEvent.setup().click(screen.getByRole('button', { name: '파일 선택' }))

    await waitFor(() =>
      expect(showToast).toHaveBeenCalledWith(
        '파일 선택을 완료하지 못했습니다. 다시 시도해주세요.',
        'danger'
      )
    )
  })

  it('provides drag-entry feedback', () => {
    render(<InputDropZone jobId={jobId} />)
    const zone = screen.getByTestId('dropzone')

    fireEvent.dragEnter(zone)
    expect(zone).toHaveAttribute('data-drag-active', 'true')
    fireEvent.dragLeave(zone)
    expect(zone).not.toHaveAttribute('data-drag-active')
  })

  it('does not toast on successful registration — the slot shows the file', async () => {
    selectInputFiles.mockResolvedValue([{ name: 'voice.mp3', sourcePath: '/voice.mp3' }])
    registerInputFiles.mockResolvedValue(batch([registeredResult('voice.mp3')]))
    render(<InputDropZone jobId={jobId} />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: '파일 선택' }))
    await waitFor(() => expect(registerInputFiles).toHaveBeenCalledTimes(1))

    expect(showToast).not.toHaveBeenCalled()
  })

  it('shows role, filename, and non-color state text and assigns a role by keyboard', async () => {
    const unknown = inputDto('recording.mp3', 'unclassified', 'unclassified')
    const assigned = { ...unknown, role: 'voice' as const, status: 'ready' as const }
    assignInputRole.mockResolvedValue([assigned])
    render(<InputDropZone initialInputs={[unknown]} jobId={jobId} />)

    expect(screen.getByRole('list', { name: '파일 슬롯' })).toHaveTextContent(
      '미분류recording.mp3✕미분류 · 역할을 선택하거나 제거하세요'
    )
    const roleSelect = screen.getByRole('combobox', { name: 'recording.mp3 역할' })
    roleSelect.focus()
    await userEvent.setup().selectOptions(roleSelect, 'voice')

    expect(assignInputRole).toHaveBeenCalledWith(jobId, unknown.id, 'voice')
    expect(await screen.findByText('준비됨')).toBeVisible()
  })

  it('shows missing slots with an icon and actionable text', () => {
    render(<InputDropZone initialInputs={[]} jobId={jobId} />)

    const slots = screen.getByRole('list', { name: '파일 슬롯' })
    expect(slots).toHaveTextContent('썸네일파일 없음')
    expect(slots).toHaveTextContent('음성파일 없음')
    // 작업별 BGM은 선택 항목으로 맨 아래에 표시된다
    expect(slots).toHaveTextContent('작업별 BGM선택파일 없음')
    expect(screen.getAllByText('−')).toHaveLength(3)
    expect(screen.getByText('+')).toBeInTheDocument()
  })

  it('marks duplicate candidates as conflicts without choosing an active input', () => {
    const first = inputDto('voice.first.mp3', 'voice', 'conflict')
    const second = {
      ...inputDto('voice.second.mp3', 'voice', 'conflict'),
      id: '44444444-4444-4444-8444-444444444444'
    }
    render(<InputDropZone initialInputs={[first, second]} jobId={jobId} />)

    expect(screen.getAllByText('충돌 · 같은 역할 후보 중 하나를 제거하세요')).toHaveLength(2)
    expect(screen.getAllByText('!')).toHaveLength(2)
  })

  it('requires explicit removal confirmation and restores focus on cancel', async () => {
    const input = inputDto('script.txt', 'script')
    render(<InputDropZone initialInputs={[input]} jobId={jobId} />)
    const user = userEvent.setup()
    const remove = screen.getByRole('button', { name: 'script.txt 제거' })

    await user.click(remove)
    expect(removeInput).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: '취소' }))

    expect(remove).toHaveFocus()
  })

  it('keeps the old slot visible and explains replacement failure', async () => {
    const input = inputDto('voice.mp3', 'voice')
    selectInputFiles.mockResolvedValue([{ name: 'voice-new.mp3', sourcePath: '/voice-new.mp3' }])
    replaceInput.mockRejectedValue(new Error('copy failed'))
    render(<InputDropZone initialInputs={[input]} jobId={jobId} />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'voice.mp3 교체' }))
    await user.click(screen.getByRole('button', { name: '교체 확인' }))

    expect(replaceInput).toHaveBeenCalledWith(jobId, input.id, {
      name: 'voice-new.mp3',
      sourcePath: '/voice-new.mp3'
    })
    expect(screen.getByText('voice.mp3')).toBeVisible()
    expect(screen.getByText('파일을 교체하지 못했습니다. 기존 입력은 유지됩니다.')).toBeVisible()
  })
})
