from __future__ import annotations

import logging

from sqlmodel import Session, select

from core.datetime_utils import _utcnow
from core.db import ProviderDefinitionModel, ProviderSettingModel, engine

logger = logging.getLogger(__name__)


_BUILTIN_DEFINITIONS: list[dict] = [
    # ── mailbox ──────────────────────────────────────────────────────
    {
        "provider_type": "mailbox",
        "provider_key": "cfworker_admin_api",
        "label": "CF Worker (Self-Hosted Domain)",
        "description": "Custom domain mailbox based on Cloudflare Worker. Requires self-deploying the Worker backend.",
        "driver_type": "cfworker_admin_api",
        "default_auth_mode": "token",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "token", "label": "Token Authentication"}],
        "fields": [
            {"key": "cfworker_api_url", "label": "API URL", "placeholder": "https://your-worker.example.com", "category": "connection"},
            {"key": "cfworker_admin_token", "label": "Admin Token", "secret": True, "category": "auth"},
            {"key": "cfworker_domain", "label": "Mailbox Domain", "placeholder": "example.com", "category": "connection"},
            {"key": "cfworker_fingerprint", "label": "Fingerprint (Optional)", "placeholder": "", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "moemail_api",
        "label": "MoeMail（sall.cc）",
        "description": "Self-hosted temporary mailbox. Supports automatic account registration or manual login to existing accounts.",
        "driver_type": "moemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [
            {"value": "password", "label": "Account Password"},
            {"value": "token", "label": "Session Token"},
        ],
        "fields": [
            {"key": "moemail_api_url", "label": "API URL", "placeholder": "https://moemail.example.com", "category": "connection"},
            {"key": "moemail_username", "label": "Username (Optional)", "category": "auth"},
            {"key": "moemail_password", "label": "Password (Optional)", "secret": True, "category": "auth"},
            {"key": "moemail_session_token", "label": "Session Token (Optional)", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_lol_api",
        "label": "TempMail.lol",
        "description": "Free temporary mailbox, ready to use out of the box, no configuration required.",
        "driver_type": "tempmail_lol_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "tempmail_lol_api_url", "label": "API URL (Optional)", "placeholder": "https://api.tempmail.lol/v2", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempyemail_api",
        "label": "Tempy.Email",
        "description": "Free temporary mailbox via tempy.email, no configuration required, auto-generated.",
        "driver_type": "tempyemail_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "mailtm_api",
        "label": "Mail.tm",
        "description": "Free temporary mailbox, no configuration required, auto-generated.",
        "driver_type": "mailtm_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "mailtm_api_url", "label": "API URL (Optional)", "placeholder": "https://api.mail.tm", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_web_api",
        "label": "Temp-Mail.org",
        "description": "Free temporary mailbox, requires browser environment (Camoufox).",
        "driver_type": "tempmail_web_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "tempmail_web_base_url", "label": "API URL (Optional)", "placeholder": "https://web2.temp-mail.org", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "duckmail_api",
        "label": "DuckMail (Auto-Generated)",
        "description": "Self-hosted mailbox service that auto-generates temporary mailboxes via API.",
        "driver_type": "duckmail_api",
        "default_auth_mode": "bearer",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "bearer", "label": "Bearer Token"}],
        "fields": [
            {"key": "duckmail_api_url", "label": "API URL", "placeholder": "https://duckmail.example.com", "category": "connection"},
            {"key": "duckmail_provider_url", "label": "Provider URL (Optional)", "placeholder": "", "category": "connection"},
            {"key": "duckmail_bearer", "label": "Bearer Token", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "freemail_api",
        "label": "FreeMail (Auto-Generated)",
        "description": "Self-hosted mailbox service. Supports account/password or Admin Token authentication.",
        "driver_type": "freemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "password", "label": "Account Password"}, {"value": "token", "label": "Admin Token"}],
        "fields": [
            {"key": "freemail_api_url", "label": "API URL", "placeholder": "https://freemail.example.com", "category": "connection"},
            {"key": "freemail_admin_token", "label": "Admin Token", "secret": True, "category": "auth"},
            {"key": "freemail_username", "label": "Username", "category": "auth"},
            {"key": "freemail_password", "label": "Password", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "testmail_api",
        "label": "Testmail (Namespace Mailbox)",
        "description": "Third-party service from Testmail.app. Automatically constructs mailbox addresses via API Key and Namespace.",
        "driver_type": "testmail_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "testmail_api_url", "label": "API URL (Optional)", "placeholder": "https://api.testmail.app", "category": "connection"},
            {"key": "testmail_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "testmail_namespace", "label": "Namespace", "category": "identity"},
            {"key": "testmail_tag_prefix", "label": "Tag Prefix (Optional)", "placeholder": "", "category": "identity"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "laoudo_api",
        "label": "Laoudo (Fixed Mailbox)",
        "description": "Fixed domain mailbox from laoudo.com. Use an existing email address to receive verification codes.",
        "driver_type": "laoudo_api",
        "default_auth_mode": "token",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "token", "label": "JWT Token"}],
        "fields": [
            {"key": "laoudo_auth", "label": "Auth Token", "secret": True, "category": "auth"},
            {"key": "laoudo_email", "label": "Email Address", "placeholder": "your@email.com", "category": "identity"},
            {"key": "laoudo_account_id", "label": "Account ID", "category": "identity"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "aitre_api",
        "label": "Aitre Temporary Mailbox",
        "description": "Free temporary mailbox from mail.aitre.cc. Requires specifying a fixed email address.",
        "driver_type": "aitre_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "aitre_email", "label": "Email Address", "placeholder": "your@email.com", "category": "identity"},
            {"key": "aitre_api_url", "label": "API URL (Optional)", "placeholder": "https://mail.aitre.cc/api/tempmail", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "ddg_email",
        "label": "DuckDuckGo Email",
        "description": "DuckDuckGo Email Protection. Generates @duck.com aliases and reads verification codes via IMAP from the forwarding mailbox.",
        "driver_type": "ddg_email",
        "default_auth_mode": "bearer",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "bearer", "label": "Bearer Token"}],
        "fields": [
            {"key": "ddg_bearer", "label": "DDG Bearer Token", "secret": True, "category": "auth"},
            {"key": "ddg_imap_host", "label": "IMAP Server (Optional)", "placeholder": "Auto-detect", "category": "connection"},
            {"key": "ddg_imap_user", "label": "IMAP Username (Forwarding Mailbox)", "placeholder": "your@gmail.com", "category": "auth"},
            {"key": "ddg_imap_pass", "label": "IMAP Password", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "local_ms_pool",
        "label": "Local Microsoft Mailbox Pool",
        "description": "Import mailbox pool in Xinlan Mailbox Assistant universal format. Prioritizes using Client ID + refresh token to receive verification codes via Microsoft Graph.",
        "driver_type": "local_ms_pool",
        "default_auth_mode": "pool",
        "enabled": True,
        "category": "custom",
        "auth_modes": [{"value": "pool", "label": "Account Pool"}],
        "fields": [
            {
                "key": "local_ms_pool_file",
                "label": "Account Pool File Path",
                "placeholder": "/Users/you/ms-mail-pool.txt",
                "category": "connection",
                "hint": "Optional; one Xinlan Mailbox Assistant universal format entry per line. After configuring the file path, there is no need to paste account plaintext into the settings page.",
            },
            {
                "key": "local_ms_pool_text",
                "label": "Account Pool Text",
                "type": "textarea",
                "category": "auth",
                "hint": "Optional; directly paste Xinlan Mailbox Assistant universal format. Supports comma, Chinese comma, TAB, and ---- delimiters.",
            },
            {
                "key": "local_ms_graph_scope",
                "label": "Graph Scope",
                "placeholder": "https://graph.microsoft.com/Mail.Read offline_access",
                "category": "connection",
            },
            {
                "key": "local_ms_pool_state_file",
                "label": "Occupancy State File",
                "placeholder": "Default: data/.local_ms_mailbox_pool_state.json",
                "category": "connection",
                "hint": "Used to prevent the same mailbox from being assigned repeatedly. Clearing this file resets the account pool occupancy state.",
            },
            {
                "key": "local_ms_pool_allow_reuse",
                "label": "Allow Reusing Mailboxes",
                "type": "toggle",
                "category": "connection",
                "hint": "Can be enabled during testing; recommended to disable for bulk registration.",
            },
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "generic_http_mailbox",
        "label": "Generic HTTP Mailbox",
        "description": "Connect to any mailbox API by configuring HTTP endpoints and authentication methods. Suitable for advanced users.",
        "driver_type": "generic_http_mailbox",
        "default_auth_mode": "",
        "enabled": True,
        "category": "custom",
        "auth_modes": [],
        "fields": [],
    },
    # ── captcha ──────────────────────────────────────────────────────
    {
        "provider_type": "captcha",
        "provider_key": "yescaptcha_api",
        "label": "YesCaptcha",
        "description": "YesCaptcha cloud CAPTCHA recognition service. Supports Turnstile and other types.",
        "driver_type": "yescaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "yescaptcha_key", "label": "Client Key", "secret": True},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "twocaptcha_api",
        "label": "2Captcha",
        "description": "2Captcha cloud CAPTCHA recognition service. Supports Turnstile and other types.",
        "driver_type": "twocaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "twocaptcha_key", "label": "API Key", "secret": True},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "local_solver",
        "label": "Local CAPTCHA Solver",
        "description": "Invoke local api_solver service (Camoufox/patchright) to solve Turnstile CAPTCHA.",
        "driver_type": "local_solver",
        "default_auth_mode": "",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [],
        "fields": [
            {"key": "solver_url", "label": "Solver URL", "placeholder": "http://localhost:8889"},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "manual",
        "label": "Manual CAPTCHA",
        "description": "Block and wait for user to manually input the CAPTCHA. Suitable for debugging scenarios.",
        "driver_type": "manual",
        "default_auth_mode": "",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [],
        "fields": [],
    },
    # ── sms ──────────────────────────────────────────────────────────
    {
        "provider_type": "sms",
        "provider_key": "herosms_api",
        "label": "HeroSMS",
        "description": "HeroSMS SMS code receiving platform. Supports number reuse and auto-resend.",
        "driver_type": "herosms_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "herosms_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "herosms_default_country", "label": "Default Country", "type": "async-select", "asyncUrl": "/sms/herosms/countries", "asyncValueKey": "id", "asyncLabelKey": "chn", "placeholder": "Please select a country..."},
            {"key": "herosms_default_service", "label": "Default Service", "type": "async-select", "asyncUrl": "/sms/herosms/services", "asyncValueKey": "code", "asyncLabelKey": "name", "placeholder": "Please select a service..."},
            {"key": "herosms_max_price", "label": "Max Price (Optional)", "placeholder": "-1"},
            {"key": "herosms_auto_country", "label": "Auto Select Optimal Country", "type": "toggle", "hint": "When enabled, ignores the default country and automatically selects the country with the lowest price and sufficient stock."},
            {"key": "herosms_auto_country_min_stock", "label": "Auto-Select Country Min Stock", "placeholder": "20"},
            {"key": "herosms_auto_country_max_price", "label": "Auto-Select Country Max Price", "placeholder": "0 (unlimited)"},
            {"key": "register_phone_extra_max", "label": "Number Reuse Extra Limit", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "Reuse Number to Max", "type": "toggle"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "sms_activate_api",
        "label": "SMS-Activate",
        "description": "SMS-Activate SMS code receiving platform (sms-activate.guru).",

        "driver_type": "sms_activate_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "sms_activate_api_key", "label": "API Key", "secret": True},
            {"key": "sms_activate_default_country", "label": "Default Country Code", "placeholder": "ru"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "smsbower_api",
        "label": "SMSBower",
        "description": "SMSBower SMS code receiving platform. API compatible with HeroSMS. Supports number reuse and auto-resend.",
        "driver_type": "smsbower_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "smsbower_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "smsbower_default_country", "label": "Default Country", "type": "async-select", "asyncUrl": "/sms/smsbower/countries", "asyncValueKey": "id", "asyncLabelKey": "chn", "placeholder": "Please select a country..."},
            {"key": "smsbower_default_service", "label": "Default Service", "type": "async-select", "asyncUrl": "/sms/smsbower/services", "asyncValueKey": "code", "asyncLabelKey": "name", "placeholder": "Please select a service..."},
            {"key": "smsbower_max_price", "label": "Max Price (Optional)", "placeholder": "-1"},
            {"key": "smsbower_auto_country", "label": "Auto Select Optimal Country", "type": "toggle", "hint": "When enabled, ignores the default country and automatically selects the country with the lowest price and sufficient stock."},
            {"key": "register_phone_extra_max", "label": "Number Reuse Extra Limit", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "Reuse Number to Max", "type": "toggle"},
        ],
    },
    # ── proxy ────────────────────────────────────────────────────────
    {
        "provider_type": "proxy",
        "provider_key": "api_extract",
        "label": "API Extract Proxy",
        "description": "Dynamically extract proxy IP list via HTTP API. Suitable for most providers' API extraction interfaces.",
        "driver_type": "api_extract",
        "default_auth_mode": "",
        "enabled": False,
        "category": "thirdparty",
        "auth_modes": [],
        "fields": [
            {"key": "proxy_api_url", "label": "API URL", "placeholder": "https://provider.com/api/get_proxy?key=xxx"},
            {"key": "proxy_protocol", "label": "Protocol", "placeholder": "http / socks5"},
            {"key": "proxy_username", "label": "Username (Optional)"},
            {"key": "proxy_password", "label": "Password (Optional)", "secret": True},
        ],
    },
    {
        "provider_type": "proxy",
        "provider_key": "rotating_gateway",
        "label": "Rotating Gateway Proxy",
        "description": "Fixed entry address. Each request is automatically assigned a different exit IP. Suitable for BrightData / Oxylabs / IPRoyal, etc.",
        "driver_type": "rotating_gateway",
        "default_auth_mode": "",
        "enabled": False,
        "category": "thirdparty",
        "auth_modes": [],
        "fields": [
            {"key": "proxy_gateway_url", "label": "Gateway Address", "placeholder": "http://user:pass@gate.example.com:7777"},
        ],
    },
]


class ProviderDefinitionsRepository:

    def ensure_seeded(self) -> None:
        """Write built-in provider definition seed data into the database.

        Insert new ones, update field definitions for existing ones (label, description, fields, etc.),
        ensuring that built-in provider metadata is synchronized to the database after code upgrades.
        """
        with Session(engine) as session:
            existing: dict[str, ProviderDefinitionModel] = {}
            for row in session.exec(select(ProviderDefinitionModel)).all():
                key = f"{row.provider_type}::{row.provider_key}"
                existing[key] = row

            changed = False
            for seed in _BUILTIN_DEFINITIONS:
                key = f"{seed['provider_type']}::{seed['provider_key']}"
                item = existing.get(key)

                if item is None:
                    # New entry
                    item = ProviderDefinitionModel(
                        provider_type=seed["provider_type"],
                        provider_key=seed["provider_key"],
                        created_at=_utcnow(),
                    )
                    logger.info("Seed data: new entry %s/%s", seed["provider_type"], seed["provider_key"])

                # Update metadata (synchronize on every startup to ensure code changes take effect)
                item.label = seed.get("label", seed["provider_key"])
                item.description = seed.get("description", "")
                item.driver_type = seed.get("driver_type", seed["provider_key"])
                item.default_auth_mode = seed.get("default_auth_mode", "")
                item.enabled = seed.get("enabled", True)
                item.is_builtin = True
                item.category = seed.get("category", "")
                item.set_auth_modes(list(seed.get("auth_modes") or []))
                item.set_fields(list(seed.get("fields") or []))
                if not item.get_metadata():
                    # Only write seed values when metadata is empty to avoid overwriting user-defined pipelines
                    item.set_metadata(dict(seed.get("metadata") or {}))
                item.updated_at = _utcnow()
                session.add(item)
                changed = True

            if changed:
                session.commit()

    # ── Query (all from DB) ────────────────────────────────────────────

    def list_by_type(self, provider_type: str, *, enabled_only: bool = False) -> list[ProviderDefinitionModel]:
        with Session(engine) as session:
            query = select(ProviderDefinitionModel).where(ProviderDefinitionModel.provider_type == provider_type)
            if enabled_only:
                query = query.where(ProviderDefinitionModel.enabled == True)  # noqa: E712
            return session.exec(query.order_by(ProviderDefinitionModel.id)).all()

    def get_by_key(self, provider_type: str, provider_key: str) -> ProviderDefinitionModel | None:
        with Session(engine) as session:
            return session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == provider_type)
                .where(ProviderDefinitionModel.provider_key == provider_key)
            ).first()

    def list_driver_templates(self, provider_type: str) -> list[dict]:
        """Read from DB: deduplicate by driver_type, return the list of available driver templates."""
        with Session(engine) as session:
            definitions = session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == provider_type)
                .order_by(ProviderDefinitionModel.is_builtin.desc(), ProviderDefinitionModel.id)
            ).all()
        seen: dict[str, dict] = {}
        for d in definitions:
            dt = d.driver_type or ""
            if dt and dt not in seen:
                seen[dt] = {
                    "provider_type": d.provider_type,
                    "provider_key": d.provider_key,
                    "driver_type": dt,
                    "label": d.label,
                    "description": d.description,
                    "default_auth_mode": d.default_auth_mode,
                    "auth_modes": d.get_auth_modes(),
                    "fields": d.get_fields(),
                }
        return list(seen.values())

    def _get_driver_defaults(self, provider_type: str, driver_type: str) -> dict | None:
        """Find existing definitions with the same driver_type from DB as a template."""
        with Session(engine) as session:
            ref = session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == provider_type)
                .where(ProviderDefinitionModel.driver_type == driver_type)
                .order_by(ProviderDefinitionModel.is_builtin.desc(), ProviderDefinitionModel.id)
            ).first()
            if not ref:
                return None
            return {
                "default_auth_mode": ref.default_auth_mode,
                "auth_modes": ref.get_auth_modes(),
                "fields": ref.get_fields(),
            }

    # ── Write ────────────────────────────────────────────────────────

    def save(
        self,
        *,
        definition_id: int | None,
        provider_type: str,
        provider_key: str,
        label: str,
        description: str,
        driver_type: str,
        enabled: bool,
        default_auth_mode: str = "",
        metadata: dict | None = None,
    ) -> ProviderDefinitionModel:
        defaults = self._get_driver_defaults(provider_type, driver_type)

        with Session(engine) as session:
            if definition_id:
                item = session.get(ProviderDefinitionModel, definition_id)
                if not item:
                    raise ValueError("Provider definition does not exist")
            else:
                item = session.exec(
                    select(ProviderDefinitionModel)
                    .where(ProviderDefinitionModel.provider_type == provider_type)
                    .where(ProviderDefinitionModel.provider_key == provider_key)
                ).first()
                if not item:
                    item = ProviderDefinitionModel(
                        provider_type=provider_type,
                        provider_key=provider_key,
                    )
                    item.created_at = _utcnow()

            item.provider_type = provider_type
            item.provider_key = provider_key
            item.label = label or provider_key
            item.description = description or ""
            item.driver_type = driver_type
            item.default_auth_mode = default_auth_mode or item.default_auth_mode or (defaults.get("default_auth_mode", "") if defaults else "")
            item.enabled = bool(enabled)
            if not item.get_auth_modes() and defaults:
                item.set_auth_modes(list(defaults.get("auth_modes") or []))
            if not item.get_fields() and defaults:
                item.set_fields(list(defaults.get("fields") or []))
            item.set_metadata(dict(metadata or {}))
            item.updated_at = _utcnow()
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def delete(self, definition_id: int) -> bool:
        with Session(engine) as session:
            item = session.get(ProviderDefinitionModel, definition_id)
            if not item:
                return False
            has_settings = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == item.provider_type)
                .where(ProviderSettingModel.provider_key == item.provider_key)
            ).first()
            if has_settings:
                raise ValueError("Please delete the corresponding provider configuration before deleting the definition")
            session.delete(item)
            session.commit()
            return True
