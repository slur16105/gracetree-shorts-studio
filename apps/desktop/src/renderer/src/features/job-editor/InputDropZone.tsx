import type { InputFileCandidate, SelectedInputFile } from '@gracetree/contracts/desktop-api'
import type { InputRegistrationResult, InputRole, JobInputDto } from '@gracetree/contracts'
import { useEffect, useRef, useState, type DragEvent } from 'react'

import styles from './InputDropZone.module.css'
import { FileSlot, MissingFileSlot } from './FileSlot'

interface InputDropZoneProps {
  jobId: string | null
  initialInputs?: JobInputDto[]
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

const SLOT_ROLES = ['thumbnail', 'voice', 'script', 'bgm'] as const

export function InputDropZone({
  jobId,
  initialInputs = []
}: InputDropZoneProps): React.JSX.Element {
  return (
    <InputDropZoneContent initialInputs={initialInputs} jobId={jobId} key={jobId ?? 'no-job'} />
  )
}

function InputDropZoneContent({
  jobId,
  initialInputs = []
}: InputDropZoneProps): React.JSX.Element {
  const [results, setResults] = useState<InputRegistrationResult[]>([])
  const [inputs, setInputs] = useState<JobInputDto[]>(initialInputs)
  const [summary, setSummary] = useState({ id: 0, text: '' })
  const [pendingFiles, setPendingFiles] = useState<Array<{ id: string; name: string }>>([])
  const [dragActive, setDragActive] = useState(false)
  const activeRef = useRef(true)
  const queueRef = useRef(Promise.resolve())
  const batchSequenceRef = useRef(0)
  const dragDepthRef = useRef(0)

  useEffect(() => {
    return () => {
      activeRef.current = false
    }
  }, [])

  const announce = (text: string): void => {
    setSummary((current) => ({ id: current.id + 1, text }))
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
        if (batch.inputs) setInputs(batch.inputs)
        const nextResults = batch.results
        const successCount = nextResults.filter((item) => item.status === 'registered').length
        const rejectedCount = nextResults.length - successCount
        announce(`파일 등록 완료: 성공 ${successCount}개, 거부 ${rejectedCount}개`)
      } catch {
        if (activeRef.current) {
          announce('파일 등록을 완료하지 못했습니다. 다시 선택해주세요.')
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
    setInputs(await window.desktopApi.assignInputRole(jobId, inputId, role))
  }

  const removeInput = async (inputId: string): Promise<void> => {
    if (!jobId) return
    setInputs(await window.desktopApi.removeInput(jobId, inputId))
  }

  const replaceInput = async (inputId: string, file: InputFileCandidate): Promise<void> => {
    if (!jobId) return
    setInputs(await window.desktopApi.replaceInput(jobId, inputId, file))
  }
  const occupiedRoles = new Set(inputs.map((input) => input.role))

  const selectFiles = async (): Promise<void> => {
    if (!jobId) return
    try {
      const selected: SelectedInputFile[] = await window.desktopApi.selectInputFiles()
      await register(selected)
    } catch {
      announce('파일 선택을 완료하지 못했습니다. 다시 시도해주세요.')
    }
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>): Promise<void> => {
    event.preventDefault()
    dragDepthRef.current = 0
    setDragActive(false)
    await register(Array.from(event.dataTransfer.files))
  }

  return (
    <section aria-labelledby="input-files-title" className={styles.section}>
      <h3 id="input-files-title">입력 파일</h3>
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
      >
        <p>썸네일, 음성, 영상, 스크립트 파일을 한 번에 놓으세요.</p>
        <button disabled={!jobId} onClick={selectFiles} type="button">
          파일 선택
        </button>
      </div>
      <p aria-atomic="true" aria-live="polite" className={styles.summary} key={summary.id}>
        {summary.text}
      </p>
      {jobId ? (
        <ul aria-label="파일 슬롯" className={styles.slots}>
          {SLOT_ROLES.filter((role) => !occupiedRoles.has(role)).map((role) => (
            <MissingFileSlot key={role} role={role} />
          ))}
          {inputs.map((input) => (
            <FileSlot
              input={input}
              key={input.id}
              onAssignRole={assignRole}
              onRemove={removeInput}
              onReplace={replaceInput}
            />
          ))}
        </ul>
      ) : null}
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
      {results.length > 0 ? (
        <ul aria-label="파일 등록 결과" className={styles.results}>
          {results.map((result, index) => {
            const errorId = `input-error-${index}`
            return (
              <li
                aria-describedby={result.errorCode ? errorId : undefined}
                className={styles.result}
                key={`${result.originalName}-${index}`}
              >
                <span>{result.originalName}</span>
                <strong>
                  {result.status === 'registered'
                    ? '등록됨'
                    : result.status === 'conflict'
                      ? '충돌'
                      : '거부됨'}
                </strong>
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
      {results.some((result) => result.status !== 'registered') ? (
        <button className={styles.retry} onClick={selectFiles} type="button">
          파일 다시 선택
        </button>
      ) : null}
    </section>
  )
}
