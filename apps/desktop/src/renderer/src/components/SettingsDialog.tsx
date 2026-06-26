import type { ResourceDto, ResourceType } from '@gracetree/contracts'
import { useEffect, useRef, useState } from 'react'

import { useFocusTrap } from '../hooks/useFocusTrap'
import styles from '../styles/App.module.css'

interface ResourceRowConfig {
  type: ResourceType
  label: string
  formats: string
}

const RESOURCE_ROWS: ResourceRowConfig[] = [
  { type: 'title_scripture_video', label: '제목·말씀 영상', formats: 'MP4, MOV' },
  { type: 'prayer_loop_video', label: '기도 영상', formats: 'MP4, MOV' },
  { type: 'default_bgm', label: '기본 BGM', formats: 'MP3, WAV, AAC' },
  { type: 'subtitle_font', label: '자막 폰트', formats: 'TTF, OTF' },
]

function basename(filePath: string | null): string {
  if (!filePath) return ''
  return filePath.replace(/\\/g, '/').split('/').pop() ?? filePath
}

function statusLabel(status: ResourceDto['status']): string {
  if (status === 'ready') return '준비'
  if (status === 'invalid') return '오류'
  return '미등록'
}

function statusIcon(status: ResourceDto['status']): string {
  if (status === 'ready') return '✓'
  if (status === 'invalid') return '⚠'
  return '✗'
}

interface SettingsDialogProps {
  managedRoot: string
  onClose: () => void
}

export function SettingsDialog({ managedRoot, onClose }: SettingsDialogProps): React.JSX.Element {
  const [resources, setResources] = useState<ResourceDto[]>([])
  const [rowErrors, setRowErrors] = useState<Partial<Record<ResourceType, string>>>({})
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const firstSelectButtonRef = useRef<HTMLButtonElement>(null)
  const handleKeyDown = useFocusTrap(dialogRef, onClose)

  // Load resources when dialog opens
  useEffect(() => {
    if (!managedRoot) return
    window.desktopApi
      .getResources(managedRoot)
      .then((loaded) => setResources(loaded))
      .catch(() => {
        // silently ignore — rows will show default missing state
      })
  }, [managedRoot])

  // Focus first select button on mount
  useEffect(() => {
    firstSelectButtonRef.current?.focus()
  }, [])

  const handleSelectFile = async (type: ResourceType): Promise<void> => {
    try {
      const selected = await window.desktopApi.selectResourceFile(type)
      if (!selected) return

      const result = await window.desktopApi.updateResource(type, selected.sourcePath, managedRoot)
      setResources(result.resources)

      if (result.error) {
        setRowErrors((current) => ({
          ...current,
          [type]: result.error!.message,
        }))
      } else {
        setRowErrors((current) => {
          const next = { ...current }
          delete next[type]
          return next
        })
      }
    } catch {
      setRowErrors((current) => ({
        ...current,
        [type]: '파일 처리 중 오류가 발생했습니다.',
      }))
    }
  }

  const getResource = (type: ResourceType): ResourceDto | undefined =>
    resources.find((r) => r.type === type)

  return (
    <div className={styles.dialogBackdrop}>
      <div
        aria-labelledby="resource-settings-title"
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <div className={styles.dialogHeader}>
          <div>
            <p className={styles.eyebrow}>설정</p>
            <h2 id="resource-settings-title">공통 리소스 설정</h2>
          </div>
          {/* 닫기 버튼은 시각적으로 헤더 우측에 위치하며, DOM 순서는 파일 선택 버튼들 이후에 옵니다 */}
        </div>

        <ul aria-label="공통 리소스 목록" className={styles.resourceList}>
          {RESOURCE_ROWS.map((row, index) => {
            const resource = getResource(row.type)
            const status = resource?.status ?? 'missing'
            const fileName = resource?.managedPath ? basename(resource.managedPath) : null
            const errorMessage = rowErrors[row.type]

            return (
              <li
                aria-label={`${row.label} — ${statusLabel(status)}`}
                className={styles.resourceRow}
                key={row.type}
              >
                <div className={styles.resourceRowMain}>
                  <div className={styles.resourceInfo}>
                    <span className={styles.resourceLabel}>{row.label}</span>
                    <span className={styles.resourceFormats}>{row.formats}</span>
                  </div>
                  <div className={styles.resourceStatus} data-status={status}>
                    <span aria-hidden="true" className={styles.resourceStatusIcon}>
                      {statusIcon(status)}
                    </span>
                    <span className={styles.resourceStatusText}>
                      {fileName ?? statusLabel(status)}
                    </span>
                  </div>
                  <button
                    aria-label={`${row.label} 파일 선택`}
                    className={styles.resourceSelectButton}
                    onClick={() => handleSelectFile(row.type)}
                    ref={index === 0 ? firstSelectButtonRef : undefined}
                    type="button"
                  >
                    파일 선택
                  </button>
                </div>
                {errorMessage ? (
                  <p className={styles.resourceError} role="alert">
                    {errorMessage}
                  </p>
                ) : null}
              </li>
            )
          })}
        </ul>

        {/* 닫기 버튼: DOM 순서 마지막, CSS로 우상단에 시각적 배치 */}
        <button
          aria-label="설정 닫기"
          className={`${styles.closeButton} ${styles.dialogCloseButton}`}
          onClick={onClose}
          ref={closeButtonRef}
          type="button"
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
    </div>
  )
}
