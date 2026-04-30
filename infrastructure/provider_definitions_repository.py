from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from core.db import ProviderDefinitionModel, ProviderSettingModel, engine

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_BUILTIN_DEFINITIONS: list[dict] = [
    # ── mailbox ──────────────────────────────────────────────────────
    {
        "provider_type": "mailbox",
        "provider_key": "cfworker_admin_api",
        "label": "CFWorker 邮箱",
        "description": "基于 Cloudflare Worker 的自定义域名邮箱服务，需部署 CFWorker 后端并配置 Admin Token",
        "driver_type": "cfworker_admin_api",
        "default_auth_mode": "token",
        "enabled": True,
        "auth_modes": [{"value": "token", "label": "Token 认证"}],
        "fields": [
            {"key": "cfworker_api_url", "label": "API 地址", "placeholder": "https://your-worker.example.com"},
            {"key": "cfworker_admin_token", "label": "Admin Token", "secret": True},
            {"key": "cfworker_domain", "label": "邮箱域名", "placeholder": "example.com"},
            {"key": "cfworker_fingerprint", "label": "指纹标识 (可选)", "placeholder": ""},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "moemail_api",
        "label": "MoeMail 邮箱",
        "description": "MoeMail 自部署临时邮箱服务，支持自动注册和手动登录",
        "driver_type": "moemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "auth_modes": [
            {"value": "password", "label": "账号密码"},
            {"value": "token", "label": "Session Token"},
        ],
        "fields": [
            {"key": "moemail_api_url", "label": "API 地址", "placeholder": "https://moemail.example.com"},
            {"key": "moemail_username", "label": "用户名"},
            {"key": "moemail_password", "label": "密码", "secret": True},
            {"key": "moemail_session_token", "label": "Session Token (可选)", "secret": True},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_lol_api",
        "label": "TempMail.lol 邮箱",
        "description": "TempMail.lol 免费临时邮箱，无需配置即可使用（自动生成邮箱地址）",
        "driver_type": "tempmail_lol_api",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_web_api",
        "label": "Temp-Mail.org 邮箱",
        "description": "基于 temp-mail.org 的临时邮箱服务，无需注册",
        "driver_type": "tempmail_web_api",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [
            {"key": "tempmail_web_base_url", "label": "API 地址 (可选)", "placeholder": "https://web2.temp-mail.org"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "duckmail_api",
        "label": "DuckMail 邮箱",
        "description": "DuckMail 自部署邮箱服务，需配置 API 地址和 Bearer Token",
        "driver_type": "duckmail_api",
        "default_auth_mode": "bearer",
        "enabled": True,
        "auth_modes": [{"value": "bearer", "label": "Bearer Token"}],
        "fields": [
            {"key": "duckmail_api_url", "label": "API 地址", "placeholder": "https://duckmail.example.com"},
            {"key": "duckmail_provider_url", "label": "Provider URL (可选)", "placeholder": ""},
            {"key": "duckmail_bearer", "label": "Bearer Token", "secret": True},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "freemail_api",
        "label": "FreeMail 邮箱",
        "description": "FreeMail 自部署邮箱服务，需配置 API 地址和管理员 Token",
        "driver_type": "freemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "auth_modes": [{"value": "password", "label": "账号密码"}, {"value": "token", "label": "Admin Token"}],
        "fields": [
            {"key": "freemail_api_url", "label": "API 地址", "placeholder": "https://freemail.example.com"},
            {"key": "freemail_admin_token", "label": "Admin Token", "secret": True},
            {"key": "freemail_username", "label": "用户名"},
            {"key": "freemail_password", "label": "密码", "secret": True},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "testmail_api",
        "label": "Testmail.app 邮箱",
        "description": "Testmail.app 邮箱服务，通过 API Key 和 Namespace 管理邮箱",
        "driver_type": "testmail_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "testmail_api_url", "label": "API 地址 (可选)", "placeholder": "https://api.testmail.app"},
            {"key": "testmail_api_key", "label": "API Key", "secret": True},
            {"key": "testmail_namespace", "label": "Namespace"},
            {"key": "testmail_tag_prefix", "label": "Tag 前缀 (可选)", "placeholder": ""},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "laoudo_api",
        "label": "Laoudo 邮箱",
        "description": "laoudo.com 邮箱服务，需配置 Auth Token 和邮箱地址",
        "driver_type": "laoudo_api",
        "default_auth_mode": "token",
        "enabled": True,
        "auth_modes": [{"value": "token", "label": "Token 认证"}],
        "fields": [
            {"key": "laoudo_auth", "label": "Auth Token", "secret": True},
            {"key": "laoudo_email", "label": "邮箱地址", "placeholder": "your@email.com"},
            {"key": "laoudo_account_id", "label": "Account ID"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "aitre_api",
        "label": "Aitre 临时邮箱",
        "description": "mail.aitre.cc 临时邮箱服务，需指定固定邮箱地址",
        "driver_type": "aitre_api",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [
            {"key": "aitre_email", "label": "邮箱地址", "placeholder": "your@email.com"},
            {"key": "aitre_api_url", "label": "API 地址 (可选)", "placeholder": "https://mail.aitre.cc/api/tempmail"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "generic_http_mailbox",
        "label": "通用 HTTP 邮箱",
        "description": "数据驱动的通用 HTTP 邮箱驱动，所有端点和认证通过配置描述，零代码新增邮箱类型",
        "driver_type": "generic_http_mailbox",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [],
    },
    # ── captcha ──────────────────────────────────────────────────────
    {
        "provider_type": "captcha",
        "provider_key": "yescaptcha_api",
        "label": "YesCaptcha",
        "description": "YesCaptcha 云端验证码识别服务，支持 Turnstile 等类型",
        "driver_type": "yescaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "yescaptcha_key", "label": "Client Key", "secret": True},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "twocaptcha_api",
        "label": "2Captcha",
        "description": "2Captcha 云端验证码识别服务，支持 Turnstile 等类型",
        "driver_type": "twocaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "twocaptcha_key", "label": "API Key", "secret": True},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "local_solver",
        "label": "本地验证码求解器",
        "description": "调用本地 api_solver 服务（Camoufox/patchright）解 Turnstile 验证码",
        "driver_type": "local_solver",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [
            {"key": "solver_url", "label": "Solver 地址", "placeholder": "http://localhost:8889"},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "manual",
        "label": "人工打码",
        "description": "阻塞等待用户手动输入验证码，适用于调试场景",
        "driver_type": "manual",
        "default_auth_mode": "",
        "enabled": True,
        "auth_modes": [],
        "fields": [],
    },
    # ── sms ──────────────────────────────────────────────────────────
    {
        "provider_type": "sms",
        "provider_key": "herosms_api",
        "label": "HeroSMS",
        "description": "HeroSMS 接码平台，支持号码复用和自动重发",
        "driver_type": "herosms_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "herosms_api_key", "label": "API Key", "secret": True},
            {"key": "herosms_default_country", "label": "默认国家代码", "placeholder": "187 (美国)"},
            {"key": "herosms_default_service", "label": "默认服务代码", "placeholder": "dr"},
            {"key": "herosms_max_price", "label": "最大价格 (可选)", "placeholder": "-1"},
            {"key": "register_phone_extra_max", "label": "号码复用额外上限", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "复用号码至最大", "placeholder": "true"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "sms_activate_api",
        "label": "SMS-Activate",
        "description": "SMS-Activate 接码平台 (sms-activate.guru)",
        "driver_type": "sms_activate_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "sms_activate_api_key", "label": "API Key", "secret": True},
            {"key": "sms_activate_default_country", "label": "默认国家代码", "placeholder": "ru"},
        ],
    },
    # ── proxy ────────────────────────────────────────────────────────
    {
        "provider_type": "proxy",
        "provider_key": "api_extract",
        "label": "API 提取代理",
        "description": "通过 HTTP API 动态提取代理 IP 列表，适用于大多数代理商的 API 提取接口",
        "driver_type": "api_extract",
        "default_auth_mode": "",
        "enabled": False,
        "auth_modes": [],
        "fields": [
            {"key": "proxy_api_url", "label": "API 地址", "placeholder": "https://provider.com/api/get_proxy?key=xxx"},
            {"key": "proxy_protocol", "label": "协议", "placeholder": "http / socks5"},
            {"key": "proxy_username", "label": "用户名 (可选)"},
            {"key": "proxy_password", "label": "密码 (可选)", "secret": True},
        ],
    },
    {
        "provider_type": "proxy",
        "provider_key": "rotating_gateway",
        "label": "旋转网关代理",
        "description": "固定入口地址，每次请求自动分配不同出口 IP，适用于 BrightData / Oxylabs / IPRoyal 等",
        "driver_type": "rotating_gateway",
        "default_auth_mode": "",
        "enabled": False,
        "auth_modes": [],
        "fields": [
            {"key": "proxy_gateway_url", "label": "网关地址", "placeholder": "http://user:pass@gate.example.com:7777"},
        ],
    },
]


class ProviderDefinitionsRepository:

    def ensure_seeded(self) -> None:
        """将内置 provider definition 种子数据写入数据库（仅插入不更新）。"""
        with Session(engine) as session:
            existing_keys: set[str] = set()
            for row in session.exec(select(ProviderDefinitionModel)).all():
                key = f"{row.provider_type}::{row.provider_key}"
                existing_keys.add(key)

            changed = False
            for seed in _BUILTIN_DEFINITIONS:
                key = f"{seed['provider_type']}::{seed['provider_key']}"
                if key in existing_keys:
                    continue
                item = ProviderDefinitionModel(
                    provider_type=seed["provider_type"],
                    provider_key=seed["provider_key"],
                    label=seed.get("label", seed["provider_key"]),
                    description=seed.get("description", ""),
                    driver_type=seed.get("driver_type", seed["provider_key"]),
                    default_auth_mode=seed.get("default_auth_mode", ""),
                    enabled=seed.get("enabled", True),
                    is_builtin=True,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                item.set_auth_modes(list(seed.get("auth_modes") or []))
                item.set_fields(list(seed.get("fields") or []))
                item.set_metadata(dict(seed.get("metadata") or {}))
                session.add(item)
                changed = True
                logger.info("种子数据: 新增 provider definition %s/%s", seed["provider_type"], seed["provider_key"])

            if changed:
                session.commit()

    # ── 查询（全部从 DB） ────────────────────────────────────────────

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
        """从 DB 读取：按 driver_type 去重，返回可用驱动模板列表。"""
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
        """从 DB 中查找同 driver_type 的已有 definition 作为模板。"""
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

    # ── 写入 ────────────────────────────────────────────────────────

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
                    raise ValueError("provider definition 不存在")
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
                raise ValueError("请先删除对应 provider 配置，再删除 definition")
            session.delete(item)
            session.commit()
            return True
