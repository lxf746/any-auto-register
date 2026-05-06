import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import {
  DEFAULT_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  getStoredLanguage,
  normalizeLanguage,
  translate,
  type Language,
  type TranslationKey,
} from '@/lib/i18n'

type I18nContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  toggleLanguage: () => void
  t: (key: TranslationKey, params?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => getStoredLanguage())

  const setLanguage = useCallback((nextLanguage: Language) => {
    setLanguageState(normalizeLanguage(nextLanguage))
  }, [])

  const toggleLanguage = useCallback(() => {
    setLanguageState(current => current === 'zh-CN' ? 'en-US' : 'zh-CN')
  }, [])

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    document.documentElement.lang = language
  }, [language])

  const value = useMemo<I18nContextValue>(() => ({
    language,
    setLanguage,
    toggleLanguage,
    t: (key, params) => translate(key, language, params),
  }), [language, setLanguage, toggleLanguage])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const value = useContext(I18nContext)
  if (!value) {
    return {
      language: DEFAULT_LANGUAGE,
      setLanguage: () => {},
      toggleLanguage: () => {},
      t: (key, params) => translate(key, DEFAULT_LANGUAGE, params),
    } satisfies I18nContextValue
  }
  return value
}
