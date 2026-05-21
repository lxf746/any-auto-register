import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { useI18n } from '@/lib/i18n-context'
import { Button } from '@/components/ui/button'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import { getPlatforms, invalidatePlatformsCache } from '@/lib/app-data'
import type { ChoiceOption } from '@/lib/config-options'
import { Save } from 'lucide-react'

const ADVANCED_COPY = {
  en: {
    checking: 'Checking',
    running: 'Running',
    stopped: 'Stopped',
    solverTitle: 'Turnstile solver',
    solverDesc: 'Status of the local Turnstile captcha solver service.',
    restartSolver: 'Restart solver',
    platformCapsTitle: 'Platform capabilities',
    platformCapsDesc: 'Customize supported executors, registration identities, and third-party entries for each platform.',
    resetDefault: 'Restore defaults',
    executors: 'Executors',
    identities: 'Registration identities',
    oauthEntries: 'Third-party entries',
    saved: 'Saved ✓',
    saving: 'Saving...',
    save: 'Save',
  },
  vi: {
    checking: 'Đang kiểm tra',
    running: 'Đang chạy',
    stopped: 'Chưa chạy',
    solverTitle: 'Bộ giải Turnstile',
    solverDesc: 'Trạng thái dịch vụ giải captcha Turnstile cục bộ.',
    restartSolver: 'Khởi động lại solver',
    platformCapsTitle: 'Năng lực nền tảng',
    platformCapsDesc: 'Tùy chỉnh các cách chạy, danh tính đăng ký và cổng bên thứ ba mà từng nền tảng hỗ trợ.',
    resetDefault: 'Khôi phục mặc định',
    executors: 'Cách chạy',
    identities: 'Danh tính đăng ký',
    oauthEntries: 'Cổng bên thứ ba',
    saved: 'Đã lưu ✓',
    saving: 'Đang lưu...',
    save: 'Lưu',
  },
  zh: {
    checking: '检测中',
    running: '运行中',
    stopped: '未运行',
    solverTitle: 'Turnstile 求解器',
    solverDesc: '本地 Turnstile 验证码求解服务状态。',
    restartSolver: '重启 Solver',
    platformCapsTitle: '平台能力',
    platformCapsDesc: '自定义各平台支持的执行方式、注册身份和第三方入口。',
    resetDefault: '恢复默认',
    executors: '执行方式',
    identities: '注册身份',
    oauthEntries: '第三方入口',
    saved: '已保存 ✓',
    saving: '保存中...',
    save: '保存',
  },
} as const

function SolverPanel() {
  const { locale } = useI18n()
  const copy = ADVANCED_COPY[locale]
  const [solverRunning, setSolverRunning] = useState<boolean | null>(null)

  const checkSolver = async () => {
    try {
      const d = await apiFetch('/solver/status')
      setSolverRunning(d.running)
    } catch {
      setSolverRunning(false)
    }
  }

  const restartSolver = async () => {
    await apiFetch('/solver/restart', { method: 'POST' })
    setSolverRunning(null)
    setTimeout(checkSolver, 4000)
  }

  useEffect(() => {
    checkSolver()
  }, [])

  const solverLabel = solverRunning === null ? copy.checking : solverRunning ? copy.running : copy.stopped

  return (
    <section>
      <h2 className="text-base font-semibold text-[var(--text-primary)]">{copy.solverTitle}</h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">{copy.solverDesc}</p>
      <div className="mt-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          {solverRunning === null ? (
            <RefreshCw className="h-4 w-4 animate-spin text-[var(--text-muted)]" />
          ) : solverRunning ? (
            <CheckCircle className="h-4 w-4 text-emerald-400" />
          ) : (
            <XCircle className="h-4 w-4 text-red-400" />
          )}
          <span
            className={cn(
              'text-sm font-medium',
              solverRunning ? 'text-emerald-400' : 'text-[var(--text-secondary)]'
            )}
          >
            {solverLabel}
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={restartSolver}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          {copy.restartSolver}
        </Button>
      </div>
    </section>
  )
}

