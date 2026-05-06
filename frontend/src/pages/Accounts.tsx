import { useEffect, useState, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useParams } from 'react-router-dom'
import { getConfig, getConfigOptions, getPlatforms } from '@/lib/app-data'
import type { ConfigOptionsResponse } from '@/lib/config-options'
import { getCaptchaStrategyLabel } from '@/lib/config-options'
import { apiDownload, apiFetch, triggerBrowserDownload } from '@/lib/utils'
import { formatDateTime, translateAccountStatus } from '@/lib/i18n'
import { useI18n } from '@/lib/i18n-context'
import { buildExecutorOptions, buildRegistrationOptions, hasReusableOAuthBrowser, pickOAuthExecutor } from '@/lib/registration'
import { TaskLogPanel } from '@/components/tasks/TaskLogPanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { getTaskStatusText, TASK_STATUS_VARIANTS } from '@/lib/tasks'
import { RefreshCw, Copy, ExternalLink, Download, Upload, Plus, X, Mail, Trash2, Zap } from 'lucide-react'

const STATUS_VARIANT: Record<string, any> = {
  registered: 'default', trial: 'success', subscribed: 'success',
  expired: 'warning', invalid: 'danger',
  free: 'secondary', eligible: 'secondary', valid: 'success', unknown: 'secondary',
}

const platformActionsCache = new Map<string, any[]>()
const platformActionsPromiseCache = new Map<string, Promise<any[]>>()

function getAccountOverview(acc: any) {
  return acc?.overview || {}
}

function getDisplaySummary(acc: any) {
  return acc?.display_summary && typeof acc.display_summary === 'object' ? acc.display_summary : {}
}

function getVerificationMailbox(acc: any) {
  const providerResources = Array.isArray(acc?.provider_resources) ? acc.provider_resources : []
  const normalized = providerResources.find((item: any) => item?.resource_type === 'mailbox')
  if (normalized) {
    return {
      provider: normalized.provider_name,
      email: normalized.handle || normalized.display_name,
      account_id: normalized.resource_identifier,
    }
  }
  return null
}

function getLifecycleStatus(acc: any) {
  return getDisplaySummary(acc)?.status?.lifecycle || acc?.lifecycle_status || 'registered'
}

function getDisplayStatus(acc: any) {
  return getDisplaySummary(acc)?.status?.display || acc?.display_status || acc?.plan_state || getLifecycleStatus(acc)
}

function getPlanState(acc: any) {
  return getDisplaySummary(acc)?.status?.plan_state || acc?.plan_state || acc?.overview?.plan_state || 'unknown'
}

function getValidityStatus(acc: any) {
  return getDisplaySummary(acc)?.status?.validity || acc?.validity_status || acc?.overview?.validity_status || 'unknown'
}

function getCompactStatusMeta(acc: any) {
  const summary = getDisplaySummary(acc)
  const primaryMetrics = Array.isArray(summary?.primary_metrics) ? summary.primary_metrics : []
  if (primaryMetrics.length > 0) {
    return primaryMetrics.slice(0, 2).map((item: any) => {
      const sub = item?.sub ? ` · ${item.sub}` : ''
      return `${item?.label || ''}:${item?.value || '-'}${sub}`
    }).join(' / ')
  }
  const overview = getAccountOverview(acc)
  const parts = [
    `生命周期:${getLifecycleStatus(acc)}`,
    `套餐:${getPlanState(acc)}`,
    `有效:${getValidityStatus(acc)}`,
  ]
  const remainingCredits = overview?.remaining_credits
  const usageTotal = overview?.usage_total
  if (remainingCredits || usageTotal) {
    parts.push(`额度:${remainingCredits || '-'} / 已用:${usageTotal || '-'}`)
  }
  return parts.join(' / ')
}

function getPrimaryMetrics(acc: any) {
  const metrics = getDisplaySummary(acc)?.primary_metrics
  return Array.isArray(metrics) ? metrics : []
}

function getSecondaryMetrics(acc: any) {
  const metrics = getDisplaySummary(acc)?.secondary_metrics
  return Array.isArray(metrics) ? metrics : []
}

function getDisplayWarnings(acc: any) {
  const warnings = getDisplaySummary(acc)?.warnings
  return Array.isArray(warnings) ? warnings : []
}

function getDisplayBadges(acc: any) {
  const badges = getDisplaySummary(acc)?.badges
  return Array.isArray(badges) ? badges : []
}

function getDisplaySections(acc: any) {
  const sections = getDisplaySummary(acc)?.sections
  return Array.isArray(sections) ? sections : []
}

function getProviderAccounts(acc: any) {
  return Array.isArray(acc?.provider_accounts) ? acc.provider_accounts : []
}

function getCredentials(acc: any) {
  return Array.isArray(acc?.credentials) ? acc.credentials : []
}

function getCashierUrl(acc: any) {
  const overview = getAccountOverview(acc)
  return overview?.cashier_url || acc?.cashier_url || ''
}

function getPrimaryToken(acc: any) {
  if (acc?.primary_token) return acc.primary_token
  const credential = getCredentials(acc).find((item: any) => item?.scope === 'platform' && item?.credential_type === 'token' && item?.value)
  return credential?.value || ''
}

