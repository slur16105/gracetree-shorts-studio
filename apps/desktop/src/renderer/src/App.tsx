import { useCallback, useEffect, useRef, useState } from 'react'

import { SettingsDialog } from './components/SettingsDialog'
import { SidebarIcon } from './components/SidebarIcon'
import { GuideView } from './features/guide/GuideView'
import { CompletionList } from './features/job-history/CompletionList'
import { JobEditor } from './features/job-editor/JobEditor'
import { FailedResultDialog } from './features/job-progress/FailedResultDialog'
import { ResultDialog } from './features/job-progress/ResultDialog'
import { errorMessage } from './features/job-progress/error-labels'
import { INITIAL_JOB_RUN_STATE } from '@gracetree/contracts/job-state'
import type { CompletedJobSummary } from '@gracetree/contracts/desktop-api'
import {
  dispatchJobEvent,
  useJobRunState,
} from './features/job-progress/job-progress-store'
import styles from './styles/App.module.css'

type View = 'home' | 'guide'

function getStatusLabel(state: ReturnType<typeof useJobRunState>): string {
  if (state.status === 'running') {
    const percent = state.percent
    const stage = state.stageName ?? '처리 중'
    return `${stage} ${percent}%`
  }
  if (state.status === 'cancelling') return '취소 중...'
  if (state.status === 'completed') return '생성 완료'
  if (state.status === 'failed') return `오류: ${errorMessage(state.errorCode)}`
  if (state.status === 'cancelled') return '취소됨'
  return '대기 중'
}

