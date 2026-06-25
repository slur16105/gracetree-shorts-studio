import type { ReadinessResult } from './readiness'
import styles from './ReadinessProgress.module.css'

interface ReadinessProgressProps {
  readiness: ReadinessResult
  isParsing: boolean
}

export function ReadinessProgress({
  readiness,
  isParsing,
}: ReadinessProgressProps): React.JSX.Element {
  const { slots, satisfiedCount, total, percent, isReady, nextAction, commonResourcesReady } = readiness
  const fullyReady = isReady && commonResourcesReady

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.label}>필수 입력 {satisfiedCount}/{total}</span>
        <span className={styles.percent}>{percent}%</span>
      </div>
      <div className={styles.progressTrack}>
        <div
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={percent}
          className={styles.progressFill}
          data-ready={isReady}
          role="progressbar"
          style={{ width: `${percent}%` }}
        />
      </div>
      <ul className={styles.slots}>
        {slots.map((slot) => (
          <li className={styles.slot} data-satisfied={slot.satisfied} key={slot.role}>
            <span
              aria-hidden="true"
              className={styles.slotIcon}
              data-satisfied={slot.satisfied}
            >
              {slot.satisfied ? '✓' : '✗'}
            </span>
            <span className={styles.slotLabel}>{slot.label}</span>
          </li>
        ))}
      </ul>
      <div aria-atomic="true" aria-live="polite" className={styles.statusArea}>
        {fullyReady ? (
          <span className={styles.readyText} role="status">
            준비 완료
          </span>
        ) : isParsing ? (
          <span className={styles.parsingText} role="status">
            스크립트를 확인하고 있습니다…
          </span>
        ) : isReady && !commonResourcesReady ? (
          <span className={styles.nextAction} role="status">
            공통 리소스를 설정하세요.
          </span>
        ) : nextAction != null ? (
          <span className={styles.nextAction}>{nextAction}</span>
        ) : null}
      </div>
    </div>
  )
}
