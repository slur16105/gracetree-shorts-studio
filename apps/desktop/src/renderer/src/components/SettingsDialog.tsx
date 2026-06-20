import { useEffect, useRef, type KeyboardEvent } from 'react'

import styles from '../styles/App.module.css'

interface SettingsDialogProps {
  onClose: () => void
}

export function SettingsDialog({ onClose }: SettingsDialogProps): React.JSX.Element {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }

    if (event.key === 'Tab') {
      event.preventDefault()
      closeButtonRef.current?.focus()
    }
  }

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="resource-settings-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={styles.eyebrow}>설정</p>
            <h2 id="resource-settings-title">공통 리소스 설정</h2>
          </div>
          <button
            aria-label="설정 닫기"
            className={styles.closeButton}
            onClick={onClose}
            ref={closeButtonRef}
            type="button"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <p className={styles.dialogDescription}>
          제목·말씀 영상, 기도 영상, 기본 배경음악과 자막 폰트 설정은 이후 단계에서 제공됩니다.
        </p>
      </div>
    </div>
  )
}
