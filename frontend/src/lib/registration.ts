type ChoiceOption = {
  value: string
  label: string
}

type AppLocale = 'en' | 'vi' | 'zh'

const VALUE_LABELS: Record<string, { en: string; vi: string; zh: string }> = {
  mailbox: { en: 'System mailbox', vi: 'Mailbox hệ thống', zh: '系统邮箱' },
  oauth_browser: { en: 'Third-party account', vi: 'Tài khoản bên thứ ba', zh: '第三方账号' },
  protocol: { en: 'Protocol mode', vi: 'Chế độ giao thức', zh: '协议模式' },
  headless: { en: 'Background browser automation', vi: 'Tự động trình duyệt nền', zh: '后台浏览器自动' },
  headed: { en: 'Visible browser automation', vi: 'Tự động trình duyệt có giao diện', zh: '可视浏览器自动' },
  google: { en: 'Google', vi: 'Google', zh: 'Google' },
  microsoft: { en: 'Microsoft', vi: 'Microsoft', zh: 'Microsoft' },
  github: { en: 'GitHub', vi: 'GitHub', zh: 'GitHub' },
  apple: { en: 'Apple', vi: 'Apple', zh: 'Apple' },
}

function getLocalizedLabel(value: string, locale: AppLocale) {
  return VALUE_LABELS[value]?.[locale] || ''
}

export function hasReusableOAuthBrowser(config: { chrome_user_data_dir?: string; chrome_cdp_url?: string }) {
  return Boolean(config.chrome_user_data_dir?.trim() || config.chrome_cdp_url?.trim())
}

function getOptionLabel(value: string, options: ChoiceOption[] = [], locale: AppLocale = 'zh') {
  const localized = getLocalizedLabel(value, locale)
  if (localized) return localized
  return options.find(item => item.value === value)?.label || value
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

export function buildRegistrationOptions(platformMeta: any, locale: AppLocale = 'zh') {
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
    const mailboxLabel = getOptionLabel('mailbox', identityModeOptions, locale)
    options.push({
      key: 'mailbox',
      label: mailboxLabel,
      description: locale === 'en'
        ? `Use ${mailboxLabel} to receive verification emails and complete registration automatically`
        : locale === 'vi'
          ? `Dùng ${mailboxLabel} để tự động nhận mã email và hoàn tất đăng ký`
          : `使用${mailboxLabel}自动收验证码并完成注册`,
      identityProvider: 'mailbox',
      oauthProvider: '',
    })
  }

  if (supportedModes.includes('oauth_browser')) {
    supportedOAuth.forEach((provider: string) => {
      const providerLabel = getOptionLabel(provider, oauthProviderOptions, locale)
      options.push({
        key: `oauth:${provider}`,
        label: providerLabel,
        description: locale === 'en'
          ? `Use ${providerLabel} account to automatically create platform accounts`
          : locale === 'vi'
            ? `Dùng tài khoản ${providerLabel} để tự động tạo tài khoản nền tảng`
            : `使用 ${providerLabel} 账号自动创建平台账号`,
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
  locale: AppLocale = 'zh',
) {
  return supportedExecutors.map((executor) => {
    const option = {
      value: executor,
      label: getOptionLabel(executor, executorOptions, locale),
      description: '',
      disabled: false,
      reason: '',
    }

    if (executor === 'protocol') {
      option.description = locale === 'en'
        ? 'Runs without opening a browser by using the protocol flow directly'
        : locale === 'vi'
          ? 'Không mở trình duyệt, chạy trực tiếp theo luồng giao thức'
          : '不打开浏览器，直接通过协议流程自动注册'
      if (identityProvider !== 'mailbox') {
        option.disabled = true
        option.reason = locale === 'en'
          ? 'Third-party account registration must use browser automation'
          : locale === 'vi'
            ? 'Đăng ký bằng tài khoản bên thứ ba phải dùng tự động hóa trình duyệt'
            : '第三方账号注册必须通过浏览器自动化完成'
      }
      return option
    }

    if (executor === 'headless') {
      option.description = identityProvider === 'mailbox'
        ? (locale === 'en'
          ? 'Browser automation runs in background without a visible window'
          : locale === 'vi'
            ? 'Tự động hóa chạy nền, không hiển thị cửa sổ trình duyệt'
            : '浏览器在后台自动执行，界面不可见')
        : (locale === 'en'
          ? 'Reuses local signed-in browser session to finish third-party login in background'
          : locale === 'vi'
            ? 'Tái sử dụng phiên đăng nhập trình duyệt cục bộ để hoàn tất đăng nhập bên thứ ba ở chế độ nền'
            : '复用本机浏览器登录态，在后台自动完成第三方登录')
      if (identityProvider === 'oauth_browser' && !reusableBrowser) {
        option.disabled = true
        option.reason = locale === 'en'
          ? 'Configure Chrome Profile path or Chrome CDP URL in global settings first'
          : locale === 'vi'
            ? 'Cần cấu hình đường dẫn Chrome Profile hoặc địa chỉ Chrome CDP trong cài đặt toàn cục trước'
            : '需要先在全局配置里填写 Chrome Profile 路径或 Chrome CDP 地址'
      }
      return option
    }

    option.description = locale === 'en'
      ? 'Opens a browser window while automation still runs automatically'
      : locale === 'vi'
        ? 'Mở cửa sổ trình duyệt nhưng vẫn tự động chạy, không cần thao tác thêm'
        : '会打开浏览器窗口，但系统仍自动执行，无需额外交互'
    return option
  })
}
