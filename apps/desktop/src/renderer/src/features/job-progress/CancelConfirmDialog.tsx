import { useEffect, useRef } from 'react'

import { useFocusTrap } from '../../hooks/useFocusTrap'
import styles from '../../styles/App.module.css'

interface CancelConfirmDialogProps {
  onClose: () => void
  onConfirm: () => void
}

export function CancelConfirmDialog({ onClose, onConfirm }: CancelConfirmDialogProps): React.JSX.Element {
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const handleKeyDown = useFocusTrap(dialogRef, onClose)

  useEffect(() => {
    cancelButtonRef.current?.focus()
  }, [])

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="cancel-confirm-dialog-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={styles.eyebrow}>작업 취소</p>
            <h2 id="cancel-confirm-dialog-title">생성을 취소하시겠습니까?</h2>
          </div>
        </div>

        <p className={styles.dialogDescription}>
          취소하면 현재 진행 중인 생성이 중단되고 임시 파일이 정리됩니다.
          기존 완료 결과와 입력 파일은 변경되지 않습니다.
        </p>

        <div className={styles.resultDialogActions}>
          <button
            className={styles.secondaryButton}
            onClick={onClose}
            ref={cancelButtonRef}
            type="button"
          >
            계속 진행
          </button>
          <button
            className={styles.primaryButton}
            onClick={onConfirm}
            type="button"
          >
            작업 취소
          </button>
        </div>
      </div>
    </div>
  )
}
