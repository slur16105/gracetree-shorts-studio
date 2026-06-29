import type { JobDto, JobInputDto, ResourceDto } from '@gracetree/contracts'
import type { ScriptValidationDto } from '@gracetree/contracts/desktop-api'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'

import { DatePicker } from './DatePicker'
import { InputDropZone } from './InputDropZone'
import styles from './JobEditor.module.css'
import { JobSummary } from './JobSummary'
import { ReadinessProgress } from './ReadinessProgress'
import { computeReadiness } from './readiness'
import { CancelConfirmDialog } from '../job-progress/CancelConfirmDialog'
import { RegenerateConfirmDialog } from '../job-progress/RegenerateConfirmDialog'
import {
  revertJobCancellingToRunning,
  setCurrentJobId,
  setJobCancelling,
  useIsRunning,
  useJobRunState,
} from '../job-progress/job-progress-store'

interface JobEditorProps {
  managedRoot: string
  onManagedRootResolved?: (managedRoot: string) => void
  onOpenSettings?: () => void
  onTitleChange?: (title: string | null) => void
  completionList?: ReactNode
}

export function JobEditor({
  managedRoot,
  onManagedRootResolved,
  onOpenSettings,
  onTitleChange,
  completionList,
}: JobEditorProps): React.JSX.Element {
  const [job, setJob] = useState<JobDto | null>(null)
  const [inputs, setInputs] = useState<JobInputDto[]>([])
  const [scriptValidation, setScriptValidation] = useState<ScriptValidationDto | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [resources, setResources] = useState<ResourceDto[]>([])
  const [isStarting, setIsStarting] = useState(false)
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false)
  const [regenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false)
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const regenerateButtonRef = useRef<HTMLButtonElement>(null)
  const validationRef = useRef<{ jobId: string; inputId: string; inputVersion: string } | null>(null)
  const onManagedRootResolvedRef = useRef(onManagedRootResolved)
  const isRunning = useIsRunning()
  const jobRunState = useJobRunState()
  const attemptId =
    jobRunState.status === 'running' || jobRunState.status === 'cancelling'
      ? jobRunState.attemptId
      : null

  useEffect(() => {
    onManagedRootResolvedRef.current = onManagedRootResolved
  })

  const handleJobLoaded = useCallback((loadedJob: JobDto | null) => {
    setJob(loadedJob)
    setInputs(loadedJob?.inputMetadata ?? [])
    setScriptValidation(null)
    setIsParsing(false)
    setIsStarting(false)
    validationRef.current = null
    setCurrentJobId(loadedJob?.id ?? null)

    if (loadedJob) {
      // Derive managedRoot from workPath: /GraceTreeData/jobs/2026-06-20 → /GraceTreeData
      const parts = loadedJob.workPath.replace(/\\/g, '/').split('/')
      const resolved = parts.slice(0, -2).join('/') || '/'
      onManagedRootResolvedRef.current?.(resolved)
    }
  }, [])

  const handleInputsChanged = useCallback((nextInputs: JobInputDto[]) => {
    setInputs(nextInputs)
  }, [])

  // 공통 리소스 로드
  useEffect(() => {
    if (!managedRoot) return
    let active = true
    window.desktopApi
      .getResources(managedRoot)
      .then((loaded) => {
        if (active) setResources(loaded)
      })
      .catch(() => {
        // 로드 실패 시 빈 배열 유지
      })
    return () => {
      active = false
    }
  }, [managedRoot])

  // script role 입력이 ready 상태로 존재하면 자동 검증 요청
  useEffect(() => {
    if (!job) return

    const scriptInput = inputs.find((i) => i.role === 'script' && i.status === 'ready')

    if (!scriptInput) {
      // 스크립트 파일 없음 → 검증 결과 초기화
      setScriptValidation(null)
      setIsParsing(false)
      validationRef.current = null
      return
    }

    const { id: inputId, updatedAt: inputVersion, managedPath } = scriptInput

    // 이미 같은 버전으로 검증 요청 중이거나 완료된 경우 스킵
    if (
      validationRef.current?.jobId === job.id &&
      validationRef.current?.inputId === inputId &&
      validationRef.current?.inputVersion === inputVersion
    ) {
      return
    }

    // 새 검증 요청 시작
    validationRef.current = { jobId: job.id, inputId, inputVersion }
    setIsParsing(true)

    let cancelled = false

    window.desktopApi
      .validateScript(job.id, inputId, inputVersion, managedPath)
      .then((result) => {
        if (cancelled) return
        // stale 검사: ref와 응답의 jobId/inputId/inputVersion이 모두 일치할 때만 반영
        if (
          validationRef.current?.jobId === job.id &&
          validationRef.current?.inputId === result.inputId &&
          validationRef.current?.inputVersion === result.inputVersion
        ) {
          setScriptValidation(result)
          setIsParsing(false)
        }
      })
      .catch(() => {
        if (cancelled) return
        if (
          validationRef.current?.jobId === job.id &&
          validationRef.current?.inputId === inputId &&
          validationRef.current?.inputVersion === inputVersion
        ) {
          setScriptValidation(null)
          setIsParsing(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [job, inputs])

  const readiness = computeReadiness(inputs, scriptValidation, resources)

  // 파싱된 스크립트 제목을 상위(푸터 "현재 작업")로 올린다.
  const onTitleChangeRef = useRef(onTitleChange)
  useEffect(() => {
    onTitleChangeRef.current = onTitleChange
  })
  useEffect(() => {
    const title =
      scriptValidation?.status === 'valid' ? (scriptValidation.oneLiner ?? null) : null
    onTitleChangeRef.current?.(title)
  }, [scriptValidation])

  const handleStartGeneration = useCallback(async () => {
    if (!job || !managedRoot || isRunning || isStarting) return
    setIsStarting(true)
    try {
      await window.desktopApi.startJob(job.id, managedRoot, job.workPath)
    } finally {
      setIsStarting(false)
    }
  }, [job, managedRoot, isRunning, isStarting])

  const handleRegenerateClick = useCallback(() => {
    setRegenerateConfirmOpen(true)
  }, [])

  const handleRegenerateDialogClose = useCallback(() => {
    setRegenerateConfirmOpen(false)
    regenerateButtonRef.current?.focus()
  }, [])

  const handleRegenerateConfirm = useCallback(async () => {
    if (!job || !managedRoot || isRunning || isStarting) return
    setRegenerateConfirmOpen(false)
    setIsStarting(true)
    try {
      await window.desktopApi.startJob(job.id, managedRoot, job.workPath, true)
    } finally {
      setIsStarting(false)
    }
  }, [job, managedRoot, isRunning, isStarting])

  const isJobCompleted = job?.status === 'completed'
  const canGenerate = Boolean(job && managedRoot && readiness.isReady && !isRunning && !isStarting && !isJobCompleted)
  const isCancelling = jobRunState.status === 'cancelling'

  const handleCancelClick = useCallback(() => {
    setCancelConfirmOpen(true)
  }, [])

  const handleCancelDialogClose = useCallback(() => {
    setCancelConfirmOpen(false)
    cancelButtonRef.current?.focus()
  }, [])

  const handleCancelConfirm = useCallback(async () => {
    if (!job || !attemptId || jobRunState.status !== 'running') return
    const prevRunState = jobRunState
    setCancelConfirmOpen(false)
    setJobCancelling()
    try {
      await window.desktopApi.cancelJob(job.id, attemptId)
    } catch (err) {
      // On timeout the cancel signal was delivered; job_cancelled arrives via the stream
      // so we must NOT revert — reverting would cause a running→cancelled flicker.
      // Only revert on genuine failure (engine crashed, IPC layer down, etc.).
      if (err instanceof Error && err.message.includes('timed out')) return
      revertJobCancellingToRunning(prevRunState)
    }
  }, [job, attemptId, jobRunState])

  const generateAction = !job ? (
    <button className={styles.primaryButton} disabled type="button">
      영상 생성
    </button>
  ) : isRunning ? (
    <button
      className={styles.secondaryButton}
      disabled={isCancelling}
      onClick={handleCancelClick}
      ref={cancelButtonRef}
      type="button"
    >
      {isCancelling ? '취소 중...' : '취소'}
    </button>
  ) : isJobCompleted ? (
    <>
      <button
        className={styles.secondaryButton}
        onClick={() => window.desktopApi.openDownloadsFolder().catch(() => {})}
        type="button"
      >
        다운로드 폴더 열기
      </button>
      <button
        aria-busy={isStarting}
        className={styles.primaryButton}
        disabled={isStarting || isRunning}
        onClick={handleRegenerateClick}
        ref={regenerateButtonRef}
        type="button"
      >
        {isStarting ? '시작 중...' : '다시 생성'}
      </button>
    </>
  ) : (
    <button
      aria-busy={isStarting}
      className={styles.primaryButton}
      disabled={!canGenerate}
      onClick={handleStartGeneration}
      type="button"
    >
      {isStarting ? '시작 중...' : '영상 생성'}
    </button>
  )

  return (
    <>
      <div className={styles.homeLayout}>
        <section aria-label="입력" className={styles.workspaceRegion}>
          <div className={styles.topRow}>
            <DatePicker onJobLoaded={handleJobLoaded} />
            <div className={styles.topActions}>{generateAction}</div>
          </div>
          <InputDropZone
            initialInputs={job?.inputMetadata}
            jobId={job?.id ?? null}
            onInputsChanged={handleInputsChanged}
          />
          {job ? <JobSummary isParsing={isParsing} scriptValidation={scriptValidation} /> : null}
        </section>
        <aside aria-label="완료 목록" className={styles.completedRegion}>
          {job ? (
            <section aria-label="입력 준비" className={styles.readinessRegion}>
              <ReadinessProgress
                isParsing={isParsing}
                onOpenSettings={onOpenSettings}
                readiness={readiness}
              />
            </section>
          ) : null}
          {completionList}
        </aside>
      </div>

      {cancelConfirmOpen ? (
        <CancelConfirmDialog onClose={handleCancelDialogClose} onConfirm={handleCancelConfirm} />
      ) : null}

      {regenerateConfirmOpen ? (
        <RegenerateConfirmDialog onClose={handleRegenerateDialogClose} onConfirm={handleRegenerateConfirm} />
      ) : null}
    </>
  )
}