function escapeCsvField(value: unknown) {
  const text = value == null ? '' : String(value)
  if (!/[",\n\r]/.test(text)) return text
  return `"${text.replace(/"/g, '""')}"`
}

async function loadPlatformActions(platform: string, options?: { force?: boolean }) {
  const key = String(platform || '').trim()
  if (!key) return []
  const force = Boolean(options?.force)
  if (!force && platformActionsCache.has(key)) {
    return platformActionsCache.get(key) || []
  }
  if (!force && platformActionsPromiseCache.has(key)) {
    return platformActionsPromiseCache.get(key) || []
  }
  const pending = apiFetch(`/actions/${key}`)
    .then((data) => {
      const actions = Array.isArray(data?.actions) ? data.actions : []
      platformActionsCache.set(key, actions)
      platformActionsPromiseCache.delete(key)
      return actions
    })
    .catch((error) => {
      platformActionsPromiseCache.delete(key)
      throw error
    })
  platformActionsPromiseCache.set(key, pending)
  return pending
}

function buildActionParamDraft(action: any, acc: any) {
  const params = Array.isArray(action?.params) ? action.params : []
  const emailPrefix = String(acc?.email || '').split('@')[0] || 'Development'
  const draft: Record<string, string> = {}
  params.forEach((param: any) => {
    if (action?.id === 'create_api_key' && param?.key === 'name') {
      draft[param.key] = `${emailPrefix}Development`
      return
    }
    draft[param?.key || ''] = ''
  })
  return draft
}

// ── 注册弹框 ────────────────────────────────────────────────
function RegisterModal({
  platform,
  platformMeta,
  onClose,
  onDone,
}: {
  platform: string
  platformMeta: any
  onClose: () => void
  onDone: () => void
}) {
  const { t, language } = useI18n()
  const [config, setConfig] = useState<any | null>(null)
  const [configOptions, setConfigOptions] = useState<ConfigOptionsResponse>({
    mailbox_providers: [],
    captcha_providers: [],
    mailbox_settings: [],
    captcha_settings: [],
    captcha_policy: {},
    executor_options: [],
    identity_mode_options: [],
    oauth_provider_options: [],
  })
  const [configLoading, setConfigLoading] = useState(true)
  const [regCount, setRegCount] = useState(1)
  const [concurrency, setConcurrency] = useState(1)
  const [selection, setSelection] = useState({
    identityProvider: '',
    oauthProvider: '',
    executorType: '',
  })
  const [taskId, setTaskId] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [starting, setStarting] = useState(false)

  const supportedExecutors: string[] = platformMeta?.supported_executors || []
  const registrationOptions = buildRegistrationOptions(platformMeta, language)
  const reusableBrowser = hasReusableOAuthBrowser(config || {})
  const executorOptions = buildExecutorOptions(
    selection.identityProvider,
    supportedExecutors,
    reusableBrowser,
    platformMeta?.supported_executor_options || [],
    language,
  )
  const selectedRegistration = registrationOptions.find(option =>
    option.identityProvider === selection.identityProvider && option.oauthProvider === selection.oauthProvider,
  )
  const selectedExecutor = executorOptions.find(option => option.value === selection.executorType)

  useEffect(() => {
    let active = true
    setConfigLoading(true)
    Promise.all([
      getConfig().catch(() => ({})),
      getConfigOptions().catch(() => null),
    ])
      .then(([cfg, options]) => {
        if (!active) return
        setConfig(cfg || {})
        if (options) {
          setConfigOptions(options)
        }
      })
      .catch(() => {
        if (!active) return
        setConfig({})
        setConfigOptions({
          mailbox_providers: [],
          captcha_providers: [],
          mailbox_settings: [],
          captcha_settings: [],
          captcha_policy: {},
          executor_options: [],
          identity_mode_options: [],
          oauth_provider_options: [],
        })
      })
      .finally(() => {
        if (active) setConfigLoading(false)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (configLoading || registrationOptions.length === 0) return
    const cfg = config || {}
    const defaultRegistration = registrationOptions.find(option =>
      option.identityProvider === cfg.default_identity_provider &&
      (option.identityProvider !== 'oauth_browser' || option.oauthProvider === (cfg.default_oauth_provider || '')),
    ) || registrationOptions[0]
    setSelection((current) => {
      const identityProvider = current.identityProvider || defaultRegistration.identityProvider
      const oauthProvider = identityProvider === 'oauth_browser'
        ? (current.oauthProvider || defaultRegistration.oauthProvider)
        : ''
      const validExecutorOptions = buildExecutorOptions(
        identityProvider,
        supportedExecutors,
        hasReusableOAuthBrowser(cfg),
        platformMeta?.supported_executor_options || [],
        language,
      )
        .filter(option => !option.disabled)
      const preferredExecutor = identityProvider === 'oauth_browser'
        ? pickOAuthExecutor(supportedExecutors, cfg.default_executor || '', hasReusableOAuthBrowser(cfg))
        : ((cfg.default_executor && supportedExecutors.includes(cfg.default_executor)) ? cfg.default_executor : supportedExecutors[0] || '')
      const executorType = validExecutorOptions.some(option => option.value === current.executorType)
        ? current.executorType
        : (validExecutorOptions.find(option => option.value === preferredExecutor)?.value || validExecutorOptions[0]?.value || '')
      if (
        current.identityProvider === identityProvider &&
        current.oauthProvider === oauthProvider &&
        current.executorType === executorType
      ) {
        return current
      }
      return { identityProvider, oauthProvider, executorType }
    })
  }, [config, configLoading, registrationOptions, supportedExecutors])

  useEffect(() => {
    if (!selection.identityProvider) return
    const validExecutorOptions = buildExecutorOptions(
      selection.identityProvider,
      supportedExecutors,
      reusableBrowser,
      platformMeta?.supported_executor_options || [],
      language,
    )
      .filter(option => !option.disabled)
    if (!validExecutorOptions.some(option => option.value === selection.executorType)) {
      setSelection(current => {
        const nextExecutorType = validExecutorOptions[0]?.value || ''
        if (current.executorType === nextExecutorType) {
          return current
        }
        return {
          ...current,
          executorType: nextExecutorType,
        }
      })
    }
  }, [selection.identityProvider, selection.oauthProvider, selection.executorType, supportedExecutors, reusableBrowser])

  const defaultMailboxProvider = (configOptions.mailbox_settings || []).find(item => item.is_default) || configOptions.mailbox_settings?.[0] || null

  const start = async () => {
    setStarting(true)
    try {
      const cfg = config || {}
      const extra: Record<string, any> = {
        identity_provider: selection.identityProvider,
        oauth_provider: selection.oauthProvider,
        oauth_email_hint: cfg.oauth_email_hint,
        chrome_user_data_dir: cfg.chrome_user_data_dir,
        chrome_cdp_url: cfg.chrome_cdp_url,
      }
      if (selection.identityProvider === 'mailbox') {
        if (!defaultMailboxProvider?.provider_key) {
          throw new Error(t('accounts.missingDefaultMailbox'))
        }
        extra.mail_provider = defaultMailboxProvider.provider_key
      }
      const res = await apiFetch('/tasks/register', {
        method: 'POST',
        body: JSON.stringify({
          platform, count: regCount, concurrency,
          executor_type: selection.executorType,
          captcha_solver: 'auto',
          proxy: null,
          extra,
        }),
      })
      setTaskId(res.task_id)
    } finally { setStarting(false) }
  }

  const handleDone = () => {
    setDone(true)
    onDone()
  }

  const dialog = (
    <div className="dialog-backdrop" onClick={!taskId ? onClose : undefined}>
      <div className="dialog-panel dialog-panel-md flex flex-col"
           onClick={e => e.stopPropagation()} style={{maxHeight: '88vh'}}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">{t('accounts.autoRegister')} {platformMeta?.display_name || platform}</h2>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"><X className="h-4 w-4" /></button>
        </div>
        <div className="px-6 py-4 flex-1 overflow-y-auto flex flex-col gap-5">
          {!taskId ? (
            configLoading ? (
              <div className="text-sm text-[var(--text-muted)]">{t('accounts.loadingRegistrationConfig')}</div>
            ) : (
              <>
                <div>
                  <div className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Step 1</div>
                  <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{t('accounts.selectIdentity')}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">{t('accounts.selectIdentityDesc')}</div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {registrationOptions.map(option => {
                      const active = selection.identityProvider === option.identityProvider && selection.oauthProvider === option.oauthProvider
                      return (
                        <button
                          key={option.key}
                          type="button"
                          onClick={() => setSelection(current => ({
                            ...current,
                            identityProvider: option.identityProvider,
                            oauthProvider: option.oauthProvider,
                          }))}
                          className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                            active
                              ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                              : 'border-[var(--border)] bg-[var(--bg-pane)]/45 hover:border-[var(--accent)]/60'
                          }`}
                        >
                          <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                            {option.identityProvider === 'mailbox' ? <Mail className="h-4 w-4" /> : null}
                            {option.label}
                          </div>
                          <div className="mt-1 text-xs text-[var(--text-muted)]">{option.description}</div>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Step 2</div>
                  <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{t('accounts.selectExecutor')}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">{t('accounts.selectExecutorDesc')}</div>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    {executorOptions.map(option => {
                      const active = selection.executorType === option.value
                      return (
                        <button
                          key={option.value}
                          type="button"
                          disabled={option.disabled}
                          onClick={() => !option.disabled && setSelection(current => ({ ...current, executorType: option.value }))}
                          className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                            option.disabled
                              ? 'cursor-not-allowed border-[var(--border)] bg-[var(--bg-hover)] opacity-50'
                              : active
                                ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                                : 'border-[var(--border)] bg-[var(--bg-pane)]/45 hover:border-[var(--accent)]/60'
                          }`}
                        >
                          <div className="text-sm font-medium text-[var(--text-primary)]">{option.label}</div>
                          <div className="mt-1 text-xs text-[var(--text-muted)]">{option.description}</div>
                          {option.reason ? (
                            <div className="mt-2 text-xs text-amber-400">{option.reason}</div>
                          ) : null}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[var(--text-muted)] block mb-1">{t('accounts.registrationCount')}</label>
                    <input type="number" min={1} max={99} value={regCount}
                      onChange={e => setRegCount(Number(e.target.value))}
                      className="control-surface control-surface-compact text-center" />
                  </div>
                  <div>
                    <label className="text-xs text-[var(--text-muted)] block mb-1">{t('accounts.concurrency')}</label>
                    <input type="number" min={1} max={5} value={concurrency}
                      onChange={e => setConcurrency(Number(e.target.value))}
                      className="control-surface control-surface-compact text-center" />
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-4 py-3 text-xs text-[var(--text-secondary)]">
                  <div>{t('accounts.identitySummary')}: <span className="text-[var(--text-primary)]">{selectedRegistration?.label || '-'}</span></div>
                  <div className="mt-1">{t('accounts.executorSummary')}: <span className="text-[var(--text-primary)]">{selectedExecutor?.label || '-'}</span></div>
                  <div className="mt-1">{t('accounts.verificationSummary')}: <span className="text-[var(--text-primary)]">{getCaptchaStrategyLabel(selection.executorType, configOptions.captcha_policy, configOptions.captcha_providers, language)}</span></div>
                  {selection.identityProvider === 'oauth_browser' && !reusableBrowser && (
                    <div className="mt-2 text-amber-400">后台浏览器自动依赖 Chrome Profile 或 Chrome CDP，未配置时只允许可视浏览器自动。</div>
                  )}
                </div>

                <Button
                  onClick={start}
                  disabled={starting || !selection.identityProvider || !selection.executorType}
                  className="w-full"
                >
                  {starting ? t('accounts.starting') : t('accounts.startAutoRegister')}
                </Button>
              </>
            )
          ) : (
            <TaskLogPanel taskId={taskId} onDone={handleDone} />
          )}
        </div>
        <div className="px-6 py-3 border-t border-[var(--border)] flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            {done ? t('common.close') : t('common.cancel')}
          </Button>
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' ? createPortal(dialog, document.body) : dialog
}

// ── 新增账号弹框 ─────────────────────────────────────────
function AddModal({ platform, onClose, onDone }: { platform: string; onClose: () => void; onDone: () => void }) {
  const [form, setForm] = useState({ email: '', password: '', lifecycle_status: 'registered', primary_token: '', cashier_url: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true)
    try {
      await apiFetch('/accounts', {
        method: 'POST',
        body: JSON.stringify({ ...form, platform }),
      })
      onDone()
    } finally { setSaving(false) }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog-panel dialog-panel-sm"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">手动新增账号</h2>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"><X className="h-4 w-4" /></button>
        </div>
        <div className="px-6 py-4 space-y-3">
          {[['email','邮箱','text'],['password','密码','text'],['primary_token','主凭证','text'],['cashier_url','试用链接','text']].map(([k,l,t]) => (
            <div key={k}>
              <label className="text-xs text-[var(--text-muted)] block mb-1">{l}</label>
              <input type={t} value={(form as any)[k]} onChange={e => set(k, e.target.value)}
                className="control-surface" />
            </div>
          ))}
          <div>
            <label className="text-xs text-[var(--text-muted)] block mb-1">生命周期状态</label>
            <select value={form.lifecycle_status} onChange={e => set('lifecycle_status', e.target.value)}
              className="control-surface appearance-none">
              <option value="registered">已注册</option>
              <option value="trial">试用中</option>
              <option value="subscribed">已订阅</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 px-6 py-4 border-t border-[var(--border)]">
          <Button onClick={save} disabled={saving} className="flex-1">{saving ? '保存中...' : '保存'}</Button>
          <Button variant="outline" onClick={onClose} className="flex-1">取消</Button>
        </div>
      </div>
    </div>
  )
}

function formatResultValue(value: any) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return String(value)
}

function ResultStat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2">
      <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-muted)]">{label}</div>
      <div className="mt-1 text-sm font-medium text-[var(--text-primary)] break-all">{formatResultValue(value)}</div>
    </div>
  )
}

