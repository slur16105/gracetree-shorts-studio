import type { CompletedJobSummary } from '@gracetree/contracts/desktop-api'
import { useCallback, useEffect, useRef, useState } from 'react'

import styles from './CompletionList.module.css'

interface CompletionListProps {
  managedRoot: string
  onJobSelected?: (jobId: string) => void
}

type LoadState = 'idle' | 'loading' | 'loaded' | 'error'

function formatDate(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function CompletionList({
  managedRoot,
  onJobSelected
}: CompletionListProps): React.JSX.Element {
  const [jobs, setJobs] = useState<CompletedJobSummary[]>([])
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const managedRootRef = useRef(managedRoot)
  managedRootRef.current = managedRoot

  const load = useCallback(async () => {
    if (!managedRootRef.current) return
    setLoadState('loading')
    try {
      const result = await window.desktopApi.listCompletedJobs(managedRootRef.current)
      // 게시 날짜 내림차순 정렬
      const sorted = [...result].sort(
        (a, b) => new Date(b.publishDate).getTime() - new Date(a.publishDate).getTime()
      )
      setJobs(sorted)
      setLoadState('loaded')
    } catch {
      setLoadState('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load, managedRoot])

  function handleRowClick(jobId: string): void {
    setSelectedJobId(jobId)
    onJobSelected?.(jobId)
  }

  function handleRowKeyDown(event: React.KeyboardEvent, jobId: string): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleRowClick(jobId)
    }
  }

  function handleOpenClick(event: React.MouseEvent, job: CompletedJobSummary): void {
    event.stopPropagation()
    void window.desktopApi.openResultFolder(job.id, job.resultPath)
  }

  const isLoading = loadState === 'loading'

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <button
          className={styles.refreshButton}
          disabled={isLoading}
          onClick={() => void load()}
          type="button"
        >
          {isLoading ? '로딩 중…' : '새로고침'}
        </button>
      </div>

      {loadState === 'error' ? (
        <div className={styles.errorState}>
          <p>완료 목록을 불러오지 못했습니다. 새로고침을 눌러 다시 시도하세요.</p>
        </div>
      ) : loadState !== 'loading' && jobs.length === 0 ? (
        <div className={styles.emptyState}>
          <p>아직 완료된 작업이 없습니다. 첫 영상을 제작해보세요.</p>
        </div>
      ) : (
        <ul aria-label="완료된 작업 목록" className={styles.list} role="listbox">
          {jobs.map((job) => {
            const isSelected = job.id === selectedJobId
            const publishDateLabel = formatDate(job.publishDate)
            const label = job.title
              ? `${job.title} — ${publishDateLabel}`
              : publishDateLabel

            return (
              <li
                aria-label={label}
                aria-selected={isSelected}
                className={styles.row}
                key={job.id}
                onClick={() => handleRowClick(job.id)}
                onKeyDown={(e) => handleRowKeyDown(e, job.id)}
                role="option"
                tabIndex={0}
              >
                <span aria-hidden="true" className={styles.selectionIcon}>
                  {isSelected ? '✓' : ''}
                </span>

                <div className={styles.rowContent}>
                  <span className={styles.publishDate}>{publishDateLabel}</span>
                  <div className={styles.rowMeta}>
                    {job.title ? (
                      <span className={styles.title} title={job.title}>
                        {job.title}
                      </span>
                    ) : null}
                    <span>생성: {formatDate(job.completedAt)}</span>
                    {!job.resultExists ? (
                      <span>결과 폴더를 찾을 수 없습니다</span>
                    ) : null}
                  </div>
                </div>

                <button
                  className={styles.openButton}
                  disabled={!job.resultExists}
                  onClick={(e) => handleOpenClick(e, job)}
                  title={job.resultExists ? '결과 폴더 열기' : '결과 폴더를 찾을 수 없습니다'}
                  type="button"
                >
                  열기
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
