import { useEffect, useRef, useState } from 'react'

import { API_BASE, apiFetch } from '@/lib/utils'
import { getTaskStatusText, isTerminalTaskStatus } from '@/lib/tasks'
import { useI18n } from '@/lib/i18n-context'

export function TaskLogPanel({
  taskId,
  onDone,
}: {
  taskId: string
  onDone: (status: string) => void
}) {
  const { t, language } = useI18n()
  const [lines, setLines] = useState<string[]>([])
  const [task, setTask] = useState<any | null>(null)
  const [doneStatus, setDoneStatus] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const seenEventIdsRef = useRef<Set<number>>(new Set())
  const cursorRef = useRef(0)
  const doneRef = useRef(false)
  const onDoneRef = useRef(onDone)
  const sseHealthyRef = useRef(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    onDoneRef.current = onDone
  }, [onDone])

  useEffect(() => {
    if (!taskId) return
    seenEventIdsRef.current = new Set()
    cursorRef.current = 0
    doneRef.current = false
    sseHealthyRef.current = false
    setLines([])
    setTask(null)
    setDoneStatus(null)

    const pushEvent = (payload: any) => {
      const eventId = Number(payload?.id || 0)
      if (eventId && seenEventIdsRef.current.has(eventId)) return
      if (eventId) {
        seenEventIdsRef.current.add(eventId)
        cursorRef.current = Math.max(cursorRef.current, eventId)
      }
      if (payload?.line) {
        setLines(prev => [...prev, payload.line])
      }
      if (payload?.done && !doneRef.current) {
        doneRef.current = true
        sseHealthyRef.current = false
        eventSourceRef.current?.close()
        eventSourceRef.current = null
        const nextStatus = payload.status || 'succeeded'
        setDoneStatus(nextStatus)
        onDoneRef.current(nextStatus)
      }
    }

    const syncTask = async () => {
      const latest = await apiFetch(`/tasks/${taskId}`)
      setTask(latest)
      if (isTerminalTaskStatus(latest.status) && !doneRef.current) {
        pushEvent({ done: true, status: latest.status })
      }
    }

    const es = new EventSource(`${API_BASE}/tasks/${taskId}/logs/stream`)
    eventSourceRef.current = es
    es.onopen = () => {
      sseHealthyRef.current = true
    }
    es.onmessage = (e) => {
      sseHealthyRef.current = true
      pushEvent(JSON.parse(e.data))
    }
    es.onerror = () => {
      if (doneRef.current) {
        es.close()
        if (eventSourceRef.current === es) {
          eventSourceRef.current = null
        }
        return
      }
      sseHealthyRef.current = false
    }

    syncTask().catch(() => {})

    const poll = window.setInterval(async () => {
      if (doneRef.current || sseHealthyRef.current) return
      try {
        const data = await apiFetch(`/tasks/${taskId}/events?since=${cursorRef.current}`)
        for (const item of data.items || []) {
          pushEvent(item)
        }
        await syncTask()
      } catch {
        // passive
      }
    }, 1000)

    return () => {
      sseHealthyRef.current = false
      eventSourceRef.current?.close()
      eventSourceRef.current = null
      window.clearInterval(poll)
    }
  }, [taskId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  const currentStatus = doneStatus || task?.status || 'running'
  const progress = task?.progress_detail || {}
  const progressTotal = Number(progress.total || 0)
  const progressCurrent = Number(progress.current || 0)
  const progressPercent = progressTotal > 0 ? Math.min(100, Math.round((progressCurrent / progressTotal) * 100)) : 0
  const errorText = task?.error || (Array.isArray(task?.errors) ? task.errors[0] : '')
  const statusTone =
    currentStatus === 'succeeded' ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200' :
    currentStatus === 'failed' ? 'border-red-400/40 bg-red-400/10 text-red-200' :
    currentStatus === 'cancelled' || currentStatus === 'interrupted' ? 'border-amber-400/40 bg-amber-400/10 text-amber-200' :
    'border-sky-400/40 bg-sky-400/10 text-sky-200'

  const copyLogs = () => {
    navigator.clipboard?.writeText(lines.join('\n')).catch(() => {})
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className={`rounded-2xl border px-4 py-3 ${statusTone}`}>
          <div className="text-[11px] uppercase tracking-[0.18em] opacity-70">{t('taskLog.status')}</div>
          <div className="mt-1 text-sm font-semibold">{getTaskStatusText(currentStatus, language)}</div>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-hover)] px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">{t('taskLog.progress')}</div>
          <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{progress.label || task?.progress || '0/0'}</div>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-hover)] px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">{t('taskLog.events')}</div>
          <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{t('taskLog.logCount', { count: lines.length })}</div>
        </div>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-hover)] ring-1 ring-[var(--border)]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            currentStatus === 'failed' ? 'bg-red-400' :
            currentStatus === 'succeeded' ? 'bg-emerald-400' :
            'bg-sky-400'
          }`}
          style={{ width: `${progressTotal > 0 ? progressPercent : (isTerminalTaskStatus(currentStatus) ? 100 : 18)}%` }}
        />
      </div>

      {errorText ? (
        <div className="rounded-2xl border border-red-400/35 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          <div className="mb-1 font-semibold">{t('taskLog.failureReason')}</div>
          <div className="break-words text-red-100/85">{errorText}</div>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">{t('taskLog.liveLog')}</div>
          <div className="mt-1 text-sm font-medium text-[var(--text-primary)]">{t('taskLog.liveTitle')}</div>
        </div>
        <button
          type="button"
          onClick={copyLogs}
          className="rounded-full border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          {t('taskLog.copyLogs')}
        </button>
      </div>

      <div className="min-h-[260px] flex-1 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg-input)] p-4 font-mono text-xs ">
        {lines.length === 0 && (
          <div className="flex h-full min-h-[180px] items-center justify-center rounded-2xl border border-dashed border-[var(--border)] text-[var(--text-muted)]">
            {t('taskLog.waiting')}
          </div>
        )}
        <div className="space-y-1.5">
          {lines.map((line, index) => (
            <div
              key={index}
              className={`rounded-xl border border-white/5 bg-white/[0.025] px-3 py-2 leading-5 ${
                line.includes('✓') || line.includes('成功') ? 'text-emerald-400' :
                line.includes('✗') || line.includes('失败') || line.includes('错误') ? 'text-red-400' :
                'text-[var(--text-secondary)]'
              }`}
            >
              {line}
            </div>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
