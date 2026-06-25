import { useCallback, useEffect, useRef, useState } from 'react'

import { SettingsDialog } from './components/SettingsDialog'
import { SidebarIcon } from './components/SidebarIcon'
import { GuideView } from './features/guide/GuideView'
import { CompletionList } from './features/job-history/CompletionList'
import { JobEditor } from './features/job-editor/JobEditor'
import styles from './styles/App.module.css'

type View = 'home' | 'guide'

function App(): React.JSX.Element {
  const [view, setView] = useState<View>('home')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [managedRoot, setManagedRoot] = useState('')
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const settingsWasOpen = useRef(false)

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
        <span className={styles.statusIndicator} />
        <span>대기 중</span>
        <span className={styles.statusDetail}>모든 기능은 로컬에서 실행됩니다</span>
      </footer>

      {settingsOpen ? (
        <SettingsDialog managedRoot={managedRoot} onClose={() => setSettingsOpen(false)} />
      ) : null}
    </div>
  )
}

export default App
