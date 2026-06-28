import { useEffect, useRef } from 'react'

import { useFocusTrap } from '../../hooks/useFocusTrap'
import { formatDate } from '../../utils/format-date'
import styles from '../../styles/App.module.css'

interface ResultDialogProps {
  title: string | null
  publishDate: string
  onOpenFolder: () => void
  onClose: () => void
}

export function ResultDialog({
  title,
  publishDate,
  onOpenFolder,
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
          <h2 id="result-dialog-title">
            <span aria-hidden="true" className={styles.resultCheck}>
              ✓
            </span>{' '}
            영상이 완성되었습니다
          </h2>
        </div>

        {title ? <p className={styles.dialogDescription}>{title}</p> : null}
        <p className={styles.resultPublish}>게시 {formatDate(publishDate)}</p>

        <div className={styles.resultDialogActions}>
          <button className={styles.secondaryButton} onClick={onOpenFolder} type="button">
            폴더 열기
          </button>
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
