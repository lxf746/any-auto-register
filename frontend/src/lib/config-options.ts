export type ChoiceOption = {
  value: string
  label: string
}

export type ProviderField = {
  key: string
  label: string
  placeholder?: string
  secret?: boolean
  category?: string
  hint?: string
  type?: 'text' | 'select' | 'textarea' | 'toggle' | 'async-select'
  options?: Array<{ value: string; label: string }>
  asyncUrl?: string
  asyncValueKey?: string
  asyncLabelKey?: string
  /**
   * If set, this async-select will re-fetch options when the form field referenced by asyncDependsOn changes.
   * The referenced value will be passed to backend via query param asyncQueryParam.
   */
  asyncDependsOn?: string
  asyncQueryParam?: string
}

export type ProviderOption = {
  provider_type?: string
  provider_key?: string
  value: string
  label: string
  description?: string
  driver_type?: string
  default_auth_mode?: string
  auth_modes?: Array<{ value: string; label: string }>
  fields: ProviderField[]
  is_builtin?: boolean
  category?: string
}

export type ProviderDriver = {
  provider_type?: string
  driver_type: string
  label: string
  description?: string
  default_auth_mode?: string
  auth_modes?: Array<{ value: string; label: string }>
  fields: ProviderField[]
}

export type CaptchaPolicy = {
  protocol_mode?: string
  protocol_order?: string[]
  browser_mode?: string
}

export type ConfigOptionsResponse = {
  mailbox_providers: ProviderOption[]
  captcha_providers: ProviderOption[]
  sms_providers?: ProviderOption[]
  mailbox_drivers?: ProviderDriver[]
  captcha_drivers?: ProviderDriver[]
  sms_drivers?: ProviderDriver[]
  mailbox_settings?: ProviderSetting[]
  captcha_settings?: ProviderSetting[]
  sms_settings?: ProviderSetting[]
  captcha_policy?: CaptchaPolicy
  executor_options?: ChoiceOption[]
  identity_mode_options?: ChoiceOption[]
  oauth_provider_options?: ChoiceOption[]
}

export type ProviderSetting = {
  id: number
  provider_type: string
  provider_key: string
  display_name: string
  catalog_label: string
  description?: string
  driver_type?: string
  auth_mode: string
  auth_modes: Array<{ value: string; label: string }>
  enabled: boolean
  is_default: boolean
  fields: ProviderField[]
  config: Record<string, string>
  auth: Record<string, string>
  auth_preview?: Record<string, string>
  metadata?: Record<string, unknown>
}

export function getProviderSelectOptions(providers: ProviderOption[]): Array<[string, string]> {
  return providers.map(provider => [provider.value, provider.label])
}

export function listProviderFieldKeys(providers: ProviderOption[] = []): string[] {
  const keys = new Set<string>()
  providers.forEach(provider => {
    ;(provider.fields || []).forEach(field => {
      if (field.key) {
        keys.add(field.key)
      }
    })
  })
  return Array.from(keys)
}

export function getCaptchaStrategyLabel(executorType: string, policy?: CaptchaPolicy, providers?: ProviderOption[]) {
  if (executorType === 'headless' || executorType === 'headed') {
    const browserDefault = policy?.browser_mode || ''
    const label = providers?.find(item => item.value === browserDefault)?.label || browserDefault
    return label ? `浏览器模式默认使用 ${label}` : '浏览器模式未配置默认验证码 provider'
  }
  const order = policy?.protocol_order || []
  if (order.length === 0) {
    return '协议模式未配置可用的远程验证码 provider'
  }
  const labels = order.map(value => providers?.find(item => item.value === value)?.label || value)
  return `协议模式按已启用顺序自动选择远程打码服务：${labels.join(' -> ')}`
}
