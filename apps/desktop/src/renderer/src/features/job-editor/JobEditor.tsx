import type { JobDto, JobInputDto, ResourceDto } from '@gracetree/contracts'
import type { ScriptValidationDto } from '@gracetree/contracts/desktop-api'
import { useCallback, useEffect, useRef, useState } from 'react'

import { DatePicker } from './DatePicker'
import { InputDropZone } from './InputDropZone'
import { JobSummary } from './JobSummary'
import { ReadinessProgress } from './ReadinessProgress'
import { computeReadiness } from './readiness'
import {
  setCurrentJobId,
  useIsRunning,
} from '../job-progress/job-progress-store'

interface JobEditorProps {
  managedRoot: string
  onManagedRootResolved?: (managedRoot: string) => void
  onOpenSettings?: () => void
}

export function JobEditor({ managedRoot, onManagedRootResolved, onOpenSettings }: JobEditorProps): React.JSX.Element {
  const [job, setJob] = useState<JobDto | null>(null)
  const [inputs, setInputs] = useState<JobInputDto[]>([])
  const [scriptValidation, setScriptValidation] = useState<ScriptValidationDto | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [resources, setResources] = useState<ResourceDto[]>([])
  const [isStarting, setIsStarting] = useState(false)
  const validationRef = useRef<{ jobId: string; inputId: string; inputVersion: string } | null>(null)
  const onManagedRootResolvedRef = useRef(onManagedRootResolved)
  const isRunning = useIsRunning()

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

  const handleStartGeneration = useCallback(async () => {
    if (!job || !managedRoot || isRunning || isStarting) return
    setIsStarting(true)
    try {
      await window.desktopApi.startJob(job.id, managedRoot, job.workPath)
    } finally {
      setIsStarting(false)
    }
  }, [job, managedRoot, isRunning, isStarting])

  const canGenerate = Boolean(job && managedRoot && readiness.isReady && !isRunning && !isStarting)

  return (
    <>
      <DatePicker onJobLoaded={handleJobLoaded} />
      <InputDropZone
        initialInputs={job?.inputMetadata}
        jobId={job?.id ?? null}
        onInputsChanged={handleInputsChanged}
      />
      {job ? (
        <>
          <ReadinessProgress isParsing={isParsing} onOpenSettings={onOpenSettings} readiness={readiness} />
          <JobSummary isParsing={isParsing} scriptValidation={scriptValidation} />
          <button
            aria-busy={isStarting || isRunning}
            disabled={!canGenerate}
            onClick={handleStartGeneration}
            type="button"
          >
            {isRunning ? '생성 중...' : isStarting ? '시작 중...' : '생성 시작'}
          </button>
        </>
      ) : null}
    </>
  )
}
