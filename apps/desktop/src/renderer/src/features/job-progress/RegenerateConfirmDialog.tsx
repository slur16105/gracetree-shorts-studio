import { useEffect, useRef } from 'react'

import { useFocusTrap } from '../../hooks/useFocusTrap'
import styles from '../../styles/App.module.css'

interface RegenerateConfirmDialogProps {
  onClose: () => void
  onConfirm: () => void
}

export function RegenerateConfirmDialog({ onClose, onConfirm }: RegenerateConfirmDialogProps): React.JSX.Element {
  const confirmButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const handleKeyDown = useFocusTrap(dialogRef, onClose)

  useEffect(() => {
    confirmButtonRef.current?.focus()
  }, [])

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="regenerate-confirm-dialog-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={styles.eyebrow}>다시 생성</p>
            <h2 id="regenerate-confirm-dialog-title">영상을 다시 생성하시겠습니까?</h2>
          </div>
        </div>

        <p className={styles.dialogDescription}>
          새 영상 생성에 성공하면 기존 완료 영상이 교체됩니다.
          생성이 실패하거나 취소되면 기존 완료 영상과 기록이 유지됩니다.
        </p>

        <div className={styles.resultDialogActions}>
          <button
            onClick={onClose}
            type="button"
          >
            취소
          </button>
          <button
            className={styles.primaryButton}
            onClick={onConfirm}
            ref={confirmButtonRef}
            type="button"
          >
            다시 생성
          </button>
        </div>
      </div>
    </div>
  )
}
