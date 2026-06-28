import { useEffect } from 'react'

import { dismissToast, useToast } from './toast-store'
import styles from './Toast.module.css'

const TOAST_DURATION_MS = 3500

export function Toast(): React.JSX.Element | null {
  const toast = useToast()

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => dismissToast(toast.id), TOAST_DURATION_MS)
    return () => window.clearTimeout(timer)
  }, [toast])

  if (!toast) return null

  return (
    <div aria-atomic="true" aria-live="polite" className={styles.region}>
      <div className={styles.toast} data-tone={toast.tone} key={toast.id}>
        {toast.message}
      </div>
    </div>
  )
}
