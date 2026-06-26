"""Mailbox provider registry — factory functions and create_mailbox entry point."""
import logging

from core.mailbox.base import BaseMailbox, FallbackMailbox

logger = logging.getLogger(__name__)


# ── Factory functions ──

def _create_tempmail(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.tempmail_lol import TempMailLolMailbox
    return TempMailLolMailbox(
        proxy=proxy,
        api_url=extra.get("tempmail_lol_api_url", ""),
    )


def _create_tempyemail(extra: dict, proxy: str | None) -> BaseMailbox:
    from providers.mailbox.tempyemail import TempyMailbox
    return TempyMailbox(
        proxy=proxy,
        api_url=extra.get("tempyemail_api_url", ""),
    )


def _create_tempmail_web(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.tempmail_web import TempMailWebMailbox
    return TempMailWebMailbox(
        base_url=extra.get("tempmail_web_base_url", ""),
        proxy=proxy,
    )


def _create_duckmail(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.duckmail import DuckMailMailbox
    return DuckMailMailbox(
        api_url=extra.get("duckmail_api_url", ""),
        provider_url=extra.get("duckmail_provider_url", ""),
        bearer=extra.get("duckmail_bearer", ""),
        proxy=proxy,
    )


def _create_ddg_email(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.ddg_email import DDGEmailMailbox
    return DDGEmailMailbox(
        bearer=extra.get("ddg_bearer", ""),
        imap_host=extra.get("ddg_imap_host", ""),
        imap_user=extra.get("ddg_imap_user", ""),
        imap_pass=extra.get("ddg_imap_pass", ""),
        proxy=proxy,
    )


def _create_freemail(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.freemail import FreemailMailbox
    return FreemailMailbox(
        api_url=extra.get("freemail_api_url", ""),
        admin_token=extra.get("freemail_admin_token", ""),
        username=extra.get("freemail_username", ""),
        password=extra.get("freemail_password", ""),
        proxy=proxy,
    )


def _create_moemail(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.moemail import MoeMailMailbox
    return MoeMailMailbox(
        api_url=extra.get("moemail_api_url"),
        username=extra.get("moemail_username", ""),
        password=extra.get("moemail_password", ""),
        session_token=extra.get("moemail_session_token", ""),
        proxy=proxy,
    )


def _create_mailtm(extra: dict, proxy: str | None) -> BaseMailbox:
    from providers.mailbox.mailtm import MailTmMailbox
    return MailTmMailbox(
        api_url=extra.get("mailtm_api_url", ""),
        proxy=proxy,
    )


def _create_cfworker(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.cfworker import CFWorkerMailbox
    return CFWorkerMailbox(
        api_url=extra.get("cfworker_api_url", ""),
        admin_token=extra.get("cfworker_admin_token", ""),
        domain=extra.get("cfworker_domain", ""),
        fingerprint=extra.get("cfworker_fingerprint", ""),
        proxy=proxy,
    )


def _create_testmail(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.testmail import TestmailMailbox
    return TestmailMailbox(
        api_url=extra.get("testmail_api_url", ""),
        api_key=extra.get("testmail_api_key", ""),
        namespace=extra.get("testmail_namespace", ""),
        tag_prefix=extra.get("testmail_tag_prefix", ""),
        proxy=proxy,
    )


def _create_local_ms_pool(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.local_ms_mailbox import LocalMicrosoftMailboxPool
    return LocalMicrosoftMailboxPool(
        pool_text=extra.get("local_ms_pool_text", ""),
        pool_file=extra.get("local_ms_pool_file", ""),
        state_file=extra.get("local_ms_pool_state_file", ""),
        graph_scope=extra.get("local_ms_graph_scope", ""),
        allow_reuse=str(extra.get("local_ms_pool_allow_reuse", "")).strip().lower() in {"1", "true", "yes", "on"},
        proxy=proxy,
    )


def _create_laoudo(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.laoudo import LaoudoMailbox
    return LaoudoMailbox(
        auth_token=extra.get("laoudo_auth", ""),
        email=extra.get("laoudo_email", ""),
        account_id=extra.get("laoudo_account_id", ""),
    )


def _create_aitre(extra: dict, proxy: str | None) -> BaseMailbox:
    from core.mailbox.aitre import AitreMailbox
    email = extra.get("aitre_email", "").strip()
    if not email:
        raise RuntimeError("Aitre email address is required but not configured. Please set the email address in the provider settings.")
    return AitreMailbox(
        email=email,
        api_url=extra.get("aitre_api_url", ""),
    )


def _create_generic_http(extra: dict, proxy: str | None, *, pipeline_config: dict | None = None) -> BaseMailbox:
    from core.generic_http_mailbox import GenericHttpMailbox
    return GenericHttpMailbox(
        pipeline_config=pipeline_config or {},
        settings=extra,
        proxy=proxy,
    )


# ── Registry ──

MAILBOX_FACTORY_REGISTRY = {
    "generic_http_mailbox": _create_generic_http,
    "tempmail_lol_api": _create_tempmail,
    "tempmail_web_api": _create_tempmail_web,
    "duckmail_api": _create_duckmail,
    "ddg_email": _create_ddg_email,
    "ddg_email_api": _create_ddg_email,
    "freemail_api": _create_freemail,
    "moemail_api": _create_moemail,
    "mailtm_api": _create_mailtm,
    "cfworker_admin_api": _create_cfworker,
    "testmail_api": _create_testmail,
    "local_ms_pool": _create_local_ms_pool,
    "laoudo_api": _create_laoudo,
    "aitre_api": _create_aitre,
    "tempyemail_api": _create_tempyemail,
    # backward-compat fallback
    "generic_http": _create_generic_http,
    "tempmail_lol": _create_tempmail,
    "tempmail_web": _create_tempmail_web,
    "duckmail": _create_duckmail,
    "freemail": _create_freemail,
    "moemail": _create_moemail,
    "mailtm": _create_mailtm,
    "cfworker": _create_cfworker,
    "testmail": _create_testmail,
    "local_ms": _create_local_ms_pool,
    "laoudo": _create_laoudo,
    "aitre": _create_aitre,
    "tempyemail": _create_tempyemail,
}


# ── Entry point ──

def create_mailbox(provider: str, extra: dict = None, proxy: str = None) -> BaseMailbox:
    """Factory method: create a mailbox instance based on provider"""
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    definitions_repo = ProviderDefinitionsRepository()
    settings_repo = ProviderSettingsRepository()
    provider_key = str(provider or "").strip()
    if not provider_key:
        raise RuntimeError("No mailbox provider selected, please configure and enable a default mailbox provider in settings")
    definition = definitions_repo.get_by_key("mailbox", provider_key)
    if not definition or not definition.enabled:
        raise RuntimeError(f"Mailbox provider does not exist or is disabled: {provider_key}")
    base_extra = dict(extra or {})

    raw_fallbacks = base_extra.get("mail_provider_fallbacks")
    explicit_fallbacks: list[str] = []
    if isinstance(raw_fallbacks, str):
        explicit_fallbacks = [item.strip() for item in raw_fallbacks.split(",") if item.strip()]
    elif isinstance(raw_fallbacks, (list, tuple, set)):
        explicit_fallbacks = [str(item or "").strip() for item in raw_fallbacks if str(item or "").strip()]

    enabled_items = settings_repo.list_enabled("mailbox")
    enabled_keys = [str(item.provider_key or "").strip() for item in enabled_items if str(item.provider_key or "").strip()]
    ordered_keys: list[str] = [provider_key]
    for key in explicit_fallbacks:
        if key not in ordered_keys:
            ordered_keys.append(key)
    for key in enabled_keys:
        if key == provider_key or key == "laoudo" or key in ordered_keys:
            continue
        ordered_keys.append(key)

    providers: list[tuple[str, BaseMailbox]] = []
    for key in ordered_keys:
        current_definition = definitions_repo.get_by_key("mailbox", key)
        if not current_definition or not current_definition.enabled:
            continue
        resolved_extra = settings_repo.resolve_runtime_settings("mailbox", key, base_extra)
        lookup_key = current_definition.driver_type if current_definition else key
        factory = MAILBOX_FACTORY_REGISTRY.get(lookup_key)
        if not factory:
            continue
        try:
            if lookup_key in ("generic_http_mailbox", "generic_http"):
                pipeline_config = current_definition.get_metadata() if current_definition else {}
                providers.append((key, factory(resolved_extra, proxy, pipeline_config=pipeline_config)))
            else:
                providers.append((key, factory(resolved_extra, proxy)))
        except Exception as exc:
            if key == provider_key:
                raise RuntimeError(f"Mailbox provider {key} initialization failed: {exc}") from exc
            logger.warning("Mailbox provider %s initialization failed, skipped: %s", key, exc)

    if not providers:
        raise RuntimeError("No available mailbox provider instances")
    if len(providers) == 1:
        return providers[0][1]
    return FallbackMailbox(providers)
