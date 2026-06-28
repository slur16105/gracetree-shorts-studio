import type { InputFileCandidate, SelectedInputFile } from '@gracetree/contracts/desktop-api'
import type { InputRegistrationResult, InputRole, JobInputDto } from '@gracetree/contracts'
import { useEffect, useRef, useState, type DragEvent } from 'react'

import { showToast, type ToastTone } from '../../components/toast-store'
import styles from './InputDropZone.module.css'
import { FileSlot, MissingFileSlot } from './FileSlot'

const REQUIRED_ROLES = ['thumbnail', 'voice', 'script'] as const

interface InputDropZoneProps {
  jobId: string | null
  initialInputs?: JobInputDto[]
  onInputsChanged?: (inputs: JobInputDto[]) => void
}

const ERROR_MESSAGES: Record<Exclude<InputRegistrationResult['errorCode'], null>, string> = {
  UNSUPPORTED_TYPE: '지원하지 않는 파일 형식입니다.',
  SOURCE_UNREADABLE: '파일을 읽을 수 없습니다. 다시 선택해주세요.',
  SOURCE_INSIDE_MANAGED_ROOT: '앱 관리 폴더의 파일은 다시 등록할 수 없습니다.',
  SYMLINK_NOT_ALLOWED: '바로가기 또는 심볼릭 링크는 등록할 수 없습니다.',
  FILE_TOO_LARGE: '파일 크기가 허용 범위를 초과했습니다.',
  NAME_CONFLICT: '같은 이름의 파일이 이미 있습니다. 교체는 다음 단계에서 지원됩니다.',
  COPY_FAILED: '파일 복사에 실패했습니다. 다시 선택해주세요.'
}

export function InputDropZone({
  jobId,
  initialInputs = [],
  onInputsChanged
}: InputDropZoneProps): React.JSX.Element {
  return (
    <InputDropZoneContent
      initialInputs={initialInputs}
      jobId={jobId}
      key={jobId ?? 'no-job'}
      onInputsChanged={onInputsChanged}
    />
  )
}

