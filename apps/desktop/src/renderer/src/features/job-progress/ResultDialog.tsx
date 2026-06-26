import { useEffect, useRef } from 'react'

import { useFocusTrap } from '../../hooks/useFocusTrap'
import { formatDate } from '../../utils/format-date'
import styles from '../../styles/App.module.css'

interface ResultDialogProps {
  title: string | null
  publishDate: string
  completedAt: string
  resultPath: string
  onClose: () => void
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
  const handleKeyDown = useFocusTrap(dialogRef, onClose)

  useEffect(() => {
    confirmButtonRef.current?.focus()
  }, [])

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