function metricToneClass(tone?: string) {
  if (tone === 'good') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
  if (tone === 'warning') return 'border-amber-500/25 bg-amber-500/10 text-amber-200'
  if (tone === 'danger') return 'border-red-500/25 bg-red-500/10 text-red-200'
  return 'border-[var(--border)] bg-[var(--bg-hover)] text-[var(--text-primary)]'
}

function metricAccentClass(tone?: string) {
  if (tone === 'good') return 'from-emerald-400/70 to-cyan-300/50'
  if (tone === 'warning') return 'from-amber-300/80 to-orange-300/50'
  if (tone === 'danger') return 'from-red-400/80 to-rose-300/50'
  return 'from-[var(--accent)]/80 to-[var(--accent-strong)]/45'
}

function DisplayMetricCard({ metric, compact = false }: { metric: any; compact?: boolean }) {
  return (
    <div className={`group relative overflow-hidden rounded-lg border px-3.5 py-3 ${metricToneClass(metric?.tone)}`}>
      <div className={`pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b ${metricAccentClass(metric?.tone)}`} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.18em] opacity-65">{metric?.label || '-'}</div>
          {metric?.sub ? <div className="mt-1 truncate text-[11px] opacity-65">{metric.sub}</div> : null}
        </div>
        <div className={`${compact ? 'text-sm' : 'text-lg'} shrink-0 font-semibold tracking-[-0.03em]`}>{formatResultValue(metric?.value)}</div>
      </div>
      {typeof metric?.percent === 'number' ? (
        <div className="relative mt-3 h-1.5 overflow-hidden rounded-full bg-black/25">
          <div className={`h-full rounded-full bg-gradient-to-r ${metricAccentClass(metric?.tone)}`} style={{ width: `${Math.max(0, Math.min(100, metric.percent))}%` }} />
        </div>
      ) : null}
    </div>
  )
}

function DisplayWarnings({ warnings }: { warnings: any[] }) {
  if (!warnings.length) return null
  return (
    <div className="space-y-2">
      {warnings.map((item: any, index: number) => (
        <div key={`${item?.key || 'warning'}-${index}`} className={`rounded-xl border px-3 py-2 text-xs ${metricToneClass(item?.tone || 'warning')}`}>
          {item?.message || '-'}
        </div>
      ))}
    </div>
  )
}