function InputDropZoneContent({
  jobId,
  initialInputs = [],
  onInputsChanged
}: InputDropZoneProps): React.JSX.Element {
  const [results, setResults] = useState<InputRegistrationResult[]>([])
  const [inputs, setInputs] = useState<JobInputDto[]>(initialInputs)
  const onInputsChangedRef = useRef(onInputsChanged)
  const [pendingFiles, setPendingFiles] = useState<Array<{ id: string; name: string }>>([])
  const [dragActive, setDragActive] = useState(false)
  const activeRef = useRef(true)
  const queueRef = useRef(Promise.resolve())
  const batchSequenceRef = useRef(0)
  const dragDepthRef = useRef(0)

  useEffect(() => {
    onInputsChangedRef.current = onInputsChanged
  })

  useEffect(() => {
    // Re-affirm on setup so React StrictMode's mount→unmount→mount cycle (which
    // fires the cleanup once before the real mount) does not leave activeRef
    // permanently false — that would make every post-registration state update
    // (and the pending-file cleanup) silently no-op, freezing files on "등록 중".
    activeRef.current = true
    return () => {
      activeRef.current = false
    }
  }, [])

  // 등록 결과 같은 일회성 안내는 하단 토스트로 보여준다.
  const announce = (text: string, tone: ToastTone = 'info'): void => {
    showToast(text, tone)
  }

  const updateInputs = (nextInputs: JobInputDto[]): void => {
    setInputs(nextInputs)
    onInputsChangedRef.current?.(nextInputs)
  }

  const register = (files: InputFileCandidate[]): Promise<void> => {
    if (!jobId || files.length === 0) return Promise.resolve()
    const requestJobId = jobId
    const batchId = `${requestJobId}-${batchSequenceRef.current++}`
    const pending = files.map((file, index) => ({
      id: `${batchId}-${index}`,
      name: file.name
    }))
    setPendingFiles((current) => [...current, ...pending])

    const execute = async (): Promise<void> => {
      try {
        const batch = await window.desktopApi.registerInputFiles(requestJobId, files)
        if (!activeRef.current) return
        setResults(batch.results)
        if (batch.inputs) updateInputs(batch.inputs)
        // 등록 성공은 슬롯에 파일명이 바로 보이므로 별도 안내를 띄우지 않는다.
      } catch {
        if (activeRef.current) {
          announce('파일 등록을 완료하지 못했습니다. 다시 선택해주세요.', 'danger')
        }
      } finally {
        if (activeRef.current) {
          const pendingIds = new Set(pending.map((file) => file.id))
          setPendingFiles((current) => current.filter((file) => !pendingIds.has(file.id)))
        }
      }
    }

    const queued = queueRef.current.then(execute, execute)
    queueRef.current = queued
    return queued
  }

  const assignRole = async (inputId: string, role: InputRole): Promise<void> => {
    if (!jobId) return
    updateInputs(await window.desktopApi.assignInputRole(jobId, inputId, role))
  }

  const removeInput = async (inputId: string): Promise<void> => {
    if (!jobId) return
    updateInputs(await window.desktopApi.removeInput(jobId, inputId))
  }

  const replaceInput = async (inputId: string, file: InputFileCandidate): Promise<void> => {
    if (!jobId) return
    updateInputs(await window.desktopApi.replaceInput(jobId, inputId, file))
  }
  const occupiedRoles = new Set(inputs.map((input) => input.role))
  const requiredMissing = REQUIRED_ROLES.filter((role) => !occupiedRoles.has(role))
  const bgmInputs = inputs.filter((input) => input.role === 'bgm')
  const nonBgmInputs = inputs.filter((input) => input.role !== 'bgm')
  // 등록 성공은 슬롯으로 보이므로, 결과 리스트엔 거부된 파일만 남긴다.
  const rejectedResults = results.filter((result) => result.status !== 'registered')

  const selectFiles = async (): Promise<void> => {
    if (!jobId) return
    try {
      const selected: SelectedInputFile[] = await window.desktopApi.selectInputFiles()
      await register(selected)
    } catch {
      announce('파일 선택을 완료하지 못했습니다. 다시 시도해주세요.', 'danger')
    }
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>): Promise<void> => {
    event.preventDefault()
    dragDepthRef.current = 0
    setDragActive(false)
    await register(Array.from(event.dataTransfer.files))
  }

  return (
    <section aria-label="입력 파일" className={styles.section}>
      <div
        className={styles.dropZone}
        data-disabled={!jobId || undefined}
        data-drag-active={dragActive || undefined}
        onDragEnter={(event) => {
          event.preventDefault()
          dragDepthRef.current += 1
          setDragActive(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
          if (dragDepthRef.current === 0) setDragActive(false)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        data-testid="dropzone"
      >
        {jobId ? (
          <>
            <div className={styles.dzHead}>
              <span aria-hidden="true" className={styles.dzIcon}>
                <svg
                  fill="none"
                  height="18"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  width="18"
                >
                  <path d="M12 16V4" />
                  <path d="M7 9l5-5 5 5" />
                  <path d="M5 20h14" />
                </svg>
              </span>
              <div className={styles.dzHeadText}>
                <div className={styles.dzTitle}>파일 {inputs.length}개</div>
                <div className={styles.dzSub}>끌어다 놓거나 선택해 등록·교체할 수 있어요</div>
              </div>
              <button className={styles.dzSelect} disabled={!jobId} onClick={selectFiles} type="button">
                파일 선택
              </button>
            </div>
            <ul aria-label="파일 슬롯" className={styles.slots}>
              {requiredMissing.map((role) => (
                <MissingFileSlot key={role} role={role} />
              ))}
              {nonBgmInputs.map((input) => (
                <FileSlot
                  input={input}
                  key={input.id}
                  onAssignRole={assignRole}
                  onRemove={removeInput}
                  onReplace={replaceInput}
                />
              ))}
              {bgmInputs.length === 0 ? <MissingFileSlot key="bgm" optional role="bgm" /> : null}
              {bgmInputs.map((input) => (
                <FileSlot
                  input={input}
                  key={input.id}
                  onAssignRole={assignRole}
                  onRemove={removeInput}
                  onReplace={replaceInput}
                  optional
                />
              ))}
            </ul>
          </>
        ) : (
          <div className={styles.dzEmpty}>
            <p>썸네일, 음성, 영상, 스크립트 파일을 한 번에 놓으세요.</p>
            <button disabled={!jobId} onClick={selectFiles} type="button">
              파일 선택
            </button>
          </div>
        )}
      </div>
      {pendingFiles.length > 0 ? (
        <ul aria-label="파일 등록 처리 상태" className={styles.results}>
          {pendingFiles.map((file) => (
            <li className={styles.result} key={file.id}>
              <span>{file.name}</span>
              <strong>등록 중</strong>
            </li>
          ))}
        </ul>
      ) : null}
      {rejectedResults.length > 0 ? (
        <ul aria-label="파일 등록 결과" className={styles.results}>
          {rejectedResults.map((result, index) => {
            const errorId = `input-error-${index}`
            return (
              <li
                aria-describedby={result.errorCode ? errorId : undefined}
                className={styles.result}
                key={`${result.originalName}-${index}`}
              >
                <span>{result.originalName}</span>
                <strong>{result.status === 'conflict' ? '충돌' : '거부됨'}</strong>
                {result.errorCode ? (
                  <span className={styles.error} id={errorId}>
                    {ERROR_MESSAGES[result.errorCode]}
                  </span>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}
      {rejectedResults.length > 0 ? (
        <button className={styles.retry} onClick={selectFiles} type="button">
          파일 다시 선택
        </button>
      ) : null}
    </section>
  )
}
