import { useEffect, useRef } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { stageLabel } from './error-labels'
import styles from '../../styles/App.module.css'

interface FailedResultDialogProps {
  jobId: string
  attemptId: string
  errorCode: string
  message: string
  stageId: string | null
  recoverable: boolean
  details: string | null
  onClose: () => void
  onOpenSettings: () => void
}

export function FailedResultDialog({
  jobId,
  attemptId,
  message,
  stageId,
  recoverable,
  onClose,
}: FailedResultDialogProps): React.JSX.Element {
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const handleKeyDown = useFocusTrap(dialogRef, onClose)

  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  const handleOpenLog = (): void => {
    window.desktopApi.openLogFolder(jobId, attemptId).catch((err: unknown) => {
      console.error('로그 폴더를 열 수 없습니다:', err)
    })
  }

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="failed-dialog-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={`${styles.eyebrow} ${styles.failStage}`}>{stageLabel(stageId)}</p>
            <h2 id="failed-dialog-title">영상 생성에 실패했습니다</h2>
          </div>
        </div>

        <div className={styles.errorBanner}>
          <p className={styles.errorBannerTitle}>{message}</p>
        </div>

        <div className={styles.failedDialogActions}>
          <button
            className={recoverable ? styles.primaryButton : styles.secondaryButton}
            onClick={onClose}
            ref={closeButtonRef}
            type="button"
          >
            {recoverable ? '입력 수정' : '닫기'}
          </button>
          <button className={styles.secondaryButton} onClick={handleOpenLog} type="button">
            로그 폴더
          </button>
        </div>
      </div>
    </div>
  )
}
