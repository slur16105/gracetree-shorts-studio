import type { JobDto } from '@gracetree/contracts'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import styles from './DatePicker.module.css'

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function weeks(dates: string[]): string[][] {
  return Array.from({ length: 6 }, (_, index) => dates.slice(index * 7, index * 7 + 7))
}

function toDateKey(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function fromDateKey(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function addDays(value: string, amount: number): string {
  const date = fromDateKey(value)
  date.setDate(date.getDate() + amount)
  return toDateKey(date)
}

function addMonths(value: string, amount: number): string {
  const date = fromDateKey(value)
  const day = date.getDate()
  const target = new Date(date.getFullYear(), date.getMonth() + amount, 1)
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()
  target.setDate(Math.min(day, lastDay))
  return toDateKey(target)
}

function formatDate(value: string): string {
  const date = fromDateKey(value)
  return `${value} · ${DAY_LABELS[date.getDay()]}`
}

function calendarDates(focusedDate: string): string[] {
  const focused = fromDateKey(focusedDate)
  const first = new Date(focused.getFullYear(), focused.getMonth(), 1)
  first.setDate(first.getDate() - first.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(first)
    date.setDate(first.getDate() + index)
    return toDateKey(date)
  })
}

export function DatePicker(): React.JSX.Element {
  const [today, setToday] = useState(() => toDateKey(new Date()))
  const [selectedDate, setSelectedDate] = useState(today)
  const [focusedDate, setFocusedDate] = useState(today)
  const [open, setOpen] = useState(false)
  const [job, setJob] = useState<JobDto | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [reloadRequest, setReloadRequest] = useState(0)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const dayRefs = useRef(new Map<string, HTMLButtonElement>())
  const dates = useMemo(() => calendarDates(focusedDate), [focusedDate])
  const focusedMonth = fromDateKey(focusedDate)

  useEffect(() => {
    let active = true
    window.desktopApi
      .getOrCreateJobForDate(selectedDate)
      .then((loadedJob) => {
        if (active) setJob(loadedJob)
      })
      .catch(() => {
        if (active) setLoadError(true)
      })
    return () => {
      active = false
    }
  }, [reloadRequest, selectedDate])

  useEffect(() => {
    const now = new Date()
    const nextMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
    const timeout = window.setTimeout(() => {
      const nextToday = toDateKey(new Date())
      setSelectedDate((current) => (current === today ? nextToday : current))
      setFocusedDate((current) => (current === today ? nextToday : current))
      setToday(nextToday)
    }, nextMidnight.getTime() - now.getTime())

    return () => window.clearTimeout(timeout)
  }, [today])

  useEffect(() => {
    if (open) dayRefs.current.get(focusedDate)?.focus()
  }, [focusedDate, open])

  const close = (): void => {
    setOpen(false)
    queueMicrotask(() => triggerRef.current?.focus())
  }

  const select = (date: string): void => {
    setJob(null)
    setLoadError(false)
    setSelectedDate(date)
    setFocusedDate(date)
    setReloadRequest((current) => current + 1)
    close()
  }

  const handleDialogKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key !== 'Tab') return

    const focusableElements = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]):not([tabindex="-1"]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ) ?? []
    )
    const first = focusableElements.at(0)
    const last = focusableElements.at(-1)
    if (!first || !last) {
      event.preventDefault()
      return
    }

    const activeElement = document.activeElement
    if (
      event.shiftKey &&
      (activeElement === first || !dialogRef.current?.contains(activeElement))
    ) {
      event.preventDefault()
      last.focus()
    } else if (
      !event.shiftKey &&
      (activeElement === last || !dialogRef.current?.contains(activeElement))
    ) {
      event.preventDefault()
      first.focus()
    }
  }

  const handleGridKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    let nextDate: string | null = null
    if (event.key === 'ArrowLeft') nextDate = addDays(focusedDate, -1)
    if (event.key === 'ArrowRight') nextDate = addDays(focusedDate, 1)
    if (event.key === 'ArrowUp') nextDate = addDays(focusedDate, -7)
    if (event.key === 'ArrowDown') nextDate = addDays(focusedDate, 7)
    if (event.key === 'Home') nextDate = addDays(focusedDate, -fromDateKey(focusedDate).getDay())
    if (event.key === 'End') {
      nextDate = addDays(focusedDate, 6 - fromDateKey(focusedDate).getDay())
    }
    if (event.key === 'PageUp') nextDate = addMonths(focusedDate, -1)
    if (event.key === 'PageDown') nextDate = addMonths(focusedDate, 1)
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      select(focusedDate)
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
      return
    }
    if (nextDate) {
      event.preventDefault()
      setFocusedDate(nextDate)
    }
  }

  return (
    <div className={styles.container}>
      <span className={styles.label}>게시 날짜</span>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`게시 날짜 ${formatDate(selectedDate)}`}
        className={styles.trigger}
        onClick={() => {
          if (open) {
            close()
            return
          }
          setFocusedDate(selectedDate)
          setOpen(true)
        }}
        ref={triggerRef}
        type="button"
      >
        {formatDate(selectedDate)}
      </button>
      <span className={styles.jobStatus} role="status">
        {loadError
          ? '작업을 불러오지 못했습니다'
          : job?.pathState === 'missing'
            ? '관리 폴더 확인 필요'
            : job
              ? '날짜별 작업 복원됨'
              : '작업 불러오는 중'}
      </span>

      {open ? (
        <div
          aria-label="게시 날짜 선택"
          aria-modal="true"
          className={styles.popover}
          onKeyDown={handleDialogKeyDown}
          ref={dialogRef}
          role="dialog"
        >
          <p aria-live="polite" className={styles.monthLabel}>
            {focusedMonth.getFullYear()}년 {focusedMonth.getMonth() + 1}월
          </p>
          <div
            aria-label={`${focusedMonth.getFullYear()}년 ${focusedMonth.getMonth() + 1}월`}
            className={styles.grid}
            onKeyDown={handleGridKeyDown}
            role="grid"
          >
            <div className={styles.gridRow} role="row">
              {DAY_LABELS.map((label) => (
                <span className={styles.columnHeader} key={label} role="columnheader">
                  {label}
                </span>
              ))}
            </div>
            {weeks(dates).map((week) => (
              <div className={styles.gridRow} key={week[0]} role="row">
                {week.map((date) => {
                  const parsed = fromDateKey(date)
                  const outsideMonth = parsed.getMonth() !== focusedMonth.getMonth()
                  return (
                    <button
                      aria-current={date === today ? 'date' : undefined}
                      aria-label={date}
                      aria-selected={date === selectedDate}
                      className={styles.day}
                      data-outside-month={outsideMonth || undefined}
                      key={date}
                      onClick={() => select(date)}
                      ref={(element) => {
                        if (element) dayRefs.current.set(date, element)
                        else dayRefs.current.delete(date)
                      }}
                      role="gridcell"
                      tabIndex={date === focusedDate ? 0 : -1}
                      type="button"
                    >
                      {parsed.getDate()}
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
