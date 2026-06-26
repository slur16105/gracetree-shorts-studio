import { useEffect, useRef, type KeyboardEvent } from 'react'

import styles from '../../styles/App.module.css'

interface ResultDialogProps {
  title: string | null
  publishDate: string
  completedAt: string
  resultPath: string
  onClose: () => void
}

function formatDate(isoString: string): string {
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return isoString
  return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function ResultDialog({
  title,
  publishDate,
  completedAt,
  resultPath,
  onClose
}: ResultDialogProps): React.JSX.Element {
  const confirmButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    confirmButtonRef.current?.focus()
  }, [])

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }

    if (event.key === 'Tab') {
      const focusableElements = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]):not([tabindex="-1"])'
        ) ?? []
      )
      const first = focusableElements.at(0)
      const last = focusableElements.at(-1)
      if (!first || !last) {
        event.preventDefault()
        return
      }
      const activeElement = document.activeElement
      if (
        event.shiftKey &&
        (activeElement === first || !dialogRef.current?.contains(activeElement))
      ) {
        event.preventDefault()
        last.focus()
      } else if (
        !event.shiftKey &&
        (activeElement === last || !dialogRef.current?.contains(activeElement))
      ) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="result-dialog-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={styles.eyebrow}>생성 완료</p>
            <h2 id="result-dialog-title">영상이 완성되었습니다</h2>
          </div>
        </div>

        {title ? <p className={styles.dialogDescription}>{title}</p> : null}

        <dl className={styles.resultMeta}>
          <dt>게시 날짜</dt>
          <dd>{formatDate(publishDate)}</dd>
          <dt>실제 생성일</dt>
          <dd>{formatDate(completedAt)}</dd>
          <dt>결과 위치</dt>
          <dd>{resultPath}</dd>
        </dl>

        <div className={styles.resultDialogActions}>
          <button
            className={styles.primaryButton}
            onClick={onClose}
            ref={confirmButtonRef}
            type="button"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  )
}