function PlatformCapsPanel() {
  const { locale } = useI18n()
  const copy = ADVANCED_COPY[locale]
  const [platforms, setPlatforms] = useState<any[]>([])
  const [drafts, setDrafts] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})

  useEffect(() => {
    getPlatforms().then((list: any[]) => {
      setPlatforms(list)
      const init: Record<string, any> = {}
      list.forEach((p) => {
        init[p.name] = {
          supported_executors: [...p.supported_executors],
          supported_identity_modes: [...p.supported_identity_modes],
          supported_oauth_providers: [...p.supported_oauth_providers],
        }
      })
      setDrafts(init)
    })
  }, [])

  const toggle = (name: string, field: string, value: string) => {
    setDrafts((d) => {
      const arr: string[] = [...(d[name]?.[field] || [])]
      const idx = arr.indexOf(value)
      if (idx >= 0) arr.splice(idx, 1)
      else arr.push(value)
      return { ...d, [name]: { ...d[name], [field]: arr } }
    })
  }

  const save = async (name: string) => {
    setSaving((s) => ({ ...s, [name]: true }))
    try {
      await apiFetch(`/platforms/${name}/capabilities`, {
        method: 'PUT',
        body: JSON.stringify(drafts[name]),
      })
      invalidatePlatformsCache()
      setSaved((s) => ({ ...s, [name]: true }))
      setTimeout(() => setSaved((s) => ({ ...s, [name]: false })), 2000)
    } finally {
      setSaving((s) => ({ ...s, [name]: false }))
    }
  }

  const reset = async (name: string) => {
    await apiFetch(`/platforms/${name}/capabilities`, { method: 'DELETE' })
    invalidatePlatformsCache()
    const list = await getPlatforms({ force: true })
    const p = list.find((x: any) => x.name === name)
    if (p)
      setDrafts((d) => ({
        ...d,
        [name]: {
          supported_executors: [...p.supported_executors],
          supported_identity_modes: [...p.supported_identity_modes],
          supported_oauth_providers: [...p.supported_oauth_providers],
        },
      }))
  }

  return (
    <section>
      <h2 className="text-base font-semibold text-[var(--text-primary)]">{copy.platformCapsTitle}</h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        {copy.platformCapsDesc}
      </p>
      <div className="mt-4 space-y-4">
        {platforms.map((p) => {
          const draft = drafts[p.name] || {}
          const executors: string[] = draft.supported_executors || []
          const modes: string[] = draft.supported_identity_modes || []
          const oauths: string[] = draft.supported_oauth_providers || []
          const executorOptions: ChoiceOption[] = p.supported_executor_options || []
          const identityOptions: ChoiceOption[] = p.supported_identity_mode_options || []
          const oauthOptions: ChoiceOption[] = p.supported_oauth_provider_options || []
          return (
            <div
              key={p.name}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5"
            >
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    {p.display_name}
                  </h3>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                    {p.name} v{p.version}
                  </p>
                </div>
                <button onClick={() => reset(p.name)} className="table-action-btn">
                  {copy.resetDefault}
                </button>
              </div>
              <div className="space-y-3">
                <div>
                  <p className="mb-2 text-xs text-[var(--text-muted)]">{copy.executors}</p>
                  <div className="flex flex-wrap gap-4">
                    {executorOptions.map((option) => (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-1.5 text-xs text-[var(--text-secondary)]"
                      >
                        <input
                          type="checkbox"
                          checked={executors.includes(option.value)}
                          onChange={() => toggle(p.name, 'supported_executors', option.value)}
                          className="checkbox-accent"
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs text-[var(--text-muted)]">{copy.identities}</p>
                  <div className="flex gap-4">
                    {identityOptions.map((option) => (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-1.5 text-xs text-[var(--text-secondary)]"
                      >
                        <input
                          type="checkbox"
                          checked={modes.includes(option.value)}
                          onChange={() => toggle(p.name, 'supported_identity_modes', option.value)}
                          className="checkbox-accent"
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs text-[var(--text-muted)]">{copy.oauthEntries}</p>
                  <div className="flex flex-wrap gap-4">
                    {oauthOptions.map((option) => (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-1.5 text-xs text-[var(--text-secondary)]"
                      >
                        <input
                          type="checkbox"
                          checked={oauths.includes(option.value)}
                          onChange={() =>
                            toggle(p.name, 'supported_oauth_providers', option.value)
                          }
                          className="checkbox-accent"
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4">
                <Button size="sm" onClick={() => save(p.name)} disabled={saving[p.name]}>
                  <Save className="mr-1 h-3.5 w-3.5" />
                  {saved[p.name] ? copy.saved : saving[p.name] ? copy.saving : copy.save}
                </Button>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default function AdvancedSettings() {
  return (
    <div className="space-y-8">
      <SolverPanel />
      <div className="border-t border-[var(--border)]" />
      <PlatformCapsPanel />
    </div>
  )
}
