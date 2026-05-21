import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '@/lib/utils'
import type { ProviderOption, ProviderSetting } from '@/lib/config-options'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Save, Eye, EyeOff, X, Pencil, Plus, Trash2, FlaskConical, Search } from 'lucide-react'
import { invalidateConfigOptionsCache } from '@/lib/app-data'
import { useI18n } from '@/lib/i18n-context'

const PROVIDER_CARDS_COPY = {
  en: {
    categories: {
      free: { label: 'Free / ready to use', desc: 'No self-hosted service required' },
      selfhost: { label: 'Self-hosted service required', desc: 'Deploy the backend service yourself' },
      thirdparty: { label: 'Third-party service', desc: 'Create an account on the provider platform to get credentials' },
      custom: { label: 'Custom', desc: 'Connect any API through the generic HTTP driver' },
    },
    selectPlaceholder: 'Please select...',
    searchPlaceholder: 'Search...',
    noMatch: 'No matching results',
    noConfig: 'This service does not require additional configuration.',
    enabled: 'Enabled',
    disabled: 'Disabled',
    loading: 'Loading...',
    requestFailed: 'Test request failed',
    saved: 'Saved ✓',
    saving: 'Saving...',
    save: 'Save',
    testing: 'Testing...',
    testConnection: 'Test connection',
    cancel: 'Cancel',
    testFailed: 'Test failed',
    defaultBadge: 'Default',
    edit: 'Edit',
    test: 'Test',
    testingShort: 'Testing',
    defaultDone: 'Default ✓',
    setDefault: 'Set default',
    delete: 'Delete',
    addCustomMailbox: 'Add custom mailbox service',
    addCustomCaptcha: 'Add custom captcha service',
    addCustomSms: 'Add custom SMS service',
    addCustomGeneric: 'Add custom service',
  },
  vi: {
    categories: {
      free: { label: 'Miễn phí / dùng ngay', desc: 'Không cần tự dựng dịch vụ' },
      selfhost: { label: 'Cần tự host dịch vụ', desc: 'Bạn cần tự triển khai dịch vụ backend' },
      thirdparty: { label: 'Dịch vụ bên thứ ba', desc: 'Cần đăng ký nền tảng bên thứ ba để lấy thông tin xác thực' },
      custom: { label: 'Tùy chỉnh', desc: 'Kết nối bất kỳ API nào qua driver HTTP chung' },
    },
    selectPlaceholder: 'Vui lòng chọn...',
    searchPlaceholder: 'Tìm kiếm...',
    noMatch: 'Không có kết quả phù hợp',
    noConfig: 'Dịch vụ này không cần cấu hình thêm.',
    enabled: 'Đã bật',
    disabled: 'Chưa bật',
    loading: 'Đang tải...',
    requestFailed: 'Yêu cầu kiểm tra thất bại',
    saved: 'Đã lưu ✓',
    saving: 'Đang lưu...',
    save: 'Lưu',
    testing: 'Đang kiểm tra...',
    testConnection: 'Kiểm tra kết nối',
    cancel: 'Hủy',
    testFailed: 'Kiểm tra thất bại',
    defaultBadge: 'Mặc định',
    edit: 'Sửa',
    test: 'Kiểm tra',
    testingShort: 'Đang kiểm tra',
    defaultDone: 'Mặc định ✓',
    setDefault: 'Đặt mặc định',
    delete: 'Xóa',
    addCustomMailbox: 'Thêm dịch vụ mailbox tùy chỉnh',
    addCustomCaptcha: 'Thêm dịch vụ captcha tùy chỉnh',
    addCustomSms: 'Thêm dịch vụ SMS tùy chỉnh',
    addCustomGeneric: 'Thêm dịch vụ tùy chỉnh',
  },
  zh: {
    categories: {
      free: { label: '免费 / 开箱即用', desc: '无需自建服务，直接使用' },
      selfhost: { label: '需要自建服务', desc: '需要自行部署后端服务' },
      thirdparty: { label: '第三方服务', desc: '需要注册第三方平台获取凭据' },
      custom: { label: '自定义', desc: '通过通用 HTTP 驱动对接任意 API' },
    },
    selectPlaceholder: '请选择...',
    searchPlaceholder: '搜索...',
    noMatch: '无匹配结果',
    noConfig: '此服务无需额外配置。',
    enabled: '已启用',
    disabled: '未启用',
    loading: '加载中...',
    requestFailed: '测试请求失败',
    saved: '已保存 ✓',
    saving: '保存中...',
    save: '保存',
    testing: '测试中...',
    testConnection: '测试连接',
    cancel: '取消',
    testFailed: '测试失败',
    defaultBadge: '默认',
    edit: '编辑',
    test: '测试',
    testingShort: '测试中',
    defaultDone: '默认 ✓',
    setDefault: '设默认',
    delete: '删除',
    addCustomMailbox: '添加自定义邮箱服务',
    addCustomCaptcha: '添加自定义验证服务',
    addCustomSms: '添加自定义接码服务',
    addCustomGeneric: '添加自定义服务',
  },
} as const

