import type { InputFileCandidate } from '@gracetree/contracts/desktop-api'
import type { InputRole, JobInputDto } from '@gracetree/contracts'
import { useEffect, useRef, useState } from 'react'

import styles from './InputDropZone.module.css'

const ROLE_LABELS: Record<InputRole, string> = {
  thumbnail: '썸네일',
  voice: '음성',
  bgm: '작업별 BGM',
  script: '스크립트',
  unclassified: '미분류'
}

export function MissingFileSlot({
  role
}: {
  role: Exclude<InputRole, 'unclassified'>
}): React.JSX.Element {
  return (
    <li className={styles.fileSlot} data-state="missing">
      <span aria-hidden="true" className={styles.stateIcon}>
        −
      </span>
      <div className={styles.slotDetails}>
        <strong>{ROLE_LABELS[role]}</strong>
        <span>파일 없음</span>
        <span className={styles.stateText}>누락 · 파일을 등록하세요</span>
      </div>
    </li>
  )
}

const STATE_LABELS: Record<JobInputDto['status'], { icon: string; text: string }> = {
  ready: { icon: '✓', text: '정상' },
  conflict: { icon: '!', text: '충돌 · 같은 역할 후보 중 하나를 제거하세요' },
  unclassified: { icon: '?', text: '미분류 · 역할을 선택하거나 제거하세요' },
  invalid: { icon: '×', text: '오류 · 파일을 교체하거나 제거하세요' }
}

interface FileSlotProps {
  input: JobInputDto
  onAssignRole(inputId: string, role: InputRole): Promise<void>
  onRemove(inputId: string): Promise<void>
  onReplace(inputId: string, file: InputFileCandidate): Promise<void>
}

export function FileSlot({
  input,
  onAssignRole,
  onRemove,
  onReplace
}: FileSlotProps): React.JSX.Element {
  const [confirmation, setConfirmation] = useState<'remove' | 'replace' | null>(null)
  const [replacement, setReplacement] = useState<InputFileCandidate | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const removeButtonRef = useRef<HTMLButtonElement>(null)
  const replaceButtonRef = useRef<HTMLButtonElement>(null)
  const restoreTarget = useRef<'remove' | 'replace' | null>(null)
  const state = STATE_LABELS[input.status]

  useEffect(() => {
    if (confirmation !== null || restoreTarget.current === null) return
    const target = restoreTarget.current
    restoreTarget.current = null
    ;(target === 'remove' ? removeButtonRef.current : replaceButtonRef.current)?.focus()
  }, [confirmation])

  const cancelConfirmation = (): void => {
    setReplacement(null)
    setConfirmation(null)
  }

  const chooseReplacement = async (): Promise<void> => {
    restoreTarget.current = 'replace'
    try {
      const selected = await window.desktopApi.selectInputFiles()
      if (selected[0]) {
        setReplacement(selected[0])
        setConfirmation('replace')
      } else {
        restoreTarget.current = null
      }
    } catch {
      setError('교체할 파일을 선택하지 못했습니다.')
      restoreTarget.current = null
    }
  }

  const runAction = async (): Promise<void> => {
    setBusy(true)
    setError('')
    try {
      if (confirmation === 'remove') {
        await onRemove(input.id)
      } else if (replacement) {
        await onReplace(input.id, replacement)
      }
      setReplacement(null)
      setConfirmation(null)
    } catch {
      setError(
        confirmation === 'remove'
          ? '파일을 제거하지 못했습니다. 기존 입력은 유지됩니다.'
          : '파일을 교체하지 못했습니다. 기존 입력은 유지됩니다.'
      )
      setConfirmation(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={styles.fileSlot} data-state={input.status}>
      <span aria-hidden="true" className={styles.stateIcon}>
        {state.icon}
      </span>
      <div className={styles.slotDetails}>
        <strong>{ROLE_LABELS[input.role]}</strong>
        <span>{input.originalName}</span>
        <span className={styles.stateText}>{state.text}</span>
      </div>
      <label className={styles.roleControl}>
        <span>역할</span>
        <select
          aria-label={`${input.originalName} 역할`}
          disabled={busy}
          onChange={async (event) => {
            setBusy(true)
            setError('')
            try {
              await onAssignRole(input.id, event.target.value as InputRole)
            } catch {
              setError('역할을 변경하지 못했습니다.')
            } finally {
              setBusy(false)
            }
          }}
          value={input.role}
        >
          {Object.entries(ROLE_LABELS).map(([role, label]) => (
            <option key={role} value={role}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <div className={styles.slotActions}>
        <button
          aria-label={`${input.originalName} 교체`}
          disabled={busy}
          onClick={chooseReplacement}
          ref={replaceButtonRef}
          type="button"
        >
          교체
        </button>
        <button
          aria-label={`${input.originalName} 제거`}
          disabled={busy}
          onClick={() => {
            restoreTarget.current = 'remove'
            setConfirmation('remove')
          }}
          ref={removeButtonRef}
          type="button"
        >
          제거
        </button>
      </div>
      {confirmation ? (
        <div className={styles.confirmation} role="group" aria-label={`${input.originalName} 확인`}>
          <span>
            {confirmation === 'remove'
              ? '관리 사본을 제거할까요? 원본 파일은 변경하지 않습니다.'
              : `${replacement?.name ?? '선택한 파일'}로 교체할까요?`}
          </span>
          <button disabled={busy} onClick={cancelConfirmation} type="button">
            취소
          </button>
          <button disabled={busy} onClick={runAction} type="button">
            {confirmation === 'remove' ? '제거 확인' : '교체 확인'}
          </button>
        </div>
      ) : null}
      {error ? (
        <p aria-live="polite" className={styles.error}>
          {error}
        </p>
      ) : null}
    </li>
  )
}
