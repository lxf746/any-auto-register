import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Sun, Moon, Monitor } from 'lucide-react'
import { cn, apiFetch } from '@/lib/utils'
import { getConfig, getConfigOptions, invalidateConfigCache } from '@/lib/app-data'
import type { ConfigOptionsResponse } from '@/lib/config-options'
import { Button } from '@/components/ui/button'
import { Save, RefreshCw, CheckCircle, ExternalLink, Sparkles } from 'lucide-react'
import Settings from '@/pages/Settings'
import Proxies from '@/pages/Proxies'
import AdvancedSettings from '@/components/settings/AdvancedSettings'
import { API } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Tab definitions                                                    */
/* ------------------------------------------------------------------ */
/*  Reusable setting group card                                        */
/* ------------------------------------------------------------------ */
function SettingGroup({
  title,
  desc,
  children,
}: {
  title: string
  desc?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-[15px] font-semibold text-[var(--text-primary)]">{title}</h3>
        {desc && <p className="mt-0.5 text-[13px] text-[var(--text-muted)]">{desc}</p>}
      </div>
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Theme selector                                                     */
/* ------------------------------------------------------------------ */
const THEME_OPTIONS = [
  { value: 'light', label: '浅色', icon: Sun },
  { value: 'dark', label: '深色', icon: Moon },
  { value: 'system', label: '跟随系统', icon: Monitor },
] as const

function ThemeSelector({ theme, setTheme }: { theme: string; setTheme: (t: string) => void }) {
  return (
    <div className="inline-flex rounded-xl border border-[var(--border)] bg-[var(--chip-bg)] p-1">
      {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={cn(
            'inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-all',
            theme === value
              ? 'bg-[var(--accent)] text-white shadow-sm'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          )}
        >
          <Icon className="h-4 w-4" />
          {label}
        </button>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  General tab — theme + default register strategy + browser reuse    */
/* ------------------------------------------------------------------ */
function GeneralTab({
  theme,
  setTheme,
}: {
  theme: string
  setTheme: (t: string) => void
}) {
  const [form, setForm] = useState<Record<string, string>>({})
  const [configOptions, setConfigOptions] = useState<ConfigOptionsResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    Promise.all([getConfig().catch(() => ({})), getConfigOptions().catch(() => null)]).then(
      ([cfg, opts]) => {
        setForm(cfg)
        if (opts) setConfigOptions(opts)
      }
    )
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await apiFetch('/config', { method: 'PUT', body: JSON.stringify({ data: form }) })
      invalidateConfigCache()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const executorOptions = configOptions?.executor_options || []
  const identityOptions = configOptions?.identity_mode_options || []
  const oauthOptions = [
    { label: '不预选，由当前页面选择', value: '' },
    ...((configOptions?.oauth_provider_options || []).filter((o) => o.value !== '')),
  ]

  return (
    <div className="space-y-8">
      <SettingGroup title="外观主题" desc="选择应用的外观主题，立即生效。">
        <ThemeSelector theme={theme} setTheme={setTheme} />
      </SettingGroup>

      <div className="border-t border-[var(--border)]" />

      <SettingGroup
        title="默认注册策略"
        desc="这里配置的是默认行为，账号列表和注册页会直接复用这些设置。"
      >
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] divide-y divide-[var(--border)]/50">
          <SettingRow label="默认注册身份">
            <select
              value={form.default_identity_provider || identityOptions[0]?.value || ''}
              onChange={(e) => setForm((f) => ({ ...f, default_identity_provider: e.target.value }))}
              className="control-surface appearance-none"
            >
              {identityOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </SettingRow>
          <SettingRow label="默认第三方入口">
            <select
              value={form.default_oauth_provider || ''}
              onChange={(e) => setForm((f) => ({ ...f, default_oauth_provider: e.target.value }))}
              className="control-surface appearance-none"
            >
              {oauthOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </SettingRow>
          <SettingRow label="默认执行方式">
            <select
              value={form.default_executor || executorOptions[0]?.value || ''}
              onChange={(e) => setForm((f) => ({ ...f, default_executor: e.target.value }))}
              className="control-surface appearance-none"
            >
              {executorOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </SettingRow>
        </div>
      </SettingGroup>

      <div className="border-t border-[var(--border)]" />

      <SettingGroup
        title="浏览器复用"
        desc="第三方账号走后台浏览器自动时，通常需要复用本机已登录浏览器。"
      >
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] divide-y divide-[var(--border)]/50">
          <SettingRow label="预期登录邮箱">
            <input
              type="text"
              value={form.oauth_email_hint || ''}
              onChange={(e) => setForm((f) => ({ ...f, oauth_email_hint: e.target.value }))}
              placeholder="your-account@example.com"
              className="control-surface"
            />
          </SettingRow>
          <SettingRow label="Chrome Profile 路径">
            <input
              type="text"
              value={form.chrome_user_data_dir || ''}
              onChange={(e) => setForm((f) => ({ ...f, chrome_user_data_dir: e.target.value }))}
              placeholder="~/Library/Application Support/Google/Chrome"
              className="control-surface"
            />
          </SettingRow>
          <SettingRow label="Chrome CDP 地址">
            <input
              type="text"
              value={form.chrome_cdp_url || ''}
              onChange={(e) => setForm((f) => ({ ...f, chrome_cdp_url: e.target.value }))}
              placeholder="http://localhost:9222"
              className="control-surface"
            />
          </SettingRow>
        </div>
      </SettingGroup>

      <Button onClick={save} disabled={saving} className="w-full">
        <Save className="mr-2 h-4 w-4" />
        {saved ? '已保存 ✓' : saving ? '保存中...' : '保存设置'}
      </Button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Setting row — label + control                                      */
/* ------------------------------------------------------------------ */
function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3.5">
      <label className="shrink-0 text-sm font-medium text-[var(--text-secondary)]">{label}</label>
      <div className="min-w-0 max-w-[320px] flex-1">{children}</div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  About tab                                                          */
/* ------------------------------------------------------------------ */
type VersionResp = {
  current: string
  latest: {
    tag: string
    html_url: string
    name: string
    body: string
    published_at: string
  } | null
  has_update: boolean
}

function AboutTab() {
  const [info, setInfo] = useState<VersionResp | null>(null)
  const [checking, setChecking] = useState(false)

  const fetchVersion = async () => {
    setChecking(true)
    try {
      const resp = await fetch(API + '/system/version')
      if (resp.ok) {
        setInfo(await resp.json())
      } else {
        setInfo({ current: '?', latest: null, has_update: false })
      }
    } catch {
      setInfo({ current: '?', latest: null, has_update: false })
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    fetchVersion()
  }, [])

  return (
    <div className="space-y-8">
      <SettingGroup title="版本信息" desc="当前应用版本与更新检测。">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] divide-y divide-[var(--border)]/50">
          <div className="flex items-center justify-between px-4 py-4">
            <div>
              <div className="text-sm text-[var(--text-muted)]">当前版本</div>
              <div className="mt-0.5 text-xl font-bold tracking-tight text-[var(--text-primary)]">
                {info ? `v${info.current}` : checking ? '加载中...' : '—'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {info && !info.has_update && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-400">
                  <CheckCircle className="h-3.5 w-3.5" />
                  已是最新
                </span>
              )}
              <Button variant="outline" size="sm" onClick={fetchVersion} disabled={checking}>
                <RefreshCw className={cn('mr-1.5 h-3.5 w-3.5', checking && 'animate-spin')} />
                检查更新
              </Button>
            </div>
          </div>

          {info?.has_update && info.latest && (
            <div className="space-y-3 px-4 py-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[var(--accent)]" />
                <span className="text-sm font-semibold text-[var(--text-primary)]">
                  新版本 v{info.latest.tag} 可用
                </span>
              </div>
              {info.latest.name && (
                <div className="text-sm text-[var(--text-secondary)]">{info.latest.name}</div>
              )}
              {info.latest.body && (
                <div className="max-h-40 overflow-y-auto rounded-xl bg-[var(--bg-input)] p-3 text-xs leading-relaxed text-[var(--text-secondary)] whitespace-pre-wrap">
                  {info.latest.body}
                </div>
              )}
              {info.latest.published_at && (
                <div className="text-xs text-[var(--text-muted)]">
                  发布于 {new Date(info.latest.published_at).toLocaleDateString('zh-CN')}
                </div>
              )}
              <Button
                size="sm"
                onClick={() => info.latest?.html_url && window.open(info.latest.html_url, '_blank')}
              >
                <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                前往下载
              </Button>
            </div>
          )}
        </div>
      </SettingGroup>

      <div className="border-t border-[var(--border)]" />

      <SettingGroup title="项目信息">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] divide-y divide-[var(--border)]/50">
          <InfoRow label="项目名称" value="Any Auto Register" />
          <InfoRow label="技术栈" value="FastAPI + React + Electron" />
          <InfoRow label="开源协议" value="AGPL-3.0" />
          <InfoRow
            label="GitHub"
            value={
              <a
                href="https://github.com/lxf746/any-auto-register"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[var(--accent)] hover:underline"
              >
                github.com/lxf746/any-auto-register
                <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M6 3.5h6.5V10M12 4L4 12" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </a>
            }
          />
        </div>
      </SettingGroup>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-sm text-[var(--text-muted)]">{label}</span>
      <span className="text-sm font-medium text-[var(--text-primary)]">{value}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main settings page                                                 */
/* ------------------------------------------------------------------ */
export default function SettingsPage({
  theme,
  setTheme,
}: {
  theme: string
  setTheme: (t: string) => void
}) {
  const [searchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'general'

  // Config center sub-tabs: register, mailbox, captcha, sms, chatgpt
  const configTabs = ['register', 'mailbox', 'captcha', 'sms', 'chatgpt']
  const isConfigTab = configTabs.includes(tab)

  // Page title mapping
  const titles: Record<string, string> = {
    general: '通用设置',
    register: '注册策略',
    mailbox: '邮箱服务',
    captcha: '验证服务',
    sms: '接码服务',
    proxies: '代理资源',
    chatgpt: 'ChatGPT',
    advanced: '高级设置',
    about: '关于',
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 text-xl font-semibold text-[var(--text-primary)]">
        {titles[tab] || '设置'}
      </h1>

      {tab === 'general' && <GeneralTab theme={theme} setTheme={setTheme} />}
      {isConfigTab && <Settings embedded defaultTab={tab} />}
      {tab === 'proxies' && <Proxies />}
      {tab === 'advanced' && <AdvancedSettings />}
      {tab === 'about' && <AboutTab />}
    </div>
  )
}