function DisplaySections({ sections }: { sections: any[] }) {
  if (!sections.length) return null
  return (
    <div className="space-y-3">
      {sections.map((section: any) => (
        <div key={section?.key || section?.title} className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-3">
          <div className="text-xs font-semibold text-[var(--text-primary)]">{section?.title || '明细'}</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {(Array.isArray(section?.items) ? section.items : []).map((item: any, index: number) => (
              <div key={`${item?.title || 'item'}-${index}`} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                <div className="text-xs font-semibold text-[var(--text-primary)]">{item?.title || '-'}</div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  {(Array.isArray(item?.metrics) ? item.metrics : []).map((metric: any) => (
                    <div key={metric?.key || metric?.label}>
                      <span className="text-[var(--text-muted)]">{metric?.label || '-'}: </span>
                      <span>{formatResultValue(metric?.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function ActionResultHighlights({ payload }: { payload: any }) {
  if (!payload || typeof payload !== 'object') return null

  const stats: Array<{ label: string; value: any }> = []
  if ('valid' in payload) stats.push({ label: '账号有效', value: payload.valid })
  if (payload.membership_type) stats.push({ label: '套餐', value: payload.membership_type })
  if (payload.plan) stats.push({ label: '套餐', value: payload.plan })
  if (payload.plan_id) stats.push({ label: 'Plan ID', value: payload.plan_id })
  if (typeof payload.has_valid_payment_method === 'boolean') stats.push({ label: '已绑卡', value: payload.has_valid_payment_method })
  if ('trial_eligible' in payload) stats.push({ label: '可试用', value: payload.trial_eligible })
  if (payload.trial_length_days) stats.push({ label: '试用天数', value: payload.trial_length_days })
  if (payload.remaining_credits) stats.push({ label: '剩余额度', value: payload.remaining_credits })
  if (payload.usage_total) stats.push({ label: '已用额度', value: payload.usage_total })
  if (payload.plan_credits) stats.push({ label: '总额度', value: payload.plan_credits })
  if (payload.usage_summary?.plan_title) stats.push({ label: 'Kiro 套餐', value: payload.usage_summary.plan_title })
  if ('days_until_reset' in (payload.usage_summary || {})) stats.push({ label: '重置倒计时', value: payload.usage_summary?.days_until_reset })
  if (payload.usage_summary?.next_reset_at) stats.push({ label: '下次重置', value: payload.usage_summary.next_reset_at })
  if ('available' in (payload.portal_session || {})) stats.push({ label: 'Portal 可用', value: payload.portal_session?.available })
  if (payload.desktop_app_state?.app_name) stats.push({ label: '桌面应用', value: payload.desktop_app_state?.app_name })
  if ('running' in (payload.desktop_app_state || {})) stats.push({ label: '桌面已打开', value: payload.desktop_app_state?.running })
  if ('ready' in (payload.desktop_app_state || {})) stats.push({ label: '桌面就绪', value: payload.desktop_app_state?.ready })
  if (payload.key_prefix) stats.push({ label: 'API Key 前缀', value: payload.key_prefix })
  if (payload.key_prefix && payload.name) stats.push({ label: 'Key 名称', value: payload.name })
  if (payload.key_prefix && payload.id) stats.push({ label: 'Key ID', value: payload.id })

  const cursorModels = payload.usage_summary?.models && typeof payload.usage_summary.models === 'object'
    ? Object.entries(payload.usage_summary.models)
    : []
  const kiroBreakdowns = Array.isArray(payload.usage_summary?.breakdowns)
    ? payload.usage_summary.breakdowns
    : []
  const kiroPlans = Array.isArray(payload.usage_summary?.plans)
    ? payload.usage_summary.plans
    : []

  if (stats.length === 0 && cursorModels.length === 0 && kiroBreakdowns.length === 0 && kiroPlans.length === 0 && !payload.quota_note) {
    return null
  }

  return (
    <div className="space-y-4 mb-4">
      {stats.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map(item => <ResultStat key={item.label} label={item.label} value={item.value} />)}
        </div>
      )}

      {cursorModels.length > 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-4">
          <div className="text-sm font-semibold text-[var(--text-primary)]">Cursor Usage</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {cursorModels.map(([model, info]: [string, any]) => (
              <div key={model} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                <div className="text-xs font-semibold text-[var(--text-primary)]">{model}</div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <div>请求数: {formatResultValue(info?.num_requests)}</div>
                  <div>总请求: {formatResultValue(info?.num_requests_total)}</div>
                  <div>Token: {formatResultValue(info?.num_tokens)}</div>
                  <div>剩余请求: {formatResultValue(info?.remaining_requests)}</div>
                  <div>请求上限: {formatResultValue(info?.max_request_usage)}</div>
                  <div>Token 上限: {formatResultValue(info?.max_token_usage)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {kiroBreakdowns.length > 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-4">
          <div className="text-sm font-semibold text-[var(--text-primary)]">Kiro Usage</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {kiroBreakdowns.map((item: any, index: number) => (
              <div key={`${item.resource_type || item.display_name}-${index}`} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                <div className="text-xs font-semibold text-[var(--text-primary)]">{item.display_name || item.resource_type}</div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <div>已用: {formatResultValue(item.current_usage)}</div>
                  <div>上限: {formatResultValue(item.usage_limit)}</div>
                  <div>剩余: {formatResultValue(item.remaining_usage)}</div>
                  <div>单位: {formatResultValue(item.unit)}</div>
                  <div>试用状态: {formatResultValue(item.trial_status)}</div>
                  <div>试用到期: {formatResultValue(item.trial_expiry)}</div>
                  <div>试用上限: {formatResultValue(item.trial_usage_limit)}</div>
                  <div>试用剩余: {formatResultValue(item.trial_remaining_usage)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {kiroPlans.length > 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-4">
          <div className="text-sm font-semibold text-[var(--text-primary)]">Kiro Plans</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {kiroPlans.map((plan: any) => (
              <div key={plan.name} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs font-semibold text-[var(--text-primary)]">{plan.title || plan.name}</div>
                  <div className="text-xs text-emerald-400">{formatResultValue(plan.amount)} {plan.currency || ''}</div>
                </div>
                <div className="mt-1 text-[11px] text-[var(--text-muted)]">{plan.billing_interval || '-'}</div>
                {Array.isArray(plan.features) && plan.features.length > 0 && (
                  <div className="mt-2 text-xs text-[var(--text-secondary)] break-words">
                    {plan.features.join(' · ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {payload.quota_note && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
          {payload.quota_note}
        </div>
      )}
    </div>
  )
}

function ActionResultModal({
  title,
  payload,
  onClose,
}: {
  title: string
  payload: any
  onClose: () => void
}) {
  const content = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2)

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="dialog-panel dialog-panel-lg"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">操作结果</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(content)}>
              <Copy className="h-4 w-4 mr-1" />
              复制
            </Button>
            <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="px-6 py-4">
          <ActionResultHighlights payload={payload} />
          <pre className="bg-[var(--bg-hover)] border border-[var(--border)] rounded-xl p-4 text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-all overflow-auto max-h-[65vh]">
            {content}
          </pre>
        </div>
      </div>
    </div>
  )
}

function ActionTaskModal({
  title,
  taskId,
  taskStatus,
  onClose,
  onDone,
}: {
  title: string
  taskId: string
  taskStatus: string | null
  onClose: () => void
  onDone: (status: string) => void
}) {
  const { t, language } = useI18n()
  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="dialog-panel flex w-[min(960px,calc(100vw-32px))] max-w-none flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
        style={{ maxHeight: '90vh' }}
      >
        <div className="relative overflow-hidden border-b border-[var(--border)] px-6 py-5">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_0%,rgba(9,182,162,0.18),transparent_34%),linear-gradient(90deg,rgba(255,255,255,0.04),transparent)]" />
          <div className="relative flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="mb-2 inline-flex rounded-full border border-[var(--border)] bg-[var(--chip-bg)] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                Platform Action
              </div>
              <h2 className="truncate text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
              <p className="mt-1 text-xs text-[var(--text-muted)]">任务状态、错误摘要与实时日志集中展示</p>
            </div>
            <div className="flex items-center gap-2">
              {taskStatus ? (
                <Badge variant={TASK_STATUS_VARIANTS[taskStatus] || 'secondary'}>
                  {getTaskStatusText(taskStatus, language)}
                </Badge>
              ) : null}
              <button onClick={onClose} className="rounded-full border border-[var(--border)] bg-[var(--bg-hover)] p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <TaskLogPanel taskId={taskId} onDone={onDone} />
        </div>
        <div className="flex items-center justify-between border-t border-[var(--border)] px-6 py-3 text-xs text-[var(--text-muted)]">
          <span>{t('taskHistory.taskId')}: {taskId}</span>
          <Button variant="outline" size="sm" onClick={onClose}>
            {t('common.close')}
          </Button>
        </div>
      </div>
    </div>
  )
}

function ActionParamsModal({
  action,
  initialValues,
  submitting,
  onClose,
  onSubmit,
}: {
  action: any
  initialValues: Record<string, string>
  submitting: boolean
  onClose: () => void
  onSubmit: (params: Record<string, string>) => void
}) {
  const [form, setForm] = useState<Record<string, string>>(initialValues)

  useEffect(() => {
    setForm(initialValues)
  }, [action?.id, initialValues])

  const params = Array.isArray(action?.params) ? action.params : []

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="dialog-panel dialog-panel-md"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">{action?.label || '动作参数'}</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">填写执行该动作所需的参数</p>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-6 py-4 space-y-4">
          {params.map((param: any) => {
            const value = form[param.key] ?? ''
            if (Array.isArray(param.options) && param.options.length > 0) {
              return (
                <label key={param.key} className="block">
                  <div className="mb-1 text-xs text-[var(--text-muted)]">{param.label || param.key}</div>
                  <select
                    value={value}
                    onChange={e => setForm(current => ({ ...current, [param.key]: e.target.value }))}
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2 text-sm outline-none focus:border-[var(--text-accent)]"
                  >
                    {param.options.map((option: string) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
              )
            }
            if (param.type === 'textarea') {
              return (
                <label key={param.key} className="block">
                  <div className="mb-1 text-xs text-[var(--text-muted)]">{param.label || param.key}</div>
                  <textarea
                    value={value}
                    onChange={e => setForm(current => ({ ...current, [param.key]: e.target.value }))}
                    rows={3}
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2 text-sm outline-none focus:border-[var(--text-accent)]"
                  />
                </label>
              )
            }
            return (
              <label key={param.key} className="block">
                <div className="mb-1 text-xs text-[var(--text-muted)]">{param.label || param.key}</div>
                <input
                  type={param.type === 'number' ? 'number' : 'text'}
                  value={value}
                  onChange={e => setForm(current => ({ ...current, [param.key]: e.target.value }))}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2 text-sm outline-none focus:border-[var(--text-accent)]"
                />
              </label>
            )
          })}
        </div>
        <div className="px-6 py-4 border-t border-[var(--border)] flex gap-3">
          <Button onClick={() => onSubmit(form)} disabled={submitting} className="flex-1">
            {submitting ? '执行中...' : '执行'}
          </Button>
          <Button variant="outline" onClick={onClose} disabled={submitting} className="flex-1">取消</Button>
        </div>
      </div>
    </div>
  )
}
// ── 行操作菜单 ─────────────────────────────────────────────
function ActionMenu({
  acc,
  onDetail,
  onDelete,
  onResult,
  onChanged,
}: {
  acc: any
  onDetail: () => void
  onDelete: () => void
  onResult: (title: string, payload: any) => void
  onChanged: () => void
}) {
  const { language } = useI18n()
  const [open, setOpen] = useState(false)
  const [actions, setActions] = useState<any[]>([])
  const [running, setRunning] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [actionTask, setActionTask] = useState<{ taskId: string; title: string } | null>(null)
  const [actionTaskStatus, setActionTaskStatus] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<{ action: any; params: Record<string, string> } | null>(null)
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0, maxHeight: 320 })
  const menuRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const runAction = (action: any, params: Record<string, any>) => {
    setRunning(action.id)
    setActionTaskStatus(null)
    apiFetch(`/actions/${acc.platform}/${acc.id}/${action.id}`, { method: 'POST', body: JSON.stringify({ params }) })
      .then(resp => {
        if (resp?.sync) {
          setRunning(null)
          if (!resp.ok) {
            setToast({ type: 'error', text: resp.error || 'Operation failed' })
            return
          }
          onChanged()
          if (resp.data?.url || resp.data?.checkout_url || resp.data?.cashier_url) {
            const actionUrl = resp.data?.url || resp.data?.checkout_url || resp.data?.cashier_url
            window.open(actionUrl, '_blank')
            try {
              navigator.clipboard.writeText(actionUrl)
            } catch {
              // Ignore clipboard errors
            }
          }
          onResult(action.label, resp.data)
          return
        }
        setActionTask({
          taskId: resp.task_id,
          title: `${acc.email} · ${action.label}`,
        })
      })
      .catch(() => {
        setRunning(null)
        setToast({ type: 'error', text: 'Request failed' })
      })
  }

  const updateMenuPosition = useCallback(() => {
    const trigger = triggerRef.current
    if (!trigger) return

    const rect = trigger.getBoundingClientRect()
    const viewportPadding = 12
    const menuWidth = 220
    const estimatedHeight = Math.min(320, actions.length * 40 + 56)

    let left = rect.right - menuWidth
    if (left < viewportPadding) left = viewportPadding
    if (left + menuWidth > window.innerWidth - viewportPadding) {
      left = Math.max(viewportPadding, window.innerWidth - menuWidth - viewportPadding)
    }

    let top = rect.bottom + 8
    if (top + estimatedHeight > window.innerHeight - viewportPadding) {
      top = Math.max(viewportPadding, rect.top - estimatedHeight - 8)
    }

    setMenuPosition({
      top: Math.round(top),
      left: Math.round(left),
      maxHeight: Math.max(160, window.innerHeight - viewportPadding * 2),
    })
  }, [actions.length])

  useEffect(() => {
    let active = true
    loadPlatformActions(acc.platform)
      .then((items) => {
        if (active) setActions(items)
      })
      .catch(() => {
        if (active) setActions([])
      })
    return () => {
      active = false
    }
  }, [acc.platform])
  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 4000); return () => clearTimeout(t) }
  }, [toast])
  useEffect(() => {
    if (!open) return
    let active = true
    loadPlatformActions(acc.platform, { force: true })
      .then((items) => {
        if (active) setActions(items)
      })
      .catch(() => {
        if (active) setActions([])
      })
    updateMenuPosition()
    const handler = (e: MouseEvent) => {
      const target = e.target as Node
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      setOpen(false)
    }
    const reposition = () => updateMenuPosition()
    document.addEventListener('mousedown', handler)
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    return () => {
      active = false
      document.removeEventListener('mousedown', handler)
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
    }
  }, [open, acc.platform, updateMenuPosition])

  const handleActionDone = async (status: string) => {
    if (!actionTask) return
    setActionTaskStatus(status)
    setRunning(null)
    try {
      const task = await apiFetch(`/tasks/${actionTask.taskId}`)
      const data = task?.data ?? task?.result?.data
      if (status !== 'succeeded') {
        setToast({ type: 'error', text: task?.error || getTaskStatusText(status, language) })
        return
      }
      onChanged()
      const actionUrl = data?.url || data?.checkout_url || data?.cashier_url
      if (actionUrl) {
        window.open(actionUrl, '_blank')
        try {
          await navigator.clipboard.writeText(actionUrl)
        } catch {
          // ignore clipboard failures
        }
      }
      if (data && typeof data === 'object') {
        if (actionUrl) {
          setToast({ type: 'success', text: data.message || '支付链接已在新标签打开，链接已复制' })
          return
        }
        const detailKeys = Object.keys(data).filter(key => !['message', 'url', 'checkout_url', 'cashier_url'].includes(key))
        if (detailKeys.length > 0) {
          onResult(actionTask.title, data)
        }
        setToast({ type: 'success', text: data.message || '操作成功' })
        return
      }
      setToast({ type: 'success', text: typeof data === 'string' && data ? data : '操作成功' })
    } catch (error: any) {
      setToast({ type: 'error', text: error?.message || '读取任务结果失败' })
    }
  }

  return (
    <div className="relative flex min-w-[136px] items-center justify-end gap-1.5 whitespace-nowrap">
      {toast && (
        <div
          className="fixed top-5 right-5 z-[9999] flex items-center gap-2.5 rounded-xl border px-4 py-3 text-[13px] font-medium shadow-lg  cursor-pointer transition-all"
          style={{
            background: toast.type === 'success' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
            borderColor: toast.type === 'success' ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)',
            color: toast.type === 'success' ? '#6ee7b7' : '#fca5a5',
          }}
          onClick={() => setToast(null)}
        >
          <span className="text-base">{toast.type === 'success' ? '✓' : '✗'}</span>
          <span>{toast.text}</span>
        </div>
      )}
      {actionTask && (
        <ActionTaskModal
          title={actionTask.title}
          taskId={actionTask.taskId}
          taskStatus={actionTaskStatus}
          onClose={() => {
            setActionTask(null)
            setActionTaskStatus(null)
          }}
          onDone={handleActionDone}
        />
      )}
      {pendingAction && (
        <ActionParamsModal
          action={pendingAction.action}
          initialValues={pendingAction.params}
          submitting={running === pendingAction.action?.id}
          onClose={() => {
            if (!running) setPendingAction(null)
          }}
          onSubmit={(params) => {
            const action = pendingAction.action
            setPendingAction(null)
            runAction(action, params)
          }}
        />
      )}
      <button onClick={onDetail} className="table-action-btn">详情</button>
      {actions.length > 0 && (
        <div className="relative">
          <button ref={triggerRef} onClick={() => setOpen(o => !o)}
            className="table-action-btn">更多 ▾</button>
          {open && typeof document !== 'undefined' && createPortal(
            <div
              ref={menuRef}
              className="fixed z-[9999] w-[220px] overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]/96 py-1.5 shadow-[var(--shadow-soft)] "
              style={{ top: menuPosition.top, left: menuPosition.left, maxHeight: menuPosition.maxHeight }}
            >
              {actions.map(a => (
                <button key={a.id}
                  onClick={() => {
                    setOpen(false)
                    if (Array.isArray(a.params) && a.params.length > 0) {
                      setPendingAction({
                        action: a,
                        params: buildActionParamDraft(a, acc),
                      })
                      return
                    }
                    runAction(a, {})
                  }}
                  disabled={!!running}
                  className="w-full px-3 py-2 text-left text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50">
                  {running === a.id ? '执行中...' : a.label}
                </button>
              ))}
              <div className="my-1 border-t border-[var(--border)]/70" />
              <button
                onClick={() => {
                  setOpen(false)
                  if (confirm(`确认删除 ${acc.email}？`)) {
                    apiFetch(`/accounts/${acc.id}`, { method: 'DELETE' }).then(onDelete)
                  }
                }}
                className="w-full px-3 py-2 text-left text-xs text-[#f0b0b0] transition-colors hover:bg-[rgba(239,68,68,0.08)] hover:text-[#ffd5d5]"
              >
                删除
              </button>
            </div>,
            document.body,
          )}
        </div>
      )}
      {actions.length === 0 && (
        <button
          onClick={() => { if (confirm(`确认删除 ${acc.email}？`)) apiFetch(`/accounts/${acc.id}`, { method: 'DELETE' }).then(onDelete) }}
          className="table-action-btn table-action-btn-danger"
        >
          删除
        </button>
      )}
    </div>
  )
}

// ── 账号详情弹框 ───────────────────────────────────────────
function DetailModal({ acc, onClose, onSave }: { acc: any; onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({
    lifecycle_status: getLifecycleStatus(acc),
    primary_token: getPrimaryToken(acc),
    cashier_url: getCashierUrl(acc),
  })
  const [saving, setSaving] = useState(false)
  const overview = getAccountOverview(acc)
  const verificationMailbox = getVerificationMailbox(acc)
  const providerAccounts = getProviderAccounts(acc)
  const credentials = getCredentials(acc)
  const primaryMetrics = getPrimaryMetrics(acc)
  const secondaryMetrics = getSecondaryMetrics(acc)
  const warnings = getDisplayWarnings(acc)
  const displayBadges = getDisplayBadges(acc)
  const displaySections = getDisplaySections(acc)
  const copyText = (text: string) => navigator.clipboard.writeText(text)
  const platformCredentials = credentials.filter((item: any) => item.scope === 'platform')

  const save = async () => {
    setSaving(true)
    try {
      await apiFetch(`/accounts/${acc.id}`, { method: 'PATCH', body: JSON.stringify(form) })
      onSave()
    } finally { setSaving(false) }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog-panel dialog-panel-sm flex flex-col" style={{maxHeight:'90vh'}} onClick={e => e.stopPropagation()}>
        {/* ── Sticky Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] shrink-0">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">账号详情</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{acc.email}</p>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"><X className="h-4 w-4" /></button>
        </div>
        {/* ── Scrollable Content ── */}
        <div className="px-6 py-4 space-y-3 flex-1 overflow-y-auto min-h-0">
          <div className="relative overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--accent-soft)] p-4 shadow-[var(--shadow-soft)]">
            <div className="pointer-events-none absolute -right-16 -top-20 h-44 w-44 rounded-full bg-[var(--accent-soft)] blur-3xl" />
            <div className="relative flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">核心状态</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant={STATUS_VARIANT[getDisplayStatus(acc)] || 'secondary'}>{getDisplayStatus(acc)}</Badge>
                  <span className="text-lg font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{acc.plan_name || overview.plan_name || overview.plan || getPlanState(acc)}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-right text-[11px] text-[var(--text-muted)] sm:grid-cols-3">
                <div className="rounded-xl border border-[var(--border-soft)] bg-black/10 px-2.5 py-2">
                  <div className="uppercase tracking-[0.12em]">生命周期</div>
                  <div className="mt-1 text-[var(--text-primary)]">{getLifecycleStatus(acc)}</div>
                </div>
                <div className="rounded-xl border border-[var(--border-soft)] bg-black/10 px-2.5 py-2">
                  <div className="uppercase tracking-[0.12em]">有效性</div>
                  <div className="mt-1 text-[var(--text-primary)]">{getValidityStatus(acc)}</div>
                </div>
                <div className="rounded-xl border border-[var(--border-soft)] bg-black/10 px-2.5 py-2">
                  <div className="uppercase tracking-[0.12em]">套餐状态</div>
                  <div className="mt-1 text-[var(--text-primary)]">{getPlanState(acc)}</div>
                </div>
              </div>
            </div>
            {secondaryMetrics.length > 0 && (
              <div className="relative mt-4 grid gap-2 sm:grid-cols-2">
                {secondaryMetrics.slice(0, 4).map((metric: any) => (
                  <DisplayMetricCard key={metric.key || metric.label} metric={metric} compact />
                ))}
              </div>
            )}
          </div>

          {primaryMetrics.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {primaryMetrics.map((metric: any) => (
                <DisplayMetricCard key={metric.key || metric.label} metric={metric} />
              ))}
            </div>
          )}

          <DisplayWarnings warnings={warnings} />
          <DisplaySections sections={displaySections} />

          {(displayBadges.length > 0 || verificationMailbox?.email) && (
            <div className="space-y-2">
              {displayBadges.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {displayBadges.map((badge: any, index: number) => (
                    <span key={`${badge?.label || 'badge'}-${index}`} className="rounded-full border border-[var(--border)] bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                      {badge?.label}
                    </span>
                  ))}
                </div>
              )}
              {verificationMailbox?.email && (
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2 text-xs text-[var(--text-secondary)]">
                  验证码邮箱: {verificationMailbox.email} · {verificationMailbox.provider || '-'} · ID {verificationMailbox.account_id || '-'}
                </div>
              )}
            </div>
          )}
          {providerAccounts.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs text-[var(--text-muted)] block">Provider Accounts</label>
              {providerAccounts.map((item: any, index: number) => (
                <div key={`${item.provider_name || 'provider'}-${item.login_identifier || index}`} className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-3">
                  <div className="text-xs font-semibold text-[var(--text-primary)]">
                    {item.provider_name || item.provider_type || 'provider'}
                  </div>
                  <div className="mt-1 text-xs text-[var(--text-secondary)] break-all">
                    登录标识: {item.login_identifier || '-'}
                  </div>
                  {item.credentials && Object.keys(item.credentials).length > 0 && (
                    <div className="mt-2 grid gap-2">
                      {Object.entries(item.credentials).map(([key, value]: [string, any]) => (
                        <div key={key}>
                          <div className="text-[11px] text-[var(--text-muted)]">{key}</div>
                          <div className="flex items-start gap-1">
                            <div className="flex-1 rounded-md border border-[var(--border)] bg-black/20 px-2 py-1.5 text-xs font-mono text-[var(--text-secondary)] break-all max-h-40 overflow-y-auto">
                              {String(value || '-')}
                            </div>
                            {value ? (
                              <button onClick={() => copyText(String(value))} className="mt-1 shrink-0 text-[var(--text-muted)] hover:text-[var(--text-secondary)]">
                                <Copy className="h-3 w-3" />
                              </button>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {platformCredentials.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs text-[var(--text-muted)] block">Platform Credentials</label>
              {platformCredentials.map((item: any) => (
                <div key={`${item.scope}-${item.key}`} className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] p-3">
                  <div className="text-[11px] text-[var(--text-muted)]">{item.key}</div>
                  <div className="mt-1 flex items-start gap-1">
                    <div className="flex-1 rounded-md border border-[var(--border)] bg-black/20 px-2 py-1.5 text-xs font-mono text-[var(--text-secondary)] break-all max-h-40 overflow-y-auto">
                      {item.value}
                    </div>
                    <button onClick={() => copyText(String(item.value || ''))} className="mt-1 shrink-0 text-[var(--text-muted)] hover:text-[var(--text-secondary)]">
                      <Copy className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div>
            <label className="text-xs text-[var(--text-muted)] block mb-1">生命周期状态</label>
            <select value={form.lifecycle_status} onChange={e => setForm(f => ({ ...f, lifecycle_status: e.target.value }))}
              className="control-surface appearance-none">
              {['registered','trial','subscribed','expired','invalid'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] block mb-1">主凭证</label>
            <textarea value={form.primary_token} onChange={e => setForm(f => ({ ...f, primary_token: e.target.value }))}
              rows={2} className="control-surface control-surface-mono resize-none" />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] block mb-1">试用链接</label>
            <textarea value={form.cashier_url} onChange={e => setForm(f => ({ ...f, cashier_url: e.target.value }))}
              rows={2} className="control-surface control-surface-mono resize-none" />
          </div>
        </div>
        {/* ── Sticky Footer ── */}
        <div className="flex gap-3 px-6 py-4 border-t border-[var(--border)] shrink-0">
          <Button onClick={save} disabled={saving} className="flex-1">{saving ? '保存中...' : '保存'}</Button>
          <Button variant="outline" onClick={onClose} className="flex-1">取消</Button>
        </div>
      </div>
    </div>
  )
}

// ── 导入弹框 ────────────────────────────────────────────────
function ImportModal({ platform, onClose, onDone }: { platform: string; onClose: () => void; onDone: () => void }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const submit = async () => {
    setLoading(true)
    try {
      const lines = text.trim().split('\n').filter(Boolean)
      const res = await apiFetch('/accounts/import', { method: 'POST', body: JSON.stringify({ platform, lines }) })
      setResult(`导入成功 ${res.created} 个`); onDone()
    } catch (e: any) { setResult(`失败: ${e.message}`) } finally { setLoading(false) }
  }
  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog-panel dialog-panel-sm p-6" onClick={e => e.stopPropagation()}>
        <h2 className="text-base font-semibold text-[var(--text-primary)] mb-2">批量导入</h2>
        <p className="text-xs text-[var(--text-muted)] mb-3">每行格式: <code className="bg-[var(--bg-hover)] px-1 rounded">email password [cashier_url]</code></p>
        <textarea value={text} onChange={e => setText(e.target.value)} rows={8}
          className="control-surface control-surface-mono resize-none mb-3" />
        {result && <p className="text-sm text-emerald-400 mb-3">{result}</p>}
        <div className="flex gap-2">
          <Button onClick={submit} disabled={loading} className="flex-1">{loading ? '导入中...' : '导入'}</Button>
          <Button variant="outline" onClick={onClose} className="flex-1">取消</Button>
        </div>
      </div>
    </div>
  )
}

function ExportMenu({
  platform,
  total,
  statusFilter,
  searchFilter,
  selectedIds,
}: {
  platform: string
  total: number
  statusFilter: string
  searchFilter: string
  selectedIds: number[]
}) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const hasSelection = selectedIds.length > 0

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const doExport = async (format: string) => {
    setLoading(format)
    try {
      const { blob, filename } = await apiDownload(`/accounts/export/${format}`, {
        method: 'POST',
        body: JSON.stringify({
          platform,
          ids: hasSelection ? selectedIds : [],
          select_all: !hasSelection,
          status_filter: !hasSelection ? statusFilter || null : null,
          search_filter: !hasSelection ? searchFilter || null : null,
        }),
      })
      triggerBrowserDownload(blob, filename)
      setOpen(false)
    } catch (e: any) {
      window.alert(e?.message || '导出失败')
    } finally {
      setLoading(null)
    }
  }

  const options = [
    { key: 'json', label: '导出 JSON' },
    { key: 'csv', label: '导出 CSV' },
    { key: 'any2api', label: '导出 Any2Api' },
    { key: 'sub2api', label: '导出 Sub2Api' },
    { key: 'cpa', label: '导出 CPA' },
    ...(platform === 'kiro' ? [{ key: 'kiro-go', label: '导出 Kiro-Go' }] : []),
  ]

  return (
    <div className="relative" ref={menuRef}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(v => !v)}
        disabled={total === 0 || !!loading}
      >
        <Download className="h-4 w-4 mr-1" />
        {loading ? '导出中...' : hasSelection ? `导出已选(${selectedIds.length})` : '导出'}
      </Button>
      {open && (
        <div className="absolute right-0 top-10 z-20 min-w-[148px] rounded-lg border border-[var(--border)] bg-[var(--bg-card)] py-1 shadow-lg">
          <div className="px-3 py-1 text-[11px] text-[var(--text-muted)]">
            {hasSelection ? `导出 ${selectedIds.length} 个已选账号` : '导出当前筛选结果'}
          </div>
          {options.map(option => (
            <button
              key={option.key}
              onClick={() => doExport(option.key)}
              className="w-full px-3 py-1.5 text-left text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main ────────────────────────────────────────────────────
export default function Accounts() {
  const { t, language } = useI18n()
  const { platform } = useParams<{ platform: string }>()
  const [tab, setTab] = useState(platform || '')
  useEffect(() => { if (platform) { setTab(platform) } }, [platform])

  const [accounts, setAccounts] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [detail, setDetail] = useState<any | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [showRegister, setShowRegister] = useState(false)
  const [platformsMap, setPlatformsMap] = useState<Record<string, any>>({})
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [actionResult, setActionResult] = useState<{ title: string; payload: any } | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [batchRefreshing, setBatchRefreshing] = useState(false)
  const [batchTask, setBatchTask] = useState<{ taskId: string; title: string } | null>(null)
  const [batchTaskStatus, setBatchTaskStatus] = useState<string | null>(null)

  useEffect(() => {
    getPlatforms().then((list: any[]) => {
      const map: Record<string, any> = {}
      list.forEach(p => { map[p.name] = p })
      setPlatformsMap(map)
      if (!platform && !tab && list[0]?.name) {
        setTab(list[0].name)
      }
    }).catch(() => {})
  }, [platform, tab])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 400)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    setSelectedIds(new Set())
  }, [tab, filterStatus, debouncedSearch])

  const load = useCallback(async (p = tab, s = debouncedSearch, fs = filterStatus) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ platform: p, page: '1', page_size: '100' })
      if (s) params.set('email', s)
      if (fs) params.set('status', fs)
      const data = await apiFetch(`/accounts?${params}`)
      setAccounts(data.items); setTotal(data.total)
    } finally { setLoading(false) }
  }, [tab, debouncedSearch, filterStatus])

  useEffect(() => { load(tab, debouncedSearch, filterStatus) }, [tab, debouncedSearch, filterStatus])

  useEffect(() => {
    setSelectedIds(prev => {
      const visible = new Set(accounts.map(acc => acc.id))
      return new Set([...prev].filter(id => visible.has(id)))
    })
  }, [accounts])

  
  const exportCsv = () => {
    const header = 'email,password,display_status,lifecycle_status,plan_state,validity_status,cashier_url,created_at'
    const rowsSource = selectedIds.size > 0 ? accounts.filter(a => selectedIds.has(a.id)) : accounts
    const rows = rowsSource.map(a => [
      a.email,
      a.password,
      getDisplayStatus(a),
      getLifecycleStatus(a),
      getPlanState(a),
      getValidityStatus(a),
      getCashierUrl(a),
      a.created_at,
    ].map(escapeCsvField).join(','))
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    triggerBrowserDownload(blob, `${tab}_accounts.csv`)
  }

  const pageIds = accounts.map(acc => acc.id)
  const allSelectedOnPage = pageIds.length > 0 && pageIds.every(id => selectedIds.has(id))
  const selectedCount = selectedIds.size

  const toggleOne = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const togglePage = () => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (allSelectedOnPage) pageIds.forEach(id => next.delete(id))
      else pageIds.forEach(id => next.add(id))
      return next
    })
  }

  const copy = (text: string) => {
    if (navigator.clipboard) { navigator.clipboard.writeText(text) }
    else { const el = document.createElement('textarea'); el.value = text; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el) }
  }

  const currentPlatformMeta = platformsMap[tab]
  const platformLabel = currentPlatformMeta?.display_name || tab
  const visibleTrial = accounts.filter(acc => getPlanState(acc) === 'trial').length
  const visibleSubscribed = accounts.filter(acc => getPlanState(acc) === 'subscribed').length
  const visibleInvalid = accounts.filter(acc => getValidityStatus(acc) === 'invalid' || getLifecycleStatus(acc) === 'invalid').length
  const linkedCashier = accounts.filter(acc => Boolean(getCashierUrl(acc))).length

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
      {detail && <DetailModal acc={detail} onClose={() => setDetail(null)} onSave={() => { setDetail(null); load() }} />}
      {showImport && <ImportModal platform={tab} onClose={() => setShowImport(false)} onDone={() => { setShowImport(false); load() }} />}
      {showAdd && <AddModal platform={tab} onClose={() => setShowAdd(false)} onDone={() => { setShowAdd(false); load() }} />}
      {showRegister && <RegisterModal platform={tab} platformMeta={platformsMap[tab]} onClose={() => setShowRegister(false)} onDone={() => load()} />}
      {actionResult && <ActionResultModal title={actionResult.title} payload={actionResult.payload} onClose={() => setActionResult(null)} />}
      {batchTask && (
        <ActionTaskModal
          title={batchTask.title}
          taskId={batchTask.taskId}
          taskStatus={batchTaskStatus}
          onClose={() => {
            setBatchTask(null)
            setBatchTaskStatus(null)
            setBatchRefreshing(false)
            load()
          }}
          onDone={(status) => {
            setBatchTaskStatus(status)
            setBatchRefreshing(false)
            load()
          }}
        />
      )}

      <Card className="shrink-0 bg-[var(--bg-pane)]/40 border border-[var(--border)] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 px-5 py-4 border-b border-[var(--border)]/50">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
              {platformLabel}
            </h1>
            <div className="h-4 w-[1px] bg-[var(--border)]"></div>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-[var(--text-muted)]">{t('accounts.count', { count: total })}</span>
              {visibleTrial > 0 && <span className="flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 font-medium text-emerald-500 ring-1 ring-inset ring-emerald-500/20">{t('accounts.trial', { count: visibleTrial })}</span>}
              {visibleSubscribed > 0 && <span className="flex items-center rounded-full bg-blue-500/10 px-2 py-0.5 font-medium text-blue-500 ring-1 ring-inset ring-blue-500/20">{t('accounts.subscribed', { count: visibleSubscribed })}</span>}
              {linkedCashier > 0 && <span className="flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 font-medium text-amber-500 ring-1 ring-inset ring-amber-500/20">{t('accounts.linked', { count: linkedCashier })}</span>}
              {visibleInvalid > 0 && <span className="flex items-center rounded-full bg-red-500/10 px-2 py-0.5 font-medium text-red-500 ring-1 ring-inset ring-red-500/20">{t('accounts.invalid', { count: visibleInvalid })}</span>}
              {selectedCount > 0 && <span className="flex items-center rounded-full bg-[var(--text-primary)]/10 px-2 py-0.5 font-medium text-[var(--text-primary)] ring-1 ring-inset ring-[var(--text-primary)]/20">{t('accounts.selected', { count: selectedCount })}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setShowRegister(true)} className="h-8 shadow-sm">
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t('accounts.autoRegister')}
            </Button>
            <div className="h-4 w-[1px] bg-[var(--border)]"></div>
            <Button size="sm" variant="outline" onClick={() => setShowImport(true)} className="h-8 bg-transparent">
              <Upload className="mr-1.5 h-3.5 w-3.5" />
              {t('accounts.import')}
            </Button>
            {tab === 'chatgpt' ? (
              <ExportMenu
                platform={tab}
                total={total}
                statusFilter={filterStatus}
                searchFilter={debouncedSearch}
                selectedIds={[...selectedIds]}
              />
            ) : (
              <Button size="sm" variant="outline" onClick={exportCsv} disabled={accounts.length === 0} className="h-8 bg-transparent">
                <Download className="mr-1.5 h-3.5 w-3.5" />
                {t('accounts.export')}
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => setShowAdd(true)} className="h-8 bg-transparent">
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t('accounts.manualAdd')}
            </Button>
          </div>
        </div>
        
        {/* Search & Filter Toolbar */}
        <div className="flex items-center justify-between gap-4 px-5 py-2.5 bg-[var(--bg-pane)]/20">
          <div className="flex flex-1 items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-[var(--text-muted)]">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
              </div>
              <input
                type="text"
                placeholder={t('accounts.searchPlaceholder')}
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-transparent py-1.5 pl-8 pr-3 text-sm text-[var(--text-primary)] transition-colors placeholder:text-[var(--text-muted)] focus:border-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--text-primary)]"
              />
            </div>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="rounded-md border border-[var(--border)] bg-transparent py-1.5 pl-3 pr-8 text-sm text-[var(--text-primary)] transition-colors focus:border-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--text-primary)] appearance-none"
              style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`, backgroundPosition: 'right 8px center', backgroundRepeat: 'no-repeat' }}
            >
              <option value="">{t('accounts.allStatuses')}</option>
              <option value="registered">{translateAccountStatus('registered', language)}</option>
              <option value="trial">{t('dashboard.trial')}</option>
              <option value="subscribed">{t('dashboard.subscribed')}</option>
              <option value="free">{t('accounts.free')}</option>
              <option value="eligible">{t('accounts.eligible')}</option>
              <option value="expired">{t('accounts.expired')}</option>
              <option value="invalid">{t('dashboard.invalid')}</option>
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={batchRefreshing || loading}
              className="h-7 px-2.5 text-[var(--text-muted)] hover:text-amber-500 hover:bg-amber-500/10"
              title={t('accounts.refreshCreditsTitle')}
              onClick={async () => {
                setBatchRefreshing(true)
                try {
                  const res = await apiFetch(`/accounts/check-all?platform=${tab}`, { method: 'POST' })
                  if (res?.task_id) {
                    setBatchTask({ taskId: res.task_id, title: t('accounts.refreshAllCreditsTask', { platform: platformLabel }) })
                    setBatchTaskStatus(null)
                  }
                } catch (e) {
                  console.error(e)
                  setBatchRefreshing(false)
                }
              }}
            >
              <Zap className={`mr-1 h-3.5 w-3.5 ${batchRefreshing ? 'animate-pulse' : ''}`} />
              {batchRefreshing ? t('accounts.refreshingCredits') : t('accounts.refreshCredits')}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => load()} disabled={loading} className="h-7 w-7 p-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]">
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            {selectedCount > 0 && (
              <Button
                size="sm"
                variant="ghost"
                disabled={bulkDeleting}
                className="h-7 px-2.5 text-red-500 hover:bg-red-500/10 hover:text-red-600"
                onClick={async () => {
                  if (!confirm(t('accounts.deleteSelectedConfirm', { count: selectedCount }))) return
                  setBulkDeleting(true)
                  try {
                    await Promise.allSettled(
                      [...selectedIds].map(id => apiFetch(`/accounts/${id}`, { method: 'DELETE' }))
                    )
                    setSelectedIds(new Set())
                    load()
                  } finally {
                    setBulkDeleting(false)
                  }
                }}
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                {bulkDeleting ? t('common.deleting') : t('common.delete')}
              </Button>
            )}
          </div>
        </div>
      </Card>

      <Card className="min-h-0 flex-1 overflow-hidden p-0 border border-[var(--border)] shadow-sm">
        <div className="flex h-full min-h-0 flex-col">
          <div className="glass-table-wrap min-h-0 flex-1 overflow-auto">
        <table className="table-fixed w-full min-w-[900px] text-sm">
          <colgroup>
            <col className="w-10" />
            <col className="w-[30%]" />
            <col className="w-[12%]" />
            <col className="w-[26%]" />
            <col className="w-[8%]" />
            <col className="w-[12%]" />
            <col className="w-[12%]" />
          </colgroup>
          <thead className="sticky top-0 z-10  bg-[var(--bg-pane)]/80">
            <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wider font-medium text-[var(--text-muted)]">
              <th className="w-10 px-3 py-2 text-left">
                <input
                  type="checkbox"
                  checked={allSelectedOnPage}
                  onChange={togglePage}
                  className="checkbox-accent rounded-[3px] border-[var(--border)] focus:ring-[var(--text-primary)] focus:ring-offset-0 bg-transparent text-[var(--text-primary)]"
                />
              </th>
              <th className="px-3 py-2 text-left">{t('common.email')}</th>
              <th className="px-3 py-2 text-left">{t('common.password')}</th>
              <th className="px-3 py-2 text-left">{t('common.status')}</th>
              <th className="px-3 py-2 text-left">{t('accounts.link')}</th>
              <th className="px-3 py-2 text-left">{t('accounts.registeredAt')}</th>
              <th className="px-3 py-2 text-right">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-24 text-center">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--bg-pane)] border border-[var(--border)] shadow-sm">
                      <svg className="h-6 w-6 text-[var(--text-muted)]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>
                    </div>
                    <h3 className="text-sm font-medium text-[var(--text-primary)]">{t('accounts.emptyTitle')}</h3>
                    <p className="text-xs text-[var(--text-muted)] max-w-sm">{t('accounts.emptyDesc')}</p>
                  </div>
                </td>
              </tr>
            )}
            {accounts.map(acc => (
              (() => {
                const overview = getAccountOverview(acc)
                const verificationMailbox = getVerificationMailbox(acc)
                const primaryMetrics = getPrimaryMetrics(acc)
                const displayBadges = getDisplayBadges(acc)
                return (
              <tr key={acc.id} className="group border-b border-[var(--border)]/30 hover:bg-[var(--text-primary)]/[0.02] transition-colors cursor-pointer"
                  onClick={() => setDetail(acc)}>
                <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(acc.id)}
                    onChange={() => toggleOne(acc.id)}
                    className="checkbox-accent rounded-[3px] border-[var(--border)] focus:ring-[var(--text-primary)] focus:ring-offset-0 bg-transparent text-[var(--text-primary)] transition-all opacity-40 group-hover:opacity-100 data-[state=checked]:opacity-100"
                  />
                </td>
                <td className="px-3 py-2.5 font-mono text-sm text-[var(--text-primary)] align-top">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span className="truncate tracking-tight" title={acc.email}>{acc.email}</span>
                    <button onClick={e => { e.stopPropagation(); copy(acc.email) }} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] opacity-0 group-hover:opacity-100 transition-opacity"><Copy className="h-3 w-3" /></button>
                  </div>
                  {verificationMailbox && (verificationMailbox.email || verificationMailbox.account_id || verificationMailbox.provider) && (
                    <div
                      className="mt-1 truncate text-xs text-[var(--text-muted)] flex items-center gap-1"
                      title={`验证邮箱: ${verificationMailbox.email || '-'} · ${verificationMailbox.provider || '-'}`}
                    >
                      <svg className="w-3 h-3 opacity-60 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>
                      <span className="truncate">{verificationMailbox.email || '-'}</span>
                    </div>
                  )}
                  {overview?.remote_email && overview.remote_email !== acc.email && (
                    <div className="mt-1 truncate text-xs text-[var(--text-muted)]" title={`远端邮箱: ${overview.remote_email}`}>
                      远端邮箱: {overview.remote_email}
                    </div>
                  )}
                  {displayBadges.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {displayBadges.slice(0, 3).map((badge: any, index: number) => (
                        <span key={`${badge?.label || 'badge'}-${index}`} className="rounded border border-[var(--border)]/50 bg-[var(--bg-pane)]/40 px-1 py-0.5 text-[11px] font-medium text-[var(--text-muted)] shadow-sm">
                          {badge?.label}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5 font-mono text-[13px] text-[var(--text-muted)] align-top">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span className="truncate blur-[3px] transition-all cursor-default hover:blur-none select-none hover:select-auto hover:text-[var(--text-primary)]" title={acc.password}>{acc.password}</span>
                    <button onClick={e => { e.stopPropagation(); copy(acc.password) }} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] opacity-0 group-hover:opacity-100 transition-opacity"><Copy className="h-3 w-3" /></button>
                  </div>
                </td>
                <td className="px-3 py-2.5 align-top">
                  <div className="min-w-0 flex flex-col items-start gap-1.5">
                    {(() => {
                      const status = getDisplayStatus(acc);
                      const variant = String(STATUS_VARIANT[status] || 'secondary');
                      const styles = (({
                        success: "bg-emerald-500/10 text-emerald-500 ring-emerald-500/20",
                        warning: "bg-amber-500/10 text-amber-500 ring-amber-500/20",
                        danger: "bg-red-500/10 text-red-500 ring-red-500/20",
                        secondary: "bg-[var(--text-primary)]/5 text-[var(--text-secondary)] ring-[var(--border)]",
                        default: "bg-blue-500/10 text-blue-500 ring-blue-500/20"
                      } as Record<string, string>)[variant]) || "bg-[var(--text-primary)]/5 text-[var(--text-secondary)] ring-[var(--border)]";
                      
                      return (
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles}`}>
                          <span className={`mr-1 h-1 w-1 rounded-full ${variant === 'success' ? 'bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.6)]' : variant === 'warning' ? 'bg-amber-500 shadow-[0_0_4px_rgba(245,158,11,0.6)]' : variant === 'danger' ? 'bg-red-500 shadow-[0_0_4px_rgba(239,68,68,0.6)]' : variant === 'default' ? 'bg-blue-500' : 'bg-gray-400'}`}></span>
                          {translateAccountStatus(status, language)}
                        </span>
                      );
                    })()}
                    {primaryMetrics.length > 0 ? (
                      <div className="flex max-w-full flex-col gap-1">
                        {primaryMetrics.slice(0, 2).map((metric: any) => (
                          <div key={metric.key || metric.label} className="flex items-center gap-1.5">
                            <span className="h-1 w-1 rounded-full bg-[var(--text-muted)] opacity-50"></span>
                            <span className="text-xs tracking-tight text-[var(--text-muted)] whitespace-nowrap">
                              <span className="font-medium text-[var(--text-secondary)] mr-0.5">{metric.label}:</span>
                              {metric.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div
                        className="truncate text-xs text-[var(--text-muted)]"
                        title={getCompactStatusMeta(acc)}
                      >
                        {getCompactStatusMeta(acc)}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-3 py-2.5 align-top">
                  {getCashierUrl(acc) ? (
                    <div className="flex items-center gap-1.5 whitespace-nowrap opacity-70 group-hover:opacity-100 transition-opacity">
                      <button onClick={e => { e.stopPropagation(); copy(getCashierUrl(acc)) }} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors p-0.5 rounded hover:bg-[var(--bg-pane)]" title="复制链接"><Copy className="h-3 w-3" /></button>
                      <a href={getCashierUrl(acc)} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors p-0.5 rounded hover:bg-[var(--bg-pane)]" title="打开收银台"><ExternalLink className="h-3 w-3" /></a>
                    </div>
                  ) : <span className="text-[var(--text-muted)]/50 text-xs">-</span>}
                </td>
                <td className="px-3 py-2.5 font-mono text-xs text-[var(--text-muted)] whitespace-nowrap align-top">
                  {acc.created_at ? formatDateTime(acc.created_at, language, { 
                    month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit',
                    hour12: false 
                  }) : '-'}
                </td>
                <td className="px-3 py-2.5 align-top" onClick={e => e.stopPropagation()}>
                  <div className="flex items-center justify-end opacity-60 group-hover:opacity-100 transition-opacity">
                    <ActionMenu
                      acc={acc}
                      onDetail={() => setDetail(acc)}
                      onDelete={() => load()}
                      onResult={(title, payload) => setActionResult({ title, payload })}
                      onChanged={() => load()}
                    />
                  </div>
                </td>
              </tr>
                )
              })()
            ))}
          </tbody>
        </table>
          </div>
        </div>
      </Card>
    </div>
  )
}
