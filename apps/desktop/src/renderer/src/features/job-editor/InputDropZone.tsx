import type { InputFileCandidate, SelectedInputFile } from '@gracetree/contracts/desktop-api'
import type { InputRegistrationResult } from '@gracetree/contracts'
import { useState, type DragEvent } from 'react'

import styles from './InputDropZone.module.css'

interface InputDropZoneProps {
  jobId: string | null
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

export function InputDropZone({ jobId }: InputDropZoneProps): React.JSX.Element {
  const [results, setResults] = useState<InputRegistrationResult[]>([])
  const [summary, setSummary] = useState('')
  const [busy, setBusy] = useState(false)

  const register = async (files: InputFileCandidate[]): Promise<void> => {
    if (!jobId || files.length === 0 || busy) return
    setBusy(true)
    try {
      const nextResults = await window.desktopApi.registerInputFiles(jobId, files)
      setResults(nextResults)
      const successCount = nextResults.filter((item) => item.status === 'registered').length
      const rejectedCount = nextResults.length - successCount
      setSummary(`파일 등록 완료: 성공 ${successCount}개, 거부 ${rejectedCount}개`)
    } catch {
      setSummary('파일 등록을 완료하지 못했습니다. 다시 선택해주세요.')
    } finally {
      setBusy(false)
    }
  }

  const selectFiles = async (): Promise<void> => {
    if (!jobId || busy) return
    const selected: SelectedInputFile[] = await window.desktopApi.selectInputFiles()
    await register(selected)
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>): Promise<void> => {
    event.preventDefault()
    await register(Array.from(event.dataTransfer.files))
  }

  return (
    <section aria-labelledby="input-files-title" className={styles.section}>
      <h3 id="input-files-title">입력 파일</h3>
      <div
        className={styles.dropZone}
        data-disabled={!jobId || busy || undefined}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <p>썸네일, 음성, 영상, 스크립트 파일을 한 번에 놓으세요.</p>
        <button disabled={!jobId || busy} onClick={selectFiles} type="button">
          {busy ? '파일 등록 중…' : '파일 선택'}
        </button>
      </div>
      <p aria-atomic="true" aria-live="polite" className={styles.summary}>
        {summary}
      </p>
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
        <button className={styles.retry} disabled={busy} onClick={selectFiles} type="button">
          파일 다시 선택
        </button>
      ) : null}
    </section>
  )
}
