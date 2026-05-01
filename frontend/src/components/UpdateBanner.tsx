import { useEffect, useState } from 'react'
import { API } from '@/lib/utils'
import { Sparkles, X } from 'lucide-react'

const DISMISS_KEY = 'update-banner-dismissed-tag'

type VersionResp = {
  current: string
  latest: { tag: string; html_url: string; name: string } | null
  has_update: boolean
}

export default function UpdateBanner() {
  const [info, setInfo] = useState<VersionResp | null>(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const fetchVersion = async () => {
      try {
        const resp = await fetch(API + '/system/version')
        if (!resp.ok) return
        const data: VersionResp = await resp.json()
        if (cancelled) return
        const dismissedTag = localStorage.getItem(DISMISS_KEY) || ''
        if (data.has_update && data.latest && data.latest.tag === dismissedTag) {
          setDismissed(true)
        }
        setInfo(data)
      } catch {
        // 静默失败 — 离线/GitHub API 不通时不影响主功能
      }
    }
    fetchVersion()
    // 每小时复查一次
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
    <div className="mb-3 flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(127,178,255,0.18),rgba(141,227,255,0.10))] px-4 py-2.5 text-sm">
      <div className="flex items-center gap-2 min-w-0">
        <Sparkles className="h-4 w-4 text-[#7fb2ff] shrink-0" />
        <span className="text-[var(--text-primary)] truncate">
          有新版本 <b>v{info.latest.tag}</b> 可下载（当前 v{info.current === 'dev' ? 'dev' : info.current}）
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={open}
          className="rounded-lg bg-[#7fb2ff] px-3 py-1 text-xs font-medium text-white hover:opacity-90"
        >
          前往下载
        </button>
        <button
          onClick={handleDismiss}
          aria-label="忽略"
          className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
