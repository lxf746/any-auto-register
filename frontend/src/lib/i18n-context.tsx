import { createContext, useContext, useEffect, useState } from 'react'

import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, detectLocale, formatLocaleDate, translate, type AppLocale } from '@/lib/i18n'

type I18nContextValue = {
  locale: AppLocale
  setLocale: (locale: AppLocale) => void
  t: (key: string, vars?: Record<string, string | number>) => string
  formatDate: (value: string | number | Date, options?: Intl.DateTimeFormatOptions) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<AppLocale>(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem(LOCALE_STORAGE_KEY) : null
    return detectLocale(saved || (typeof navigator !== 'undefined' ? navigator.language : DEFAULT_LOCALE))
  })

  useEffect(() => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale)
    document.documentElement.lang = locale
  }, [locale])

  const value: I18nContextValue = {
    locale,
    setLocale: setLocaleState,
    t: (key, vars) => translate(locale, key, vars),
    formatDate: (value, options) => formatLocaleDate(locale, value, options),
  }

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n must be used within I18nProvider')
  return context
}