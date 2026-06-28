import { useSyncExternalStore } from 'react'

export type ToastTone = 'info' | 'progress' | 'warning' | 'danger'

export interface ToastState {
  id: number
  message: string
  tone: ToastTone
}

let _toast: ToastState | null = null
let _seq = 0
const _listeners = new Set<() => void>()

function _emit(): void {
  for (const listener of _listeners) listener()
}

/** Show a transient toast that slides up from the bottom and auto-dismisses. */
export function showToast(message: string, tone: ToastTone = 'info'): void {
  _toast = { id: ++_seq, message, tone }
  _emit()
}

export function dismissToast(id: number): void {
  if (_toast?.id === id) {
    _toast = null
    _emit()
  }
}

function _subscribe(listener: () => void): () => void {
  _listeners.add(listener)
  return () => _listeners.delete(listener)
}

function _getSnapshot(): ToastState | null {
  return _toast
}

export function useToast(): ToastState | null {
  return useSyncExternalStore(_subscribe, _getSnapshot)
}
