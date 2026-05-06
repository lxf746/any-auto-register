import { useEffect, useState } from 'react'
import { getPlatforms } from '@/lib/app-data'
import { apiFetch } from '@/lib/utils'
import { formatDateTime } from '@/lib/i18n'
import { useI18n } from '@/lib/i18n-context'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getTaskStatusText, TASK_STATUS_VARIANTS } from '@/lib/tasks'
import { RefreshCw, Activity, CheckCircle2, AlertTriangle, Clock3, ChevronDown } from 'lucide-react'

function shortId(id: string) {
  if (!id) return '-'
  return id.length > 12 ? '...' + id.slice(-8) : id
}

function formatError(error: string | null | undefined): string {
  if (!error) return ''
  // Try to extract a readable message from JSON-like strings
  try {
    if (error.startsWith('{') || error.startsWith('[')) {
      const parsed = JSON.parse(error)
      if (parsed.message) return parsed.message
      if (parsed.error) return parsed.error
      if (Array.isArray(parsed.errors) && parsed.errors.length > 0) {
        const first = parsed.errors[0]
        return first.message || first.kind || JSON.stringify(first).slice(0, 80)
      }
    }
  } catch {
    // not JSON
  }
  // Truncate long strings
  return error.length > 100 ? error.slice(0, 100) + '...' : error
}

export default function TaskHistory() {
  const { t, language } = useI18n()
  const [tasks, setTasks] = useState<any[]>([])
  const [platform, setPlatform] = useState('')
  const [status, setStatus] = useState('')
  const [platforms, setPlatforms] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: '1', page_size: '50' })
      if (platform) params.set('platform', platform)
      if (status) params.set('status', status)
      const data = await apiFetch(`/tasks?${params}`)
      setTasks(data.items || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    getPlatforms()
      .then((data) => setPlatforms(data || []))
      .catch(() => setPlatforms([]))
  }, [])

  useEffect(() => {
    load()
  }, [platform, status])

  const succeeded = tasks.filter((t) => t.status === 'succeeded').length
  const failed = tasks.filter((t) => t.status === 'failed').length
  const running = tasks.filter((t) =>
    ['running', 'claimed', 'pending', 'cancel_requested'].includes(t.status)
  ).length

  const metricCards = [
    { label: t('taskHistory.metric.total'), value: tasks.length, icon: Activity, tone: 'text-[var(--accent)]' },
    { label: t('common.success'), value: succeeded, icon: CheckCircle2, tone: 'text-emerald-500' },
    { label: t('common.failure'), value: failed, icon: AlertTriangle, tone: 'text-red-500' },
    { label: t('taskHistory.metric.running'), value: running, icon: Clock3, tone: 'text-amber-500' },
  ]

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">{t('taskHistory.title')}</h1>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      </div>

      {/* Metrics */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        {metricCards.map(({ label, value, icon: Icon, tone }) => (
          <div
            key={label}
            className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3"
          >
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--chip-bg)] ${tone}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider">{label}</div>
              <div className="text-lg font-semibold text-[var(--text-primary)]">{value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters — inline with table header */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-2.5">
          <span className="text-sm font-medium text-[var(--text-primary)]">{t('taskHistory.recent')}</span>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <div className="relative">
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="h-8 appearance-none rounded-md border border-[var(--border)] bg-[var(--bg-input)] pl-3 pr-7 text-xs text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] focus:border-[var(--accent)]"
              >
                <option value="">{t('taskHistory.allPlatforms')}</option>
                {platforms.map((item: any) => (
                  <option key={item.name} value={item.name}>{item.display_name}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-[var(--text-muted)]" />
            </div>
            <div className="relative">
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="h-8 appearance-none rounded-md border border-[var(--border)] bg-[var(--bg-input)] pl-3 pr-7 text-xs text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] focus:border-[var(--accent)]"
              >
                <option value="">{t('taskHistory.allStatuses')}</option>
                <option value="running">{t('taskHistory.running')}</option>
                <option value="succeeded">{t('common.success')}</option>
                <option value="failed">{t('common.failure')}</option>
                <option value="cancelled">{getTaskStatusText('cancelled', language)}</option>
                <option value="interrupted">{getTaskStatusText('interrupted', language)}</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-[var(--text-muted)]" />
            </div>
            {(platform || status) && (
              <button
                onClick={() => { setPlatform(''); setStatus('') }}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--accent)]"
              >
                {t('common.clear')}
              </button>
            )}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-pane)]">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('common.date')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('taskHistory.taskId')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('common.platform')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('common.status')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('common.progress')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('taskHistory.successFailure')}</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">{t('common.error')}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-[var(--text-muted)]">
                    {t('taskHistory.empty')}
                  </td>
                </tr>
              )}
              {tasks.map((task) => {
                const success = task.success || 0
                const errorCount = task.error_count || 0
                const total = success + errorCount
                const errorText = formatError(task.error)
                return (
                  <tr
                    key={task.id}
                    className="border-b border-[var(--border)]/50 transition-colors hover:bg-[var(--bg-hover)]"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-[var(--text-muted)]">
                      {task.created_at
                        ? formatDateTime(task.created_at, language, {
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false,
                          })
                        : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="cursor-default font-mono text-xs text-[var(--text-muted)]"
                        title={task.id}
                      >
                        {shortId(task.id)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="secondary">{task.platform || '-'}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={TASK_STATUS_VARIANTS[task.status] || 'secondary'}>
                        {getTaskStatusText(task.status, language)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">
                      {task.progress || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {total > 0 ? (
                          <>
                            <div className="flex h-1.5 w-16 overflow-hidden rounded-full bg-[var(--chip-bg)]">
                              {success > 0 && (
                                <div
                                  className="h-full bg-emerald-500 rounded-full"
                                  style={{ width: `${(success / total) * 100}%` }}
                                />
                              )}
                              {errorCount > 0 && (
                                <div
                                  className="h-full bg-red-500 rounded-full"
                                  style={{ width: `${(errorCount / total) * 100}%` }}
                                />
                              )}
                            </div>
                            <span className="text-xs text-[var(--text-muted)] whitespace-nowrap">
                              <span className="text-emerald-500">{success}</span>
                              {' / '}
                              <span className="text-red-500">{errorCount}</span>
                            </span>
                          </>
                        ) : (
                          <span className="text-xs text-[var(--text-muted)]">-</span>
                        )}
                      </div>
                    </td>
                    <td className="max-w-[280px] px-4 py-3">
                      {errorText ? (
                        <span
                          className="block truncate text-xs text-red-500 cursor-default"
                          title={task.error || ''}
                        >
                          {errorText}
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)]">-</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
