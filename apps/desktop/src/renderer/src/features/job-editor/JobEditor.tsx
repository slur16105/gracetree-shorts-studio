import type { JobDto } from '@gracetree/contracts'
import { useCallback, useState } from 'react'

import { DatePicker } from './DatePicker'
import { InputDropZone } from './InputDropZone'

export function JobEditor(): React.JSX.Element {
  const [job, setJob] = useState<JobDto | null>(null)
  const handleJobLoaded = useCallback((loadedJob: JobDto | null) => {
    setJob(loadedJob)
  }, [])

  return (
    <>
      <DatePicker onJobLoaded={handleJobLoaded} />
      <InputDropZone jobId={job?.id ?? null} />
    </>
  )
}