/* ------------------------------------------------------------------ */
/*  Toggle                                                             */
/* ------------------------------------------------------------------ */
function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
        disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
      } ${checked ? 'bg-[var(--accent)]' : 'bg-[var(--chip-bg)] border border-[var(--border)]'}`}
    >
      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-[18px]' : 'translate-x-[3px]'}`} />
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  Searchable Select                                                  */
/* ------------------------------------------------------------------ */
function SearchableSelect({ value, options, placeholder, onChange }: {
  value: string
  options: Array<{ value: string; label: string }>
  placeholder?: string
  onChange: (v: string) => void
}) {
  const { locale } = useI18n()
  const copy = PROVIDER_CARDS_COPY[locale]
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = search
    ? options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()) || o.value.includes(search))
    : options

  const selectedLabel = options.find(o => o.value === value)?.label || ''

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus()
  }, [open])

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => { setOpen(!open); setSearch('') }}
        className="control-surface w-full text-left flex items-center justify-between"
      >
        <span className={selectedLabel ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'}>
          {selectedLabel || placeholder || copy.selectPlaceholder}
        </span>
        <svg className="h-4 w-4 text-[var(--text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={open ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-pane)] shadow-lg">
          <div className="p-2 border-b border-[var(--border)]">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-muted)]" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder={copy.searchPlaceholder}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-base)] pl-8 pr-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
          </div>
          <div className="max-h-48 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-sm text-[var(--text-muted)]">{copy.noMatch}</div>
            ) : filtered.map(o => (
              <button
                key={o.value}
                type="button"
                onClick={() => { onChange(o.value); setOpen(false); setSearch('') }}
                className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--chip-bg)] ${
                  o.value === value ? 'bg-[var(--accent)]/10 text-[var(--accent)] font-medium' : 'text-[var(--text-primary)]'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Edit modal                                                         */
/* ------------------------------------------------------------------ */
function EditModal({
  provider, setting, providerType, onClose, onSaved,
}: {
  provider: ProviderOption; setting: ProviderSetting | null; providerType: string
  onClose: () => void; onSaved: () => void
}) {
  const { locale } = useI18n()
  const copy = PROVIDER_CARDS_COPY[locale]
  const fields = provider.fields || []
  const [form, setForm] = useState<Record<string, string>>(() => {
    const data: Record<string, string> = {}
    for (const field of fields) {
      data[field.key] = (setting?.auth?.[field.key] || '') || (setting?.config?.[field.key] || '')
    }
    return data
  })
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null)
  const [asyncOptions, setAsyncOptions] = useState<Record<string, Array<{ value: string; label: string }>>>({})
  const [asyncLoading, setAsyncLoading] = useState<Record<string, boolean>>({})

  // Load async-select field options.
  useEffect(() => {
    for (const field of fields) {
      if (field.type === 'async-select' && field.asyncUrl && !asyncOptions[field.key]) {
        setAsyncLoading(prev => ({ ...prev, [field.key]: true }))
        apiFetch(field.asyncUrl)
          .then((data: any) => {
            const valueKey = field.asyncValueKey || 'value'
            const labelKey = field.asyncLabelKey || 'label'
            // Support multiple response shapes.
            let items: any[] = []
            if (Array.isArray(data)) items = data
            else if (data?.countries) items = data.countries
            else if (data?.services) items = data.services
            else if (data?.data) items = Array.isArray(data.data) ? data.data : []

            const options = items.map((item: any) => {
              if (typeof item === 'object') {
                const v = String(item[valueKey] ?? item.id ?? item.country ?? '')
                const l = String(item[labelKey] ?? item.name ?? item.title ?? item.eng ?? v)
                return { value: v, label: l ? `${l} (${v})` : v }
              }
              return { value: String(item), label: String(item) }
            }).filter(o => o.value)
            setAsyncOptions(prev => ({ ...prev, [field.key]: options }))
          })
          .catch(() => setAsyncOptions(prev => ({ ...prev, [field.key]: [] })))
          .finally(() => setAsyncLoading(prev => ({ ...prev, [field.key]: false })))
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    const config: Record<string, string> = {}
    const auth: Record<string, string> = {}
    for (const field of fields) {
      if (field.category === 'auth') auth[field.key] = form[field.key] || ''
      else config[field.key] = form[field.key] || ''
    }
    setSaving(true)
    try {
      if (setting) {
        await apiFetch('/provider-settings', {
          method: 'PUT',
          body: JSON.stringify({
            id: setting.id, provider_type: providerType, provider_key: provider.value,
            display_name: setting.display_name || provider.label,
            auth_mode: setting.auth_mode || provider.default_auth_mode || '',
            enabled: true, is_default: setting.is_default, config, auth, metadata: {},
          }),
        })
      } else {
        await apiFetch('/provider-settings', {
          method: 'POST',
          body: JSON.stringify({
            provider_type: providerType, provider_key: provider.value,
            display_name: provider.label, auth_mode: provider.default_auth_mode || '',
            enabled: true, is_default: false, config, auth, metadata: {},
          }),
        })
      }
      invalidateConfigOptionsCache()
      setSaved(true)
      setTimeout(() => { onSaved(); onClose() }, 500)
    } catch (e) { console.error(e) } finally { setSaving(false) }
  }

  const handleTest = async () => {
    const config: Record<string, string> = {}
    const auth: Record<string, string> = {}
    for (const field of fields) {
      if (field.category === 'auth') auth[field.key] = form[field.key] || ''
      else config[field.key] = form[field.key] || ''
    }
    setTesting(true)
    setTestResult(null)
    try {
      const result = await apiFetch('/provider-settings/test', {
        method: 'POST',
        body: JSON.stringify({
          provider_type: providerType,
          provider_key: provider.value,
          config, auth,
        }),
      })
      setTestResult(result)
    } catch (e: any) {
      setTestResult({ ok: false, error: e.message || copy.requestFailed })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog-panel dialog-panel-sm flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">{provider.label}</h2>
            {provider.description && <p className="mt-0.5 text-xs text-[var(--text-muted)]">{provider.description}</p>}
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"><X className="h-4 w-4" /></button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {fields.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">{copy.noConfig}</p>
          ) : fields.map(field => {
            const sk = `${provider.value}:${field.key}`
            return (
              <div key={field.key}>
                <label className="mb-1.5 block text-sm font-medium text-[var(--text-secondary)]">{field.label}</label>
                {field.hint && <p className="mb-1.5 text-xs text-[var(--text-muted)]">{field.hint}</p>}
                <div className="relative">
                  {field.type === 'toggle' ? (
                    <div className="flex items-center gap-3">
                      <Toggle
                        checked={['true', '1', 'yes', 'on'].includes((form[field.key] || '').toLowerCase())}
                        onChange={v => setForm(f => ({ ...f, [field.key]: v ? 'true' : 'false' }))}
                      />
                      <span className="text-sm text-[var(--text-muted)]">
                        {['true', '1', 'yes', 'on'].includes((form[field.key] || '').toLowerCase()) ? copy.enabled : copy.disabled}
                      </span>
                    </div>
                  ) : field.type === 'async-select' ? (
                    asyncLoading[field.key] ? (
                      <div className="control-surface text-[var(--text-muted)] text-sm py-2">{copy.loading}</div>
                    ) : (
                      <SearchableSelect
                        value={form[field.key] || ''}
                        options={asyncOptions[field.key] || []}
                        placeholder={field.placeholder}
                        onChange={v => setForm(f => ({ ...f, [field.key]: v }))}
                      />
                    )
                  ) : field.type === 'select' && field.options?.length ? (
                    <select value={form[field.key] || ''} onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))} className="control-surface appearance-none">
                      {field.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  ) : field.type === 'textarea' ? (
                    <textarea
                      value={form[field.key] || ''}
                      onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                      placeholder={field.placeholder || ''}
                      className="control-surface min-h-32 font-mono text-xs"
                      autoComplete="off"
                      data-1p-ignore
                      data-lpignore="true"
                    />
                  ) : (
                    <>
                      <input type={field.secret && !showSecret[sk] ? 'password' : 'text'} value={form[field.key] || ''}
                        onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                        placeholder={field.placeholder || ''} className="control-surface pr-9" autoComplete="new-password"
                        data-1p-ignore data-lpignore="true" />
                      {field.secret && (
                        <button onClick={() => setShowSecret(s => ({ ...s, [sk]: !s[sk] }))}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-secondary)]">
                          {showSecret[sk] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        {/* Test result */}
        {testResult && (
          <div className={`mx-5 rounded-lg px-3 py-2 text-xs ${
            testResult.ok
              ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
              : 'border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400'
          }`}>
            {testResult.ok ? testResult.message : testResult.error}
          </div>
        )}

        {/* Footer */}
        <div className="flex gap-2 border-t border-[var(--border)] px-5 py-3">
          <Button onClick={handleSave} disabled={saving} className="flex-1">
            <Save className="h-3.5 w-3.5 mr-1.5" />
            {saved ? copy.saved : saving ? copy.saving : copy.save}
          </Button>
          <Button variant="outline" onClick={handleTest} disabled={testing || fields.length === 0} className="flex-1">
            <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
            {testing ? copy.testing : copy.testConnection}
          </Button>
          <Button variant="outline" onClick={onClose}>{copy.cancel}</Button>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main                                                               */
/* ------------------------------------------------------------------ */
type Props = {
  providerType: string
  catalog: ProviderOption[]
  settings: ProviderSetting[]
  onReload: () => Promise<void>
  onCreateCustom?: () => void
}

export default function ProviderCards({ providerType, catalog, settings, onReload, onCreateCustom }: Props) {
  const { locale } = useI18n()
  const copy = PROVIDER_CARDS_COPY[locale]
  const [editTarget, setEditTarget] = useState<{ provider: ProviderOption; setting: ProviderSetting | null } | null>(null)
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message?: string; error?: string }>>({})
  const [testingKeys, setTestingKeys] = useState<Record<string, boolean>>({})

  const settingsMap: Record<string, ProviderSetting> = {}
  for (const s of settings) settingsMap[s.provider_key] = s
  const defaultKey = settings.find(s => s.is_default)?.provider_key || ''

  const grouped: Record<string, ProviderOption[]> = {}
  for (const p of catalog) {
    const cat = p.category || 'custom'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(p)
  }

  const withLoading = async (key: string, fn: () => Promise<void>) => {
    setLoading(p => ({ ...p, [key]: true }))
    try { await fn() } finally { setLoading(p => ({ ...p, [key]: false })) }
  }

  const handleToggle = (provider: ProviderOption, enable: boolean) => withLoading(provider.value, async () => {
    const setting = settingsMap[provider.value]
    if (enable && !setting) {
      await apiFetch('/provider-settings', {
        method: 'POST',
        body: JSON.stringify({
          provider_type: providerType, provider_key: provider.value,
          display_name: provider.label, auth_mode: provider.default_auth_mode || '',
          enabled: true, is_default: settings.length === 0, config: {}, auth: {}, metadata: {},
        }),
      })
    } else if (!enable && setting) {
      await apiFetch(`/provider-settings/${setting.id}`, { method: 'DELETE' })
    }
    invalidateConfigOptionsCache()
    await onReload()
  })

  const handleSetDefault = (provider: ProviderOption) => withLoading(provider.value, async () => {
    const setting = settingsMap[provider.value]
    if (!setting) return
    await apiFetch('/provider-settings', {
      method: 'PUT',
      body: JSON.stringify({
        id: setting.id, provider_type: providerType, provider_key: provider.value,
        display_name: setting.display_name, auth_mode: setting.auth_mode,
        enabled: true, is_default: true, config: setting.config, auth: setting.auth, metadata: {},
      }),
    })
    invalidateConfigOptionsCache()
    await onReload()
  })

  const handleTestInline = async (provider: ProviderOption) => {
    const setting = settingsMap[provider.value]
    if (!setting) return
    const key = provider.value
    setTestingKeys(p => ({ ...p, [key]: true }))
    setTestResults(p => { const n = { ...p }; delete n[key]; return n })
    try {
      const result = await apiFetch('/provider-settings/test', {
        method: 'POST',
        body: JSON.stringify({
          provider_type: providerType,
          provider_key: key,
          config: setting.config || {},
          auth: setting.auth || {},
        }),
      })
      setTestResults(p => ({ ...p, [key]: result }))
    } catch (e: any) {
      setTestResults(p => ({ ...p, [key]: { ok: false, error: e.message || copy.testFailed } }))
    } finally {
      setTestingKeys(p => ({ ...p, [key]: false }))
    }
  }

  const handleDelete = (provider: ProviderOption) => withLoading(provider.value, async () => {
    const setting = settingsMap[provider.value]
    if (!setting) return
    // Delete the setting
    await apiFetch(`/provider-settings/${setting.id}`, { method: 'DELETE' })
    // Delete the definition (only works for non-builtin)
    const def = catalog.find(p => p.value === provider.value)
    if (def && !def.is_builtin && (def as any).id) {
      try {
        await apiFetch(`/provider-definitions/${(def as any).id}`, { method: 'DELETE' })
      } catch {
        // definition delete may fail if it's builtin, ignore
      }
    }
    invalidateConfigOptionsCache()
    await onReload()
  })

  const renderCard = (provider: ProviderOption, allowDelete = false) => {
    const key = provider.value
    const setting = settingsMap[key]
    const isEnabled = !!setting
    const isDefault = key === defaultKey
    const hasFields = (provider.fields || []).length > 0

    return (
      <div key={key}>
        <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
          {/* Left: name + desc + badge */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-[var(--text-primary)]">{provider.label}</span>
              {isDefault && <Badge variant="success">{copy.defaultBadge}</Badge>}
            </div>
            {provider.description && (
              <p className="mt-0.5 text-xs text-[var(--text-muted)] line-clamp-1">{provider.description}</p>
            )}
          </div>

          {/* Right: actions */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => hasFields && isEnabled ? setEditTarget({ provider, setting }) : undefined}
              disabled={!hasFields || !isEnabled}
              className={`table-action-btn ${(!hasFields || !isEnabled) ? 'opacity-30 cursor-not-allowed' : ''}`}
            >
              <Pencil className="h-3 w-3 mr-1" /> {copy.edit}
            </button>

            <button
              onClick={() => isEnabled ? handleTestInline(provider) : undefined}
              disabled={!isEnabled || testingKeys[key]}
              className={`table-action-btn ${!isEnabled ? 'opacity-30 cursor-not-allowed' : ''}`}
            >
              <FlaskConical className="h-3 w-3 mr-1" /> {testingKeys[key] ? copy.testingShort : copy.test}
            </button>

            <button
              onClick={() => isEnabled && !isDefault ? handleSetDefault(provider) : undefined}
              disabled={!isEnabled || isDefault || loading[key]}
              className={`table-action-btn ${(!isEnabled || isDefault) ? 'opacity-30 cursor-not-allowed' : ''}`}
            >
              {isDefault ? copy.defaultDone : copy.setDefault}
            </button>

            {allowDelete && (
              <button
                onClick={() => isEnabled ? handleDelete(provider) : undefined}
                disabled={!isEnabled || isDefault || loading[key]}
                className={`table-action-btn table-action-btn-danger ${(!isEnabled || isDefault) ? 'opacity-30 cursor-not-allowed' : ''}`}
              >
                <Trash2 className="h-3 w-3 mr-1" /> {copy.delete}
              </button>
            )}

            <Toggle
              checked={isEnabled}
              onChange={v => handleToggle(provider, v)}
              disabled={loading[key] || isDefault}
            />
          </div>
        </div>
        {/* Inline test result */}
        {testResults[key] && (
          <div className={`mt-1 rounded-lg px-3 py-2 text-xs ${
            testResults[key].ok
              ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
              : 'border border-red-500/20 bg-red-500/10 text-red-600'
          }`}>
            {testResults[key].ok ? testResults[key].message : testResults[key].error}
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      <div className="space-y-6">
        {Object.entries(copy.categories).map(([cat, meta]) => {
          const providers = grouped[cat]
          if (!providers || providers.length === 0) return null

          // Hide "通用 HTTP 邮箱" from the list — it's the engine behind custom providers
          const visible = cat === 'custom'
            ? providers.filter(p => p.value !== 'generic_http_mailbox')
            : providers

          return (
            <div key={cat}>
              <div className="mb-2">
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">{meta.label}</h3>
                <p className="text-xs text-[var(--text-muted)]">{meta.desc}</p>
              </div>
              <div className="space-y-1.5">
                {visible.map(p => renderCard(p, cat === 'custom'))}
                {cat === 'custom' && (
                  <button
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] px-4 py-3 text-sm text-[var(--text-muted)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
                    onClick={() => onCreateCustom?.()}
                  >
                    <Plus className="h-4 w-4" />
                    {providerType === 'mailbox'
                      ? copy.addCustomMailbox
                      : providerType === 'captcha'
                        ? copy.addCustomCaptcha
                        : providerType === 'sms'
                          ? copy.addCustomSms
                          : copy.addCustomGeneric}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {editTarget && (
        <EditModal
          provider={editTarget.provider}
          setting={editTarget.setting}
          providerType={providerType}
          onClose={() => setEditTarget(null)}
          onSaved={onReload}
        />
      )}
    </>
  )
}
