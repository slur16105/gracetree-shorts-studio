import type { ScriptValidationDto } from '@gracetree/contracts/desktop-api'

import styles from './JobSummary.module.css'

interface JobSummaryProps {
  scriptValidation: ScriptValidationDto | null
  isParsing: boolean
}

export function JobSummary({ scriptValidation, isParsing }: JobSummaryProps): React.JSX.Element | null {
  if (isParsing) {
    return (
      <div className={styles.container}>
        <p className={styles.parsingText} role="status">
          스크립트를 확인하고 있습니다…
        </p>
      </div>
    )
  }

  if (scriptValidation === null) {
    return null
  }

  if (scriptValidation.status === 'valid' && scriptValidation.oneLiner != null) {
    return (
      <div className={styles.container}>
        <h4 className={styles.oneLiner} title={scriptValidation.oneLiner}>
          {scriptValidation.oneLiner}
        </h4>
      </div>
    )
  }

  if (scriptValidation.status === 'invalid' && scriptValidation.errors.length > 0) {
    return (
      <div className={styles.container}>
        <ul className={styles.errorList} role="list">
          {scriptValidation.errors.map((error, index) => (
            <li className={styles.errorItem} key={`${error.code}-${index}`}>
              {error.message}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return null
}
