import { useCallback, useEffect, useRef, useState } from 'react'
import { getConfig, getConfigOptions, getPlatforms } from '@/lib/app-data'
import type { ConfigOptionsResponse, ProviderOption, ProviderSetting } from '@/lib/config-options'
import { getCaptchaStrategyLabel, getProviderSelectOptions, listProviderFieldKeys } from '@/lib/config-options'
import { apiFetch } from '@/lib/utils'
import { useI18n } from '@/lib/i18n-context'
import { buildExecutorOptions, buildRegistrationOptions, hasReusableOAuthBrowser, pickOAuthExecutor } from '@/lib/registration'
import { TaskLogPanel } from '@/components/tasks/TaskLogPanel'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Play, CheckCircle, XCircle, Loader2, Orbit, Mail, ScanText, ShieldCheck, Workflow } from 'lucide-react'
import { getTaskStatusText, isTerminalTaskStatus, TASK_STATUS_VARIANTS } from '@/lib/tasks'

const DEFAULT_FORM: Record<string, any> = {
  platform: '',
  email: '',
  password: '',
  count: 1,
  proxy: '',
  executor_type: '',
  captcha_solver: 'auto',
  identity_provider: '',
  oauth_provider: '',
  oauth_email_hint: '',
  chrome_user_data_dir: '',
  chrome_cdp_url: '',
  mail_provider: '',
  sms_provider: '',
}

function getProviderSetting(settings: ProviderSetting[] = [], providerKey: string) {
  return settings.find(item => item.provider_key === providerKey) || null
}

function getProviderMergedValues(setting: ProviderSetting | null) {
  return {
    ...(setting?.config || {}),
    ...(setting?.auth || {}),
  }
}

function getDefaultProviderKey(settings: ProviderSetting[] = []) {
  return settings.find(item => item.is_default)?.provider_key || settings[0]?.provider_key || ''
}