function App(): React.JSX.Element {
  const [view, setView] = useState<View>('home')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [failedDialogOpen, setFailedDialogOpen] = useState(false)
  const [managedRoot, setManagedRoot] = useState('')
  const [completionRefreshKey, setCompletionRefreshKey] = useState(0)
  const [resultDialogJob, setResultDialogJob] = useState<CompletedJobSummary | null>(null)
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const settingsWasOpen = useRef(false)
  const resultDialogPrevFocusRef = useRef<Element | null>(null)
  const loadedForJobIdRef = useRef<string | null>(null)
  // pendingResultJobIdRef: set when we need onJobsLoaded to find this job for the dialog
  const pendingResultJobIdRef = useRef<string | null>(null)
  // mirrors resultDialogJob state so the completion effect can read it without a stale closure
  const resultDialogJobRef = useRef<CompletedJobSummary | null>(null)
  const jobState = useJobRunState() ?? INITIAL_JOB_RUN_STATE

  // keep ref in sync with state on every render (before effects run)
  resultDialogJobRef.current = resultDialogJob

  // live region: 1초 스로틀 — cleanup 없이 타이머가 자연히 실행되어야 한다
  const [liveAnnouncement, setLiveAnnouncement] = useState('')
  const throttleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastAnnouncedRef = useRef(0)
  const pendingTextRef = useRef('')

  useEffect(() => {
    const text = getStatusLabel(jobState)
    pendingTextRef.current = text
    const now = Date.now()
    const elapsed = now - lastAnnouncedRef.current
    if (elapsed >= 1000) {
      if (throttleTimerRef.current !== null) {
        clearTimeout(throttleTimerRef.current)
        throttleTimerRef.current = null
      }
      lastAnnouncedRef.current = now
      setLiveAnnouncement(text)
    } else if (throttleTimerRef.current === null) {
      throttleTimerRef.current = setTimeout(() => {
        throttleTimerRef.current = null
        lastAnnouncedRef.current = Date.now()
        setLiveAnnouncement(pendingTextRef.current)
      }, 1000 - elapsed)
    }
  }, [jobState])

  // 엔진 이벤트 구독 (전역)
  useEffect(() => {
    return window.desktopApi.onJobEvent(dispatchJobEvent)
  }, [])

  // 작업 완료 시 완료 목록 갱신 및 결과 다이얼로그 표시.
  // 다이얼로그 데이터는 CompletionList의 onJobsLoaded 콜백으로만 설정한다
  // (App 자체 listCompletedJobs 호출 제거 → IPC 중복 방지, 비동기 경쟁 조건 제거).
  useEffect(() => {
    if (jobState.status === 'completed') {
      // managedRoot가 아직 확인되지 않았으면 loadedForJobIdRef를 잠그지 않는다:
      // managedRoot가 확정되면 이 effect가 재실행된다.
      if (loadedForJobIdRef.current !== jobState.jobId && managedRoot) {
        loadedForJobIdRef.current = jobState.jobId
        pendingResultJobIdRef.current = jobState.jobId
        setCompletionRefreshKey((k) => k + 1)
      }
      setFailedDialogOpen(false)
    } else if (jobState.status === 'failed') {
      setFailedDialogOpen(true)
      loadedForJobIdRef.current = null
      pendingResultJobIdRef.current = null
      if (resultDialogJobRef.current !== null) {
        const prev = resultDialogPrevFocusRef.current
        if (prev instanceof HTMLElement) prev.focus()
        setResultDialogJob(null)
      }
    } else {
      setFailedDialogOpen(false)
      loadedForJobIdRef.current = null
      pendingResultJobIdRef.current = null
      // 다이얼로그가 열려 있는 상태에서 job이 비완료 상태로 전환되면 포커스를 복원 후 닫는다
      if (resultDialogJobRef.current !== null) {
        const prev = resultDialogPrevFocusRef.current
        if (prev instanceof HTMLElement) prev.focus()
        setResultDialogJob(null)
      }
    }
  }, [jobState, managedRoot])

  useEffect(() => {
    if (settingsWasOpen.current && !settingsOpen) {
      settingsButtonRef.current?.focus()
    }
    settingsWasOpen.current = settingsOpen
  }, [settingsOpen])

  const handleManagedRootResolved = useCallback((resolved: string) => {
    setManagedRoot((current) => (current === resolved ? current : resolved))
  }, [])

  // CompletionList 로드 완료 콜백: pendingResultJobId에 해당하는 작업이 있으면 다이얼로그 표시
  const handleJobsLoaded = useCallback((jobs: CompletedJobSummary[]) => {
    const pendingId = pendingResultJobIdRef.current
    if (!pendingId) return
    const job = jobs.find((j) => j.id === pendingId)
    if (job) {
      pendingResultJobIdRef.current = null
      // 다이얼로그가 실제로 마운트되는 시점에 포커스를 캡처한다 (비동기 응답 후)
      resultDialogPrevFocusRef.current = document.activeElement
      setResultDialogJob(job)
    }
  }, [])

  const handleResultDialogClose = useCallback(() => {
    setResultDialogJob(null)
    const prev = resultDialogPrevFocusRef.current
    if (prev instanceof HTMLElement) {
      prev.focus()
    }
  }, [])

  return (
    <div className={styles.shell}>
      <nav aria-label="전역 탐색" className={styles.sidebar}>
        <div aria-hidden="true" className={styles.brandMark}>
          G
        </div>
        <div className={styles.primaryNavigation}>
          <button
            aria-current={view === 'home' ? 'page' : undefined}
            aria-label="홈"
            className={styles.navigationButton}
            onClick={() => setView('home')}
            type="button"
          >
            <SidebarIcon name="home" />
          </button>
          <button
            aria-current={view === 'guide' ? 'page' : undefined}
            aria-label="사용 가이드"
            className={styles.navigationButton}
            onClick={() => setView('guide')}
            type="button"
          >
            <SidebarIcon name="guide" />
          </button>
        </div>
        <button
          aria-expanded={settingsOpen}
          aria-haspopup="dialog"
          aria-label="공통 리소스 설정"
          className={styles.navigationButton}
          onClick={() => setSettingsOpen(true)}
          ref={settingsButtonRef}
          type="button"
        >
          <SidebarIcon name="settings" />
        </button>
      </nav>

      <main className={styles.main}>
        {view === 'home' ? (
          <section aria-labelledby="home-title" className={styles.view}>
            <p className={styles.eyebrow}>GraceTree Shorts Studio</p>
            <h1 id="home-title">영상 작업</h1>
            <div className={styles.homeLayout}>
              <section aria-labelledby="workspace-title" className={styles.workspaceRegion}>
                <h2 id="workspace-title">새 영상 준비</h2>
                <JobEditor
                  managedRoot={managedRoot}
                  onManagedRootResolved={handleManagedRootResolved}
                  onOpenSettings={() => setSettingsOpen(true)}
                />
              </section>
              <aside aria-labelledby="completed-title" className={styles.completedRegion}>
                <h2 id="completed-title">완료 목록</h2>
                {managedRoot ? (
                  <CompletionList
                    managedRoot={managedRoot}
                    onJobsLoaded={handleJobsLoaded}
                    refreshKey={completionRefreshKey}
                  />
                ) : (
                  <div className={styles.compactEmptyState}>
                    <p>완료된 영상이 없습니다.</p>
                  </div>
                )}
              </aside>
            </div>
          </section>
        ) : (
          <section aria-labelledby="guide-title" className={styles.view}>
            <p className={styles.eyebrow}>도움말</p>
            <h1 id="guide-title">사용 가이드</h1>
            <GuideView />
          </section>
        )}
      </main>

      <footer className={styles.statusBar}>
        <span
          className={styles.statusIndicator}
          data-running={jobState.status === 'running' || jobState.status === 'cancelling' ? '' : undefined}
        />
        <span>{getStatusLabel(jobState)}</span>
        {jobState.status === 'running' ? (
          <span className={styles.statusDetail}>
            {jobState.stageId ? `단계: ${jobState.stageName ?? jobState.stageId}` : '준비 중'}
          </span>
        ) : (
          <span className={styles.statusDetail}>모든 기능은 로컬에서 실행됩니다</span>
        )}
      </footer>

      <div aria-atomic="true" aria-live="polite" className={styles.srOnly}>
        {liveAnnouncement}
      </div>

      {settingsOpen ? (
        <SettingsDialog managedRoot={managedRoot} onClose={() => setSettingsOpen(false)} />
      ) : null}

      {resultDialogJob ? (
        <ResultDialog
          completedAt={resultDialogJob.completedAt}
          onClose={handleResultDialogClose}
          publishDate={resultDialogJob.publishDate}
          resultPath={resultDialogJob.resultPath}
          title={resultDialogJob.title}
        />
      ) : null}

      {failedDialogOpen && jobState.status === 'failed' ? (
        <FailedResultDialog
          attemptId={jobState.attemptId}
          details={jobState.details}
          errorCode={jobState.errorCode}
          jobId={jobState.jobId}
          message={errorMessage(jobState.errorCode)}
          onClose={() => setFailedDialogOpen(false)}
          onOpenSettings={() => setSettingsOpen(true)}
          recoverable={jobState.recoverable}
          stageId={jobState.stageId}
        />
      ) : null}
    </div>
  )
}

export default App
