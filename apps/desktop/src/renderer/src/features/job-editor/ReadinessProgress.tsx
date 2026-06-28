import type { ReadinessResult } from './readiness'
import styles from './ReadinessProgress.module.css'

interface ReadinessProgressProps {
  readiness: ReadinessResult
  isParsing: boolean
  onOpenSettings?: () => void
}

export function ReadinessProgress({
  readiness,
  isParsing,
  onOpenSettings,
}: ReadinessProgressProps): React.JSX.Element {
  const { slots, satisfiedCount, total, percent, isReady, commonResourcesReady } = readiness
  const fullyReady = isReady && commonResourcesReady

  return (
    <div className={styles.container}>
      <div className={styles.cardTitle}>
        <span>입력 준비</span>
        {fullyReady ? (
          <span className={styles.readyText} role="status">
            준비 완료
          </span>
        ) : null}
      </div>
      <div className={styles.progressTrack}>
        <div
          aria-label="작업 준비 진행률"
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={percent}
          className={styles.progressFill}
          data-ready={isReady}
          role="progressbar"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className={styles.readyRow}>
        <span className={styles.readyPct}>{percent}%</span>
        <span className={styles.meta}>필수 입력 {satisfiedCount}/{total}</span>
      </div>
      <ul className={styles.chips}>
        {slots.map((slot) => (
          <li
            aria-label={`${slot.label}: ${slot.satisfied ? '완료' : '미완료'}`}
            className={styles.chip}
            data-satisfied={slot.satisfied}
            key={slot.role}
          >
            <i aria-hidden="true" className={styles.chipDot} />
            <span className={styles.chipLabel}>{slot.label}</span>
          </li>
        ))}
      </ul>
      {isParsing || (isReady && !commonResourcesReady && !fullyReady) ? (
        <div aria-atomic="true" aria-live="polite" className={styles.statusArea}>
          {isParsing ? (
            <span className={styles.parsingText} role="status">
              스크립트를 확인하고 있습니다…
            </span>
          ) : (
            <span className={styles.nextAction} role="status">
              공통 리소스를 설정하세요.{' '}
              {onOpenSettings ? (
                <button className={styles.openSettingsButton} onClick={onOpenSettings} type="button">
                  설정 열기
                </button>
              ) : null}
            </span>
          )}
        </div>
      ) : null}
    </div>
  )
}
