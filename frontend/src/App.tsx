import { BrowserRouter, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getPlatforms } from '@/lib/app-data'
import { getAuthToken, setAuthToken, API, cn } from '@/lib/utils'
import { I18nProvider, useI18n } from '@/lib/i18n-context'
import type { TranslationKey } from '@/lib/i18n'
import Dashboard from '@/pages/Dashboard'
import Accounts from '@/pages/Accounts'
import Register from '@/pages/Register'
import Proxies from '@/pages/Proxies'
import SettingsPage from '@/pages/SettingsPage'
import TaskHistory from '@/pages/TaskHistory'
import UpdateBanner from '@/components/UpdateBanner'
import {
  ChevronRight,
  History,
  LayoutDashboard,
  Moon,
  Settings as SettingsIcon,
  Sun,
  Monitor,
  Languages,
  Users,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  Sidebar                                                            */
/* ------------------------------------------------------------------ */

type NavItem = { path: string; labelKey: TranslationKey; icon: any; exact?: boolean }

const NAV_ITEMS: NavItem[] = [
  { path: '/', labelKey: 'nav.dashboard', icon: LayoutDashboard, exact: true },
  { path: '/history', labelKey: 'nav.tasks', icon: History },
]

function Sidebar({
  theme,
  toggleTheme,
  collapsed,
  setCollapsed,
}: {
  theme: string
  toggleTheme: () => void
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}) {
  const { t, toggleLanguage } = useI18n()
  const location = useLocation()
  const navigate = useNavigate()
  const [platforms, setPlatforms] = useState<{ key: string; label: string }[]>([])
  const [accountsOpen, setAccountsOpen] = useState(location.pathname.startsWith('/accounts'))

  useEffect(() => {
    getPlatforms()
      .then((data) => setPlatforms((data || []).map((p: any) => ({ key: p.name, label: p.display_name }))))
      .catch(() => setPlatforms([]))
  }, [])

  useEffect(() => {
    if (location.pathname.startsWith('/accounts')) setAccountsOpen(true)
  }, [location.pathname])

  const isAccounts = location.pathname.startsWith('/accounts')
  const isSettings = location.pathname === '/settings'

  const navLinkClass = (active: boolean) =>
    cn(
      'group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors',
      active
        ? 'bg-[var(--accent-soft)] text-[var(--text-primary)]'
        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
      collapsed && 'justify-center px-0'
    )

  const iconClass = (active: boolean) =>
    cn('h-[18px] w-[18px] shrink-0', active ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] group-hover:text-[var(--text-secondary)]')

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-[220px]'
      )}
    >
      {/* Header */}
      <div className={cn('flex h-12 shrink-0 items-center border-b border-[var(--border)] px-3', collapsed && 'justify-center')}>
        {!collapsed && (
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[11px] font-bold text-white">
              A
            </div>
            <span className="truncate text-sm font-semibold text-[var(--text-primary)]">Auto Register</span>
          </div>
        )}
        {collapsed && (
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent)] text-[11px] font-bold text-white">
            A
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map(({ path, labelKey, icon: Icon, exact }) => {
          const active = exact ? location.pathname === path : location.pathname.startsWith(path)
          const label = t(labelKey)
          return (
            <NavLink key={path} to={path} end={exact} className={navLinkClass(active)} title={collapsed ? label : undefined}>
              <Icon className={iconClass(active)} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          )
        })}

        {/* Accounts with sub-items */}
        <div>
          <button
            onClick={() => {
              if (collapsed) {
                navigate('/accounts')
              } else {
                setAccountsOpen(!accountsOpen)
              }
            }}
            className={cn(navLinkClass(isAccounts), 'w-full')}
            title={collapsed ? t('nav.accounts') : undefined}
          >
            <Users className={iconClass(isAccounts)} />
            {!collapsed && (
              <>
                <span className="flex-1 text-left">{t('nav.accounts')}</span>
                <ChevronRight className={cn('h-3 w-3 text-[var(--text-muted)] transition-transform duration-150', accountsOpen && 'rotate-90')} />
              </>
            )}
          </button>
          {!collapsed && accountsOpen && (
            <div className="ml-[21px] mt-0.5 space-y-px border-l border-[var(--border)] pl-3">
              {platforms.map((p) => (
                <NavLink
                  key={p.key}
                  to={`/accounts/${p.key}`}
                  className={({ isActive }) =>
                    cn(
                      'block rounded-md px-2.5 py-1.5 text-[13px] transition-colors',
                      isActive
                        ? 'text-[var(--text-primary)] font-medium bg-[var(--bg-hover)]'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                    )
                  }
                >
                  {p.label}
                </NavLink>
              ))}
            </div>
          )}
        </div>

        {/* Divider */}
        {!collapsed && <div className="!my-2 mx-1 border-t border-[var(--border)]" />}

        {/* Settings with sub-items */}
        <div>
          <button
            onClick={() => {
              if (collapsed) {
                navigate('/settings')
              } else {
                navigate('/settings')
              }
            }}
            className={cn(navLinkClass(isSettings), 'w-full')}
            title={collapsed ? t('nav.settings') : undefined}
          >
            <SettingsIcon className={iconClass(isSettings)} />
            {!collapsed && <span>{t('nav.settings')}</span>}
          </button>
          {!collapsed && isSettings && (
            <div className="ml-[21px] mt-0.5 space-y-px border-l border-[var(--border)] pl-3">
              {[
                { label: t('nav.settings.general'), hash: 'general' },
                { label: t('nav.settings.register'), hash: 'register' },
                { label: t('nav.settings.mailbox'), hash: 'mailbox' },
                { label: t('nav.settings.captcha'), hash: 'captcha' },
                { label: t('nav.settings.sms'), hash: 'sms' },
                { label: t('nav.settings.proxies'), hash: 'proxies' },
                { label: t('nav.settings.chatgpt'), hash: 'chatgpt' },
                { label: t('nav.settings.advanced'), hash: 'advanced' },
                { label: t('nav.settings.about'), hash: 'about' },
              ].map((item) => {
                const params = new URLSearchParams(location.search)
                const currentTab = params.get('tab') || 'general'
                const active = currentTab === item.hash
                return (
                  <NavLink
                    key={item.hash}
                    to={`/settings?tab=${item.hash}`}
                    className={cn(
                      'relative block rounded-md px-2.5 py-1.5 text-[13px] transition-colors',
                      active
                        ? 'text-[var(--accent)] font-medium bg-[var(--accent-soft)]'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                    )}
                  >
                    {active && <span className="absolute -left-[13.5px] top-1/2 -translate-y-1/2 h-4 w-[2px] rounded-full bg-[var(--accent)]" />}
                    {item.label}
                  </NavLink>
                )
              })}
            </div>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="shrink-0 border-t border-[var(--border)] px-2 py-1.5 flex items-center gap-1">
        <button
          onClick={toggleTheme}
          className={cn(
            'flex items-center justify-center rounded-md p-2 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]',
          )}
          title={theme === 'light' ? t('sidebar.theme.toDark') : theme === 'dark' ? t('sidebar.theme.toLight') : t('sidebar.theme.followSystem')}
        >
          {theme === 'light' ? <Moon className="h-4 w-4" /> : theme === 'system' ? <Monitor className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </button>
        {!collapsed && (
          <span className="flex-1 text-[12px] text-[var(--text-muted)]">
            {theme === 'light' ? t('sidebar.theme.light') : theme === 'dark' ? t('sidebar.theme.dark') : t('sidebar.theme.system')}
          </span>
        )}
        <button
          onClick={toggleLanguage}
          className="flex items-center justify-center rounded-md p-2 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          title={t('sidebar.languageToggle')}
        >
          <Languages className="h-4 w-4" />
        </button>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center rounded-md p-2 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          title={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>
    </aside>
  )
}

/* ------------------------------------------------------------------ */
/*  Shell                                                              */
/* ------------------------------------------------------------------ */

function Shell({
  theme,
  setTheme,
  toggleTheme,
}: {
  theme: string
  setTheme: (t: string) => void
  toggleTheme: () => void
}) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar-collapsed') === 'true')

  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', String(collapsed))
  }, [collapsed])

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
      <Sidebar theme={theme} toggleTheme={toggleTheme} collapsed={collapsed} setCollapsed={setCollapsed} />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-6 lg:px-8">
          <UpdateBanner />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/accounts/:platform" element={<Accounts />} />
            <Route path="/register" element={<Register />} />
            <Route path="/history" element={<TaskHistory />} />
            <Route path="/proxies" element={<Proxies />} />
            <Route path="/settings" element={<SettingsPage theme={theme} setTheme={setTheme} />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Login                                                              */
/* ------------------------------------------------------------------ */

function LoginScreen({ onLogin }: { onLogin: (token: string) => void }) {
  const { t } = useI18n()
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
        setError(data.error || t('login.passwordError'))
      }
    } catch {
      setError(t('login.requestFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-base)]">
      <form onSubmit={submit} className="w-80 space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-sm font-bold text-white">A</div>
          <h1 className="text-base font-semibold text-[var(--text-primary)]">Any Auto Register</h1>
        </div>
        <p className="text-sm text-[var(--text-muted)]">{t('login.prompt')}</p>
        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder={t('login.passwordPlaceholder')}
          autoFocus
          className="control-surface w-full"
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading || !pw}
          className="w-full rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          {loading ? t('login.checking') : t('login.submit')}
        </button>
      </form>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  App root                                                           */
/* ------------------------------------------------------------------ */

function AppContent() {
  const { t } = useI18n()
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  const [authState, setAuthState] = useState<'loading' | 'open' | 'locked' | 'authed'>('loading')

  useEffect(() => {
    const applyTheme = () => {
      let effective = theme
      if (theme === 'system') {
        effective = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
      }
      document.documentElement.classList.toggle('light', effective === 'light')
    }
    applyTheme()
    localStorage.setItem('theme', theme)
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const handler = () => { if (theme === 'system') applyTheme() }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  useEffect(() => {
    fetch(API + '/auth/check')
      .then((r) => r.json())
      .then((data) => {
        if (!data.required) setAuthState('open')
        else if (getAuthToken()) setAuthState('authed')
        else setAuthState('locked')
      })
      .catch(() => setAuthState('open'))
  }, [])

  const toggleTheme = () =>
    setTheme((c) => (c === 'dark' ? 'light' : c === 'light' ? 'system' : 'dark'))

  if (authState === 'loading') {
    return <div className="flex h-screen items-center justify-center bg-[var(--bg-base)] text-[var(--text-muted)] text-sm">{t('app.loading')}</div>
  }
  if (authState === 'locked') {
    return <LoginScreen onLogin={() => setAuthState('authed')} />
  }

  return (
    <BrowserRouter>
      <Shell theme={theme} setTheme={setTheme} toggleTheme={toggleTheme} />
    </BrowserRouter>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <AppContent />
    </I18nProvider>
  )
}
