from __future__ import annotations

from typing import Any

from core.base_sms import create_phone_callbacks

from .errors import BrowserReuseRequiredError, IdentityResolutionError, RegistrationUnsupportedError
from .models import RegistrationContext


def has_reusable_oauth_browser(identity: Any) -> bool:
    return bool((getattr(identity, "chrome_user_data_dir", "") or "").strip() or (getattr(identity, "chrome_cdp_url", "") or "").strip())


def resolve_timeout(extra: dict[str, Any], keys: tuple[str, ...], default: int) -> int:
    for key in keys:
        value = extra.get(key)
        if value not in (None, ""):
            return int(value)
    return int(default)


def ensure_identity_email(ctx: RegistrationContext, message: str) -> None:
    if not getattr(ctx.identity, "email", ""):
        raise IdentityResolutionError(message)


def ensure_mailbox_identity(ctx: RegistrationContext, message: str) -> None:
    if not getattr(ctx.identity, "has_mailbox", False):
        raise IdentityResolutionError(message)


def ensure_oauth_executor_allowed(ctx: RegistrationContext, allowed_executor_types: tuple[str, ...] | None, message: str | None = None) -> None:
    if not allowed_executor_types:
        return
    if ctx.executor_type not in allowed_executor_types:
        expected = ", ".join(allowed_executor_types)
        raise RegistrationUnsupportedError(message or f"{ctx.platform_display_name} 当前 OAuth 仅支持 executor_type={expected}")


def ensure_oauth_browser_reuse(ctx: RegistrationContext, message: str) -> None:
    if not has_reusable_oauth_browser(ctx.identity):
        raise BrowserReuseRequiredError(message)


def build_otp_callback(
    ctx: RegistrationContext,
    *,
    keyword: str = "",
    timeout: int | None = None,
    code_pattern: str | None = None,
    wait_message: str = "等待验证码...",
    success_label: str = "验证码",
):
    mailbox = getattr(ctx.platform, "mailbox", None)
    mail_acct = getattr(ctx.identity, "mailbox_account", None)
    if not mailbox or not mail_acct:
        return None

    def otp_cb():
        ctx.log(wait_message)
        kwargs = {"keyword": keyword, "before_ids": getattr(ctx.identity, "before_ids", set())}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if code_pattern:
            kwargs["code_pattern"] = code_pattern
        code = mailbox.wait_for_code(mail_acct, **kwargs)
        if code:
            ctx.log(f"{success_label}: {code}")
        return code

    return otp_cb


def build_phone_callbacks(ctx: RegistrationContext, *, service: str | None = None):
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    extra = ctx.extra
    requested_provider_key = str(
        extra.get("sms_provider")
        or extra.get("phone_provider")
        or ""
    ).strip()
    settings_repo = ProviderSettingsRepository()
    definitions_repo = ProviderDefinitionsRepository()

    provider_key = requested_provider_key
    source = "task params"
    if not provider_key:
        provider_key = str(settings_repo.get_default_provider_key("sms") or "").strip()
        source = "global default"
    if not provider_key:
        if extra.get("sms_activate_api_key"):
            provider_key = "sms_activate"
            source = "legacy sms_activate_api_key"
    if not provider_key:
        ctx.log("[SMS] 未配置 SMS provider（任务参数/全局默认/历史兼容字段都为空），phone_callback=None — 注册到 add_phone 步骤将抛错")
        return None, None

    definition = definitions_repo.get_by_key("sms", provider_key)
    merged = settings_repo.resolve_runtime_settings("sms", provider_key, extra) if definition else dict(extra)

    auth_fields = []
    if definition:
        auth_fields = [
            str(field.get("key") or "").strip()
            for field in definition.get_fields()
            if str(field.get("category") or "").strip() == "auth"
        ]
    if auth_fields and not any(str(merged.get(field_key, "")).strip() for field_key in auth_fields):
        ctx.log(f"[SMS] provider={provider_key} (来源={source}) 已找到 definition，但认证字段 {auth_fields} 全部为空，phone_callback=None")
        return None, None

    # 默认不让短信/邮箱等第三方服务走平台代理（避免代理对外部 API 造成额外失败）。
    # 只有显式配置 sms_proxy / proxy / sms_use_proxy=true 时才使用代理。
    use_sms_proxy = str(merged.get("sms_use_proxy") or "").strip().lower() in ("1", "true", "yes", "on")
    if use_sms_proxy and ctx.proxy and not str(merged.get("sms_proxy") or merged.get("proxy") or "").strip():
        merged["sms_proxy"] = ctx.proxy

    country = str(
        merged.get("sms_country")
        or merged.get("phone_country")
        or merged.get("sms_activate_country")
        or merged.get("sms_activate_default_country")
        or merged.get("herosms_country")
        or merged.get("herosms_default_country")
        or merged.get("smsbower_country")
        or merged.get("smsbower_default_country")
        or merged.get("grizzlysms_country")
        or merged.get("grizzlysms_default_country")
        or merged.get("fivesim_country")
        or merged.get("fivesim_default_country")
        or ""
    ).strip()
    sms_service = str(
        merged.get("sms_service")
        or merged.get("herosms_service")
        or merged.get("herosms_default_service")
        or merged.get("smsbower_service")
        or merged.get("smsbower_default_service")
        or merged.get("grizzlysms_service")
        or merged.get("grizzlysms_default_service")
        or merged.get("fivesim_product")
        or merged.get("fivesim_default_product")
        or merged.get("sms_activate_service")
        or merged.get("sms_activate_default_service")
        or service
        or ctx.platform_name
    ).strip() or ctx.platform_name
    ctx.log(f"[SMS] phone_callback 已就绪: provider={provider_key} 来源={source} service={sms_service} country={country or 'default'}")
    return create_phone_callbacks(
        provider_key,
        merged,
        service=sms_service,
        country=country,
        log_fn=ctx.log,
    )


def build_link_callback(
    ctx: RegistrationContext,
    *,
    keyword: str = "",
    timeout: int | None = None,
    wait_message: str = "等待验证链接邮件...",
    success_label: str = "验证链接",
    preview_chars: int = 80,
):
    mailbox = getattr(ctx.platform, "mailbox", None)
    mail_acct = getattr(ctx.identity, "mailbox_account", None)
    if not mailbox or not mail_acct:
        return None

    def link_cb():
        ctx.log(wait_message)
        before_ids = mailbox.get_current_ids(mail_acct)
        kwargs = {"keyword": keyword, "before_ids": before_ids}
        if timeout is not None:
            kwargs["timeout"] = timeout
        link = mailbox.wait_for_link(mail_acct, **kwargs)
        if link:
            preview = link if len(link) <= preview_chars else f"{link[:preview_chars]}..."
            ctx.log(f"{success_label}: {preview}")
        return link

    return link_cb
