import type { CompletedJobSummary } from '@gracetree/contracts/desktop-api'
import { useCallback, useEffect, useRef, useState } from 'react'

import { showToast } from '../../components/toast-store'
import { formatDate } from '../../utils/format-date'
import styles from './CompletionList.module.css'

interface CompletionListProps {
  managedRoot: string
  refreshKey?: number
  onJobsLoaded?: (jobs: CompletedJobSummary[]) => void
}

type LoadState = 'idle' | 'loading' | 'loaded' | 'error'

export function CompletionList({
  managedRoot,
  refreshKey,
  onJobsLoaded
}: CompletionListProps): React.JSX.Element {
  const [jobs, setJobs] = useState<CompletedJobSummary[]>([])
  const [loadState, setLoadState] = useState<LoadState>('idle')

  const managedRootRef = useRef(managedRoot)
  managedRootRef.current = managedRoot
  const onJobsLoadedRef = useRef(onJobsLoaded)
  onJobsLoadedRef.current = onJobsLoaded

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
      onJobsLoadedRef.current?.(sorted)
    } catch {
      setLoadState('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load, managedRoot, refreshKey])

  function handleOpenClick(event: React.MouseEvent, job: CompletedJobSummary): void {
    event.stopPropagation()
    window.desktopApi.openResultFolder(job.id).catch((err: unknown) => {
      const message = err instanceof Error ? err.message : '폴더를 열 수 없습니다.'
      showToast(message, 'danger')
    })
  }

  const isLoading = loadState === 'loading'

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.heading} id="completed-title">
          완료 목록
        </h2>
        <button
          aria-label="새로고침"
          className={styles.refreshButton}
          disabled={isLoading}
          onClick={() => void load()}
          title="새로고침"
          type="button"
        >
          <svg
            aria-hidden="true"
            fill="none"
            height="16"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            width="16"
          >
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <path d="M21 3v6h-6" />
          </svg>
        </button>
      </div>

      {loadState === 'error' ? (
        <div className={styles.errorState}>
          <p>완료 목록을 불러오지 못했습니다. 새로고침을 눌러 다시 시도하세요.</p>
        </div>
      ) : loadState !== 'loading' && jobs.length === 0 ? (
        <div className={styles.emptyState}>
          <p>아직 완료된 작업이 없습니다. 날짜를 선택해 새 작업을 등록하고 첫 영상을 제작해보세요.</p>
        </div>
      ) : (
        <ul aria-label="완료된 작업 목록" className={styles.list}>
          {jobs.map((job) => {
            const publishDateLabel = formatDate(job.publishDate)
            const label = job.title
              ? `${job.title} — ${publishDateLabel}`
              : publishDateLabel

            return (
              <li aria-label={label} className={styles.row} key={job.id}>
                <div className={styles.rowContent}>
                  <div className={styles.rowTop}>
                    <span className={styles.publishDate}>{publishDateLabel}</span>
                    {job.title ? (
                      <span className={styles.title} title={job.title}>
                        {job.title}
                      </span>
                    ) : null}
                  </div>
                  <div className={styles.rowMeta}>
                    <span>생성 {formatDate(job.completedAt)}</span>
                    {!job.resultExists ? (
                      <span className={styles.missing}>결과 폴더 없음</span>
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
