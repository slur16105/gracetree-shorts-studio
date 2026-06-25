import { useCallback, useEffect, useRef, useState } from 'react'

import { SettingsDialog } from './components/SettingsDialog'
import { SidebarIcon } from './components/SidebarIcon'
import { GuideView } from './features/guide/GuideView'
import { CompletionList } from './features/job-history/CompletionList'
import { JobEditor } from './features/job-editor/JobEditor'
import { INITIAL_JOB_RUN_STATE } from '@gracetree/contracts/job-state'
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
  if (state.status === 'completed') return '생성 완료'
  if (state.status === 'failed') return `오류: ${state.errorCode}`
  if (state.status === 'cancelled') return '취소됨'
  return '대기 중'
}

function App(): React.JSX.Element {
  const [view, setView] = useState<View>('home')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [managedRoot, setManagedRoot] = useState('')
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const settingsWasOpen = useRef(false)
  const jobState = useJobRunState() ?? INITIAL_JOB_RUN_STATE

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

  useEffect(() => {
    if (settingsWasOpen.current && !settingsOpen) {
      settingsButtonRef.current?.focus()
    }
    settingsWasOpen.current = settingsOpen
  }, [settingsOpen])

  const handleManagedRootResolved = useCallback((resolved: string) => {
    setManagedRoot((current) => (current === resolved ? current : resolved))
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
                  <CompletionList managedRoot={managedRoot} />
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
          data-running={jobState.status === 'running' ? '' : undefined}
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
    </div>
  )
}

export default App
