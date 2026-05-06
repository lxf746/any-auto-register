import { translate, translateChoiceLabel, type Language } from '@/lib/i18n'

type ChoiceOption = {
  value: string
  label: string
}

export function hasReusableOAuthBrowser(config: { chrome_user_data_dir?: string; chrome_cdp_url?: string }) {
  return Boolean(config.chrome_user_data_dir?.trim() || config.chrome_cdp_url?.trim())
}

function getOptionLabel(value: string, options: ChoiceOption[] = [], language?: Language) {
  return translateChoiceLabel(value, options.find(item => item.value === value)?.label || value, language)
}

export function pickOAuthExecutor(
  supportedExecutors: string[],
  preferredExecutor: string,
  reusableBrowser: boolean,
) {
  if (supportedExecutors.includes(preferredExecutor) && preferredExecutor !== 'protocol') {
    return preferredExecutor
  }
  if (reusableBrowser && supportedExecutors.includes('headless')) {
    return 'headless'
  }
  if (supportedExecutors.includes('headed')) {
    return 'headed'
  }
  if (supportedExecutors.includes('headless')) {
    return 'headless'
  }
  return supportedExecutors[0] || ''
}

export function buildRegistrationOptions(platformMeta: any, language?: Language) {
  const supportedModes: string[] = platformMeta?.supported_identity_modes || []
  const supportedOAuth: string[] = platformMeta?.supported_oauth_providers || []
  const identityModeOptions: ChoiceOption[] = platformMeta?.supported_identity_mode_options || []
  const oauthProviderOptions: ChoiceOption[] = platformMeta?.supported_oauth_provider_options || []
  const options: Array<{
    key: string
    label: string
    description: string
    identityProvider: string
    oauthProvider: string
  }> = []

  if (supportedModes.includes('mailbox')) {
    const label = getOptionLabel('mailbox', identityModeOptions, language)
    options.push({
      key: 'mailbox',
      label,
      description: translate('registration.mailboxDescription', language, { label }),
      identityProvider: 'mailbox',
      oauthProvider: '',
    })
  }

  if (supportedModes.includes('oauth_browser')) {
    supportedOAuth.forEach((provider: string) => {
      const providerLabel = getOptionLabel(provider, oauthProviderOptions, language)
      options.push({
        key: `oauth:${provider}`,
        label: providerLabel,
        description: translate('registration.oauthDescription', language, { label: providerLabel }),
        identityProvider: 'oauth_browser',
        oauthProvider: provider,
      })
    })
  }

  return options
}

export function buildExecutorOptions(
  identityProvider: string,
  supportedExecutors: string[],
  reusableBrowser: boolean,
  executorOptions: ChoiceOption[] = [],
  language?: Language,
) {
  return supportedExecutors.map((executor) => {
    const option = {
      value: executor,
      label: getOptionLabel(executor, executorOptions, language),
      description: '',
      disabled: false,
      reason: '',
    }

    if (executor === 'protocol') {
      option.description = translate('executor.protocolDescription', language)
      if (identityProvider !== 'mailbox') {
        option.disabled = true
        option.reason = translate('executor.oauthRequiresBrowser', language)
      }
      return option
    }

    if (executor === 'headless') {
      option.description = identityProvider === 'mailbox'
        ? translate('executor.headlessMailboxDescription', language)
        : translate('executor.headlessOauthDescription', language)
      if (identityProvider === 'oauth_browser' && !reusableBrowser) {
        option.disabled = true
        option.reason = translate('executor.requiresChromeProfile', language)
      }
      return option
    }

    option.description = translate('executor.headedDescription', language)
    return option
  })
}
