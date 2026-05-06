import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/utils'
import { useI18n } from '@/lib/i18n-context'
import { Sparkles, X } from 'lucide-react'

const DISMISS_KEY = 'update-banner-dismissed-tag'

type VersionResp = {
  current: string
  latest: { tag: string; html_url: string; name: string } | null
  has_update: boolean
}

export default function UpdateBanner() {
  const { t } = useI18n()
  const [info, setInfo] = useState<VersionResp | null>(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const fetchVersion = async () => {
      try {
        const data: VersionResp = await apiFetch('/system/version')
        if (cancelled) return
        const dismissedTag = localStorage.getItem(DISMISS_KEY) || ''
        if (data.has_update && data.latest && data.latest.tag === dismissedTag) {
          setDismissed(true)
        }
        setInfo(data)
      } catch {
        // silent
      }
    }
    fetchVersion()
    const id = setInterval(fetchVersion, 60 * 60 * 1000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  if (!info || !info.has_update || !info.latest || dismissed) return null

  const handleDismiss = () => {
    if (info.latest) localStorage.setItem(DISMISS_KEY, info.latest.tag)
    setDismissed(true)
  }

  const open = () => {
    if (info.latest?.html_url) window.open(info.latest.html_url, '_blank')
  }

  return (
    <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-[var(--accent-edge)] bg-[var(--accent-soft)] px-4 py-2.5 text-sm">
      <div className="flex items-center gap-2 min-w-0">
        <Sparkles className="h-4 w-4 text-[var(--accent)] shrink-0" />
        <span className="text-[var(--text-primary)] truncate">
          {t('update.banner', { latest: info.latest.tag, current: info.current === 'dev' ? 'dev' : info.current })}
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={open}
          className="rounded-md bg-[var(--accent)] px-3 py-1 text-xs font-medium text-white hover:bg-[var(--accent-hover)]"
        >
          {t('update.download')}
        </button>
        <button
          onClick={handleDismiss}
          aria-label={t('update.dismiss')}
          className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
