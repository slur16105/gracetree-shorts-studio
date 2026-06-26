import { useCallback } from 'react'
import type { KeyboardEvent, RefObject } from 'react'

export function useFocusTrap(
  dialogRef: RefObject<HTMLElement | null>,
  onEscape: () => void
): (event: KeyboardEvent) => void {
  return useCallback(
    (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onEscape()
        return
      }
      if (event.key === 'Tab') {
        const els = Array.from(
          dialogRef.current?.querySelectorAll<HTMLElement>(
            'button:not([disabled]):not([tabindex="-1"])'
          ) ?? []
        )
        const first = els.at(0)
        const last = els.at(-1)
        if (!first || !last) {
          event.preventDefault()
          return
        }
        const active = document.activeElement
        if (event.shiftKey && (active === first || !dialogRef.current?.contains(active))) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && (active === last || !dialogRef.current?.contains(active))) {
          event.preventDefault()
          first.focus()
        }
      }
    },
    [dialogRef, onEscape]
  )
}
