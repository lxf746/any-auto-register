import { BrowserRouter, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getPlatforms } from '@/lib/app-data'
import { getAuthToken, setAuthToken, API } from '@/lib/utils'
import Dashboard from '@/pages/Dashboard'
import Accounts from '@/pages/Accounts'
import Register from '@/pages/Register'
import Proxies from '@/pages/Proxies'
import Settings from '@/pages/Settings'
import TaskHistory from '@/pages/TaskHistory'
import UpdateBanner from '@/components/UpdateBanner'
import {
  ChevronDown,
  ChevronRight,
  Globe,
  History,
  LayoutDashboard,
  Moon,
  Settings as SettingsIcon,
  Sun,
  Users,
} from 'lucide-react'

type NavItem = {
  path: string
  label: string
  icon: any
  exact?: boolean
}

const PRIMARY_NAV: NavItem[] = [
  { path: '/', label: '总览', icon: LayoutDashboard, exact: true },
]

const SECONDARY_NAV: NavItem[] = [
  { path: '/history', label: '任务记录', icon: History },
  { path: '/proxies', label: '代理资源', icon: Globe },
  { path: '/settings', label: '配置中心', icon: SettingsIcon },
]

function appNavClass(isActive: boolean) {
  return [
    'group flex items-center gap-2.5 rounded-[16px] px-3 py-2 text-sm transition-all duration-150',
    isActive
      ? 'border border-[var(--accent-edge)] bg-[var(--bg-active)] text-[var(--text-primary)] shadow-[0_18px_34px_rgba(7,15,18,0.34)]'
      : 'border border-transparent text-[var(--text-secondary)] hover:border-[var(--border-soft)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
  ].join(' ')
}

function AccountsSubNav() {
  const location = useLocation()
  const isAccounts = location.pathname.startsWith('/accounts')
  const [open, setOpen] = useState(isAccounts)
  const [platforms, setPlatforms] = useState<{ key: string; label: string }[]>([])

  useEffect(() => {
    if (isAccounts) setOpen(true)
  }, [isAccounts])

  useEffect(() => {
    getPlatforms()
      .then((data) => setPlatforms((data || []).map((p: any) => ({ key: p.name, label: p.display_name }))))
      .catch(() => setPlatforms([]))
  }, [])

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className={`${appNavClass(isAccounts)} w-full justify-between text-left`}
      >
        <span className="flex items-center gap-3">
          <Users className={`h-4 w-4 ${isAccounts ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] group-hover:text-[var(--accent)]'}`} />
          <span>账号资产</span>
        </span>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && (
        <div className="ml-4 max-h-[42vh] space-y-1.5 overflow-y-auto border-l border-[var(--border-soft)] pl-4 pr-1">
          {platforms.map((platform) => (
            <NavLink
              key={platform.key}
              to={`/accounts/${platform.key}`}
              className={({ isActive }) => [
                'flex items-center gap-2 rounded-2xl px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] text-[var(--text-primary)]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
              ].join(' ')}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]/80" />
              <span>{platform.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

function Sidebar({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }) {
  const isLight = theme === 'light'

  return (
    <aside className="app-sidebar flex w-[15rem] min-h-0 shrink-0 flex-col">
      <div className="flex min-h-0 flex-1 flex-col rounded-[24px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.045),rgba(255,255,255,0.012))] p-3 shadow-[var(--shadow-hard)] backdrop-blur-xl">
        <div className="mb-3 flex items-center justify-between gap-3 rounded-[18px] border border-[var(--border-soft)] bg-[var(--hero-bg)] px-3 py-2.5">
          <div className="text-sm font-semibold text-[var(--text-primary)]">控制台</div>
          <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[var(--border-soft)] bg-[var(--chip-bg)] text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--text-primary)]"
          >
            {isLight ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
          <section>
            <div className="mb-2 px-2 text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">入口</div>
            <nav className="space-y-1.5">
              {PRIMARY_NAV.map(({ path, label, icon: Icon, exact }) => (
                <NavLink key={path} to={path} end={exact} className={({ isActive }) => appNavClass(isActive)}>
                  {({ isActive }) => (
                    <>
                      <Icon className={`h-4 w-4 ${isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] group-hover:text-[var(--accent)]'}`} />
                      <span>{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </section>

          <section>
            <div className="mb-2 px-2 text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">资产</div>
            <AccountsSubNav />
          </section>

          <section>
            <div className="mb-2 px-2 text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">系统</div>
            <nav className="space-y-1.5">
              {SECONDARY_NAV.map(({ path, label, icon: Icon }) => (
                <NavLink key={path} to={path} className={({ isActive }) => appNavClass(isActive)}>
                  {({ isActive }) => (
                    <>
                      <Icon className={`h-4 w-4 ${isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] group-hover:text-[var(--accent)]'}`} />
                      <span>{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </section>
        </div>
      </div>
    </aside>
  )
}

function Shell({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }) {
  return (
    <div className="app-shell min-h-screen p-2.5 lg:p-3">
      <div className="app-window flex h-[calc(100dvh-1.5rem)] min-h-[calc(100dvh-1.5rem)] gap-3 overflow-hidden p-2.5 lg:p-3">
        <Sidebar theme={theme} toggleTheme={toggleTheme} />
        <div className="flex min-w-0 min-h-0 flex-1 flex-col">
          <UpdateBanner />
          <main className="min-h-0 flex-1 overflow-y-auto rounded-[22px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.012))] p-3 shadow-[var(--shadow-hard)] backdrop-blur-xl lg:p-3.5">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/accounts/:platform" element={<Accounts />} />
              <Route path="/register" element={<Register />} />
              <Route path="/history" element={<TaskHistory />} />
              <Route path="/proxies" element={<Proxies />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  )
}

function LoginScreen({ onLogin }: { onLogin: (token: string) => void }) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch(API + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw }),
      })
      const data = await res.json()
      if (data.ok) {
        setAuthToken(data.token || '')
        onLogin(data.token || '')
      } else {
        setError(data.error || '密码错误')
      }
    } catch {
      setError('请求失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-base)]">
      <form onSubmit={submit} className="w-80 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-lg">
        <h1 className="mb-1 text-lg font-semibold text-[var(--text-primary)]">Account Manager</h1>
        <p className="mb-5 text-xs text-[var(--text-muted)]">请输入访问密码</p>
        <input
          type="password"
          value={pw}
          onChange={e => setPw(e.target.value)}
          placeholder="密码"
          autoFocus
          className="control-surface mb-3 w-full"
        />
        {error && <p className="mb-3 text-xs text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={loading || !pw}
          className="w-full rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? '验证中...' : '登 录'}
        </button>
      </form>
    </div>
  )
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  const [authState, setAuthState] = useState<'loading' | 'open' | 'locked' | 'authed'>('loading')

  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light')
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    fetch(API + '/auth/check')
      .then(r => r.json())
      .then(data => {
        if (!data.required) {
          setAuthState('open')
        } else if (getAuthToken()) {
          setAuthState('authed')
        } else {
          setAuthState('locked')
        }
      })
      .catch(() => setAuthState('open'))
  }, [])

  const toggleTheme = () => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))

  if (authState === 'loading') {
    return <div className="flex h-screen items-center justify-center bg-[var(--bg-base)] text-[var(--text-muted)] text-sm">加载中...</div>
  }

  if (authState === 'locked') {
    return <LoginScreen onLogin={() => setAuthState('authed')} />
  }

  return (
    <BrowserRouter>
      <Shell theme={theme} toggleTheme={toggleTheme} />
    </BrowserRouter>
  )
}