export default function Register() {
  const { t, language } = useI18n()
  const [form, setForm] = useState<Record<string, any>>(DEFAULT_FORM)
  const [platforms, setPlatforms] = useState<any[]>([])
  const [configOptions, setConfigOptions] = useState<ConfigOptionsResponse>({
    mailbox_providers: [],
    captcha_providers: [],
    sms_providers: [],
    mailbox_settings: [],
    captcha_settings: [],
    sms_settings: [],
    captcha_policy: {},
    executor_options: [],
    identity_mode_options: [],
    oauth_provider_options: [],
  })
  const [optionsError, setOptionsError] = useState('')
  const [task, setTask] = useState<any>(null)
  const [polling, setPolling] = useState(false)
  const handledTerminalTaskIdsRef = useRef<Set<string>>(new Set())
  const openedCashierTaskIdsRef = useRef<Set<string>>(new Set())

  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  const applyTerminalTask = useCallback((latest: any, statusHint?: string) => {
    setTask(latest)
    const taskKey = String(latest?.task_id || latest?.id || task?.task_id || '')
    if (!taskKey) return
    handledTerminalTaskIdsRef.current.add(taskKey)
    const resolvedStatus = statusHint || latest?.status || ''
    if (
      resolvedStatus === 'succeeded'
      && latest?.cashier_urls
      && latest.cashier_urls.length > 0
      && !openedCashierTaskIdsRef.current.has(taskKey)
    ) {
      openedCashierTaskIdsRef.current.add(taskKey)
      latest.cashier_urls.forEach((url: string) => window.open(url, '_blank'))
    }
  }, [task?.task_id])

  useEffect(() => {
    Promise.all([
      getConfig().catch(() => ({})),
      getPlatforms().catch(() => []),
      getConfigOptions().catch(() => null),
    ]).then(([cfg, ps, options]) => {
      setPlatforms(ps || [])
      if (options) {
        setConfigOptions(options)
        setOptionsError('')
      } else {
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
        setOptionsError(t('register.providerMetadataError'))
      }
      setForm(f => {
        const nextForm: Record<string, any> = {
          ...f,
          executor_type: cfg.default_executor || f.executor_type,
          captcha_solver: 'auto',
          identity_provider: cfg.default_identity_provider || f.identity_provider,
          oauth_provider: cfg.default_oauth_provider || f.oauth_provider,
          oauth_email_hint: cfg.oauth_email_hint || f.oauth_email_hint,
          chrome_user_data_dir: cfg.chrome_user_data_dir || f.chrome_user_data_dir,
          chrome_cdp_url: cfg.chrome_cdp_url || f.chrome_cdp_url,
          mail_provider: getDefaultProviderKey((options?.mailbox_settings as ProviderSetting[]) || []) || f.mail_provider,
          sms_provider: getDefaultProviderKey((options?.sms_settings as ProviderSetting[]) || []) || f.sms_provider,
        }
        const providerFieldKeys = listProviderFieldKeys([
          ...((options?.mailbox_providers as ProviderOption[]) || []),
          ...((options?.captcha_providers as ProviderOption[]) || []),
          ...((options?.sms_providers as ProviderOption[]) || []),
        ])
        providerFieldKeys.forEach(fieldKey => {
          nextForm[fieldKey] = cfg[fieldKey] || f[fieldKey] || ''
        })
        return nextForm
      })
    })
  }, [])

  const currentPlatform = platforms.find((p: any) => p.name === form.platform) || null
  const platformOptions = platforms.map((p: any) => [p.name, p.display_name])
  const supportedExecutors = currentPlatform?.supported_executors || []
  const registrationOptions = buildRegistrationOptions(currentPlatform, language)
  const executorOptions = buildExecutorOptions(
    form.identity_provider,
    supportedExecutors,
    hasReusableOAuthBrowser(form),
    currentPlatform?.supported_executor_options || [],
    language,
  )
  const mailboxProviderOptions = getProviderSelectOptions(configOptions.mailbox_providers || [])
  const currentMailboxProvider = (configOptions.mailbox_providers || []).find(provider => provider.value === form.mail_provider) || null
  const currentMailboxSetting = getProviderSetting(configOptions.mailbox_settings || [], form.mail_provider)
  const smsProviderOptions = getProviderSelectOptions(configOptions.sms_providers || [])
  const currentSmsProvider = (configOptions.sms_providers || []).find(provider => provider.value === form.sms_provider) || null
  const currentSmsSetting = getProviderSetting(configOptions.sms_settings || [], form.sms_provider)
  const allProviderFieldKeys = listProviderFieldKeys([
    ...(configOptions.mailbox_providers || []),
    ...(configOptions.captcha_providers || []),
    ...(configOptions.sms_providers || []),
  ])

  useEffect(() => {
    const defaultProviderKey = getDefaultProviderKey(configOptions.mailbox_settings || [])
    if (form.identity_provider === 'mailbox' && !form.mail_provider && defaultProviderKey) {
      set('mail_provider', defaultProviderKey)
    }
  }, [form.identity_provider, form.mail_provider, configOptions.mailbox_settings])

  useEffect(() => {
    if (!currentMailboxProvider) return
    const values = getProviderMergedValues(currentMailboxSetting)
    const fields = currentMailboxProvider.fields || []
    if (fields.length === 0) return
    setForm(current => {
      const next = { ...current }
      let changed = false
      fields.forEach(field => {
        const nextValue = values[field.key] ?? current[field.key] ?? ''
        if ((next[field.key] ?? '') !== nextValue) {
          next[field.key] = nextValue
          changed = true
        }
      })
      return changed ? next : current
    })
  }, [form.mail_provider, currentMailboxProvider, currentMailboxSetting])

  useEffect(() => {
    const defaultProviderKey = getDefaultProviderKey(configOptions.sms_settings || [])
    if (!form.sms_provider && defaultProviderKey) {
      set('sms_provider', defaultProviderKey)
    }
  }, [form.sms_provider, configOptions.sms_settings])

  useEffect(() => {
    if (!currentSmsProvider) return
    const values = getProviderMergedValues(currentSmsSetting)
    const fields = currentSmsProvider.fields || []
    if (fields.length === 0) return
    setForm(current => {
      const next = { ...current }
      let changed = false
      fields.forEach(field => {
        const nextValue = values[field.key] ?? current[field.key] ?? ''
        if ((next[field.key] ?? '') !== nextValue) {
          next[field.key] = nextValue
          changed = true
        }
      })
      return changed ? next : current
    })
  }, [form.sms_provider, currentSmsProvider, currentSmsSetting])

  useEffect(() => {
    if (!platforms.some((p: any) => p.name === form.platform)) {
      const fallback = platforms[0]?.name || ''
      if (fallback !== form.platform) {
        set('platform', fallback)
      }
    }
  }, [form.platform, platforms])

  useEffect(() => {
    if (registrationOptions.length === 0) return
    const currentRegistration = registrationOptions.find(option =>
      option.identityProvider === form.identity_provider &&
      option.oauthProvider === form.oauth_provider,
    )
    if (!currentRegistration) {
      const preferred = registrationOptions.find(option =>
        option.identityProvider === form.identity_provider,
      ) || registrationOptions[0]
      set('identity_provider', preferred.identityProvider)
      set('oauth_provider', preferred.oauthProvider)
    }
  }, [registrationOptions, form.identity_provider, form.oauth_provider, form.platform])

  useEffect(() => {
    const validExecutors = executorOptions.filter(option => !option.disabled)
    if (validExecutors.length === 0) return
    if (!validExecutors.some(option => option.value === form.executor_type)) {
      const nextExecutor = form.identity_provider === 'oauth_browser'
        ? pickOAuthExecutor(supportedExecutors, form.executor_type, hasReusableOAuthBrowser(form))
        : ((supportedExecutors.includes(form.executor_type) && form.executor_type) ? form.executor_type : supportedExecutors[0] || '')
      set('executor_type', validExecutors.find(option => option.value === nextExecutor)?.value || validExecutors[0].value)
    }
  }, [executorOptions, supportedExecutors, form.executor_type, form.identity_provider, form.chrome_user_data_dir, form.chrome_cdp_url])

  const submit = async () => {
    const extra: Record<string, any> = {
      identity_provider: form.identity_provider,
      oauth_provider: form.oauth_provider,
      oauth_email_hint: form.oauth_email_hint,
      chrome_user_data_dir: form.chrome_user_data_dir || undefined,
      chrome_cdp_url: form.chrome_cdp_url || undefined,
    }
    if (form.mail_provider) {
      extra.mail_provider = form.mail_provider
    }
    if (form.sms_provider) {
      extra.sms_provider = form.sms_provider
    }
    allProviderFieldKeys.forEach(fieldKey => {
      if (form[fieldKey] !== undefined) {
        extra[fieldKey] = form[fieldKey]
      }
    })
    const res = await apiFetch('/tasks/register', {
      method: 'POST',
      body: JSON.stringify({
        platform: form.platform,
        email: form.email || null,
        password: form.password || null,
        count: form.count,
        proxy: form.proxy || null,
        executor_type: form.executor_type,
        captcha_solver: 'auto',
        extra,
      }),
    })
    setTask(res)
    setPolling(true)
  }

  const handleTaskDone = useCallback(async (status: string) => {
    if (!task?.task_id) return
    if (handledTerminalTaskIdsRef.current.has(String(task.task_id))) {
      setPolling(false)
      return
    }
    try {
      const latest = await apiFetch(`/tasks/${task.task_id}`)
      applyTerminalTask(latest, status)
    } finally {
      setPolling(false)
    }
  }, [applyTerminalTask, task?.task_id])

  useEffect(() => {
    if (!task?.task_id || isTerminalTaskStatus(task.status)) {
      if (task?.status) {
        setPolling(false)
      }
      return
    }
    const interval = window.setInterval(async () => {
      if (document.visibilityState !== 'visible') return
      try {
        const latest = await apiFetch(`/tasks/${task.task_id}`)
        setTask(latest)
        if (isTerminalTaskStatus(latest.status)) {
          window.clearInterval(interval)
          setPolling(false)
          applyTerminalTask(latest)
        }
      } catch {
        // passive
      }
    }, 5000)
    return () => window.clearInterval(interval)
  }, [applyTerminalTask, task?.task_id, task?.status])

  const Input = ({ label, k, type = 'text', placeholder = '' }: any) => (
    <div>
      <label className="block text-xs text-[var(--text-muted)] mb-1">{label}</label>
      <input
        type={type}
        value={(form as any)[k]}
        onChange={e => set(k, type === 'number' ? Number(e.target.value) : e.target.value)}
        placeholder={placeholder}
        className="control-surface"
      />
    </div>
  )

  const Select = ({ label, k, options }: any) => (
    <div>
      <label className="block text-xs text-[var(--text-muted)] mb-1">{label}</label>
      <select
        value={(form as any)[k]}
        onChange={e => set(k, e.target.value)}
        className="control-surface appearance-none"
      >
        {options.map(([v, l]: any) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  )

  const renderProviderField = (field: any) => (
    <Input
      key={field.key}
      label={field.label}
      k={field.key}
      type={field.secret ? 'password' : 'text'}
      placeholder={field.placeholder || ''}
    />
  )

  const summaryRegistration = registrationOptions.find(option => option.identityProvider === form.identity_provider && option.oauthProvider === form.oauth_provider)?.label || '-'
  const summaryExecutor = executorOptions.find(option => option.value === form.executor_type)?.label || '-'
  const summaryVerification = getCaptchaStrategyLabel(form.executor_type, configOptions.captcha_policy, configOptions.captcha_providers, language)
  const activeTaskStats = task ? [
    { label: t('common.status'), value: getTaskStatusText(task.status, language), icon: Orbit },
    { label: t('common.progress'), value: task.progress || '0/0', icon: Workflow },
    { label: t('common.success'), value: String(task.success ?? 0), icon: CheckCircle },
    { label: t('common.failure'), value: String(task.error_count ?? task.errors?.length ?? 0), icon: XCircle },
  ] : []

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_340px]">
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>{t('register.basicConfig')}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Select label={t('common.platform')} k="platform" options={platformOptions} />
              <div className="grid gap-4 md:grid-cols-2">
                <Input label={t('register.batchCount')} k="count" type="number" />
                <Input label={t('register.proxyOptional')} k="proxy" placeholder="http://user:pass@host:port" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t('register.stepIdentity')}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                {registrationOptions.map((option) => {
                  const active = form.identity_provider === option.identityProvider && form.oauth_provider === option.oauthProvider
                  return (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => {
                        set('identity_provider', option.identityProvider)
                        set('oauth_provider', option.oauthProvider)
                      }}
                      className={`rounded-lg border px-4 py-4 text-left transition-colors ${
                        active
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                          : 'border-[var(--border)] bg-[var(--bg-pane)]/45 hover:border-[var(--accent)]/60'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                        {option.identityProvider === 'mailbox' ? <Mail className="h-4 w-4 text-[var(--accent)]" /> : <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />}
                        {option.label}
                      </div>
                      <div className="mt-2 text-xs leading-5 text-[var(--text-muted)]">{option.description}</div>
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t('register.stepExecutor')}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-3">
                {executorOptions.map((option) => {
                  const active = form.executor_type === option.value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      disabled={option.disabled}
                      onClick={() => !option.disabled && set('executor_type', option.value)}
                      className={`rounded-lg border px-4 py-4 text-left transition-colors ${
                        option.disabled
                          ? 'cursor-not-allowed border-[var(--border)] bg-[var(--bg-hover)] opacity-50'
                          : active
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                            : 'border-[var(--border)] bg-[var(--bg-pane)]/45 hover:border-[var(--accent)]/60'
                      }`}
                    >
                      <div className="text-sm font-medium text-[var(--text-primary)]">{option.label}</div>
                      <div className="mt-2 text-xs leading-5 text-[var(--text-muted)]">{option.description}</div>
                      {option.reason ? (
                        <div className="mt-2 text-xs text-amber-400">{option.reason}</div>
                      ) : null}
                    </button>
                  )
                })}
              </div>
              {form.identity_provider === 'oauth_browser' && (
                <>
                  <Input label={t('register.oauthHintOptional')} k="oauth_email_hint" placeholder="your-account@example.com" />
                  <Input label={t('settings.chromeProfile')} k="chrome_user_data_dir" placeholder="~/Library/Application Support/Google/Chrome" />
                  <Input label={t('settings.chromeCdp')} k="chrome_cdp_url" placeholder="http://localhost:9222" />
                  <p className="text-xs text-[var(--text-muted)]">
                    {t('register.browserReuseHint')}
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {form.identity_provider === 'mailbox' && (
            <Card>
              <CardHeader><CardTitle>{t('register.mailboxConfig')}</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {optionsError && (
                  <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {optionsError}
                  </div>
                )}
                {mailboxProviderOptions.length > 0 ? (
                  <Select label={t('register.mailboxService')} k="mail_provider" options={mailboxProviderOptions} />
                ) : (
                  <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                    {t('register.noMailboxProvider')}
                  </div>
                )}
                {currentMailboxProvider?.description ? (
                  <p className="text-xs leading-5 text-[var(--text-muted)]">{currentMailboxProvider.description}</p>
                ) : null}
                {(currentMailboxProvider?.fields || []).map(renderProviderField)}
              </CardContent>
            </Card>
          )}

          {smsProviderOptions.length > 0 && (
            <Card>
              <CardHeader><CardTitle>{t('register.smsConfig')}</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {optionsError && (
                  <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {optionsError}
                  </div>
                )}
                <Select label={t('register.smsService')} k="sms_provider" options={smsProviderOptions} />
                {currentSmsProvider?.description ? (
                  <p className="text-xs leading-5 text-[var(--text-muted)]">{currentSmsProvider.description}</p>
                ) : null}
                {(currentSmsProvider?.fields || []).map(renderProviderField)}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-5 xl:sticky xl:top-4 xl:self-start">
          <Card className="bg-[var(--bg-pane)]/62">
            <CardHeader>
              <CardTitle>{t('register.summary')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]"><Mail className="h-3.5 w-3.5" /> Platform</div>
                  <div className="mt-2 text-base font-medium text-[var(--text-primary)]">{currentPlatform?.display_name || form.platform}</div>
                </div>
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]"><ShieldCheck className="h-3.5 w-3.5" /> Identity</div>
                  <div className="mt-2 text-base font-medium text-[var(--text-primary)]">{summaryRegistration}</div>
                </div>
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]"><Workflow className="h-3.5 w-3.5" /> Executor</div>
                  <div className="mt-2 text-base font-medium text-[var(--text-primary)]">{summaryExecutor}</div>
                </div>
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]"><ScanText className="h-3.5 w-3.5" /> Verification</div>
                  <div className="mt-2 text-base font-medium text-[var(--text-primary)]">{summaryVerification}</div>
                </div>
              </div>
              <Button onClick={submit} disabled={polling} className="w-full">
                {polling ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t('register.running')}</> : <><Play className="mr-2 h-4 w-4" />{t('register.start')}</>}
              </Button>
            </CardContent>
          </Card>

          {task ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {t('register.executionStatus')}
                    <Badge variant={TASK_STATUS_VARIANTS[task.status] || 'secondary'}>
                      {getTaskStatusText(task.status, language)}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
                    {activeTaskStats.map(({ label, value, icon: Icon }) => (
                      <div key={label} className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-3">
                        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                          <Icon className="h-3.5 w-3.5" />
                          {label}
                        </div>
                        <div className="mt-2 text-sm font-medium text-[var(--text-primary)]">{value}</div>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--chip-bg)] p-3 text-xs text-[var(--text-secondary)]">
                    <div>{t('taskHistory.taskId')}</div>
                    <div className="mt-1 break-all font-mono text-[var(--text-primary)]">{task.id}</div>
                  </div>
                  {task.errors?.length > 0 && (
                    <div className="space-y-1">
                      {task.errors.map((e: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-red-400">
                          <XCircle className="h-4 w-4" />
                          <span className="text-xs">{e}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {task.error && (
                    <div className="flex items-center gap-2 text-red-400">
                      <XCircle className="h-4 w-4" />
                      <span className="text-xs">{task.error}</span>
                    </div>
                  )}
                  {task.status === 'interrupted' && !task.error && (
                    <div className="flex items-center gap-2 text-amber-400">
                      <XCircle className="h-4 w-4" />
                      <span className="text-xs">{t('register.taskInterrupted')}</span>
                    </div>
                  )}
                  {task.status === 'cancelled' && !task.error && (
                    <div className="flex items-center gap-2 text-amber-400">
                      <XCircle className="h-4 w-4" />
                      <span className="text-xs">{t('register.taskCancelled')}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>{t('register.liveLogs')}</CardTitle></CardHeader>
                <CardContent>
                  <TaskLogPanel taskId={task.id} onDone={handleTaskDone} />
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="bg-[var(--bg-pane)]/55">
              <CardHeader><CardTitle>{t('register.waiting')}</CardTitle></CardHeader>
              <CardContent className="text-sm text-[var(--text-secondary)]">{t('register.waitingDesc')}</CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
