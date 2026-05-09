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
        "label": "CF Worker（自建域名）",
        "description": "基于 Cloudflare Worker 的自定义域名邮箱，需自行部署 Worker 后端",
        "driver_type": "cfworker_admin_api",
        "default_auth_mode": "token",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "token", "label": "Token 认证"}],
        "fields": [
            {"key": "cfworker_api_url", "label": "API 地址", "placeholder": "https://your-worker.example.com", "category": "connection"},
            {"key": "cfworker_admin_token", "label": "Admin Token", "secret": True, "category": "auth"},
            {"key": "cfworker_domain", "label": "邮箱域名", "placeholder": "example.com", "category": "connection"},
            {"key": "cfworker_fingerprint", "label": "指纹标识（可选）", "placeholder": "", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "moemail_api",
        "label": "MoeMail（sall.cc）",
        "description": "自部署临时邮箱，支持自动注册账号或手动登录已有账号",
        "driver_type": "moemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [
            {"value": "password", "label": "账号密码"},
            {"value": "token", "label": "Session Token"},
        ],
        "fields": [
            {"key": "moemail_api_url", "label": "API 地址", "placeholder": "https://moemail.example.com", "category": "connection"},
            {"key": "moemail_username", "label": "用户名（可选）", "category": "auth"},
            {"key": "moemail_password", "label": "密码（可选）", "secret": True, "category": "auth"},
            {"key": "moemail_session_token", "label": "Session Token（可选）", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_lol_api",
        "label": "TempMail.lol",
        "description": "免费临时邮箱，开箱即用，无需任何配置",
        "driver_type": "tempmail_lol_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "tempmail_web_api",
        "label": "Temp-Mail.org",
        "description": "免费临时邮箱，需要浏览器环境（Camoufox）",
        "driver_type": "tempmail_web_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "tempmail_web_base_url", "label": "API 地址（可选）", "placeholder": "https://web2.temp-mail.org", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "duckmail_api",
        "label": "DuckMail（自动生成）",
        "description": "自部署邮箱服务，通过 API 自动生成临时邮箱",
        "driver_type": "duckmail_api",
        "default_auth_mode": "bearer",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "bearer", "label": "Bearer Token"}],
        "fields": [
            {"key": "duckmail_api_url", "label": "API 地址", "placeholder": "https://duckmail.example.com", "category": "connection"},
            {"key": "duckmail_provider_url", "label": "Provider URL（可选）", "placeholder": "", "category": "connection"},
            {"key": "duckmail_bearer", "label": "Bearer Token", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "freemail_api",
        "label": "FreeMail（自动生成）",
        "description": "自部署邮箱服务，支持账号密码或 Admin Token 认证",
        "driver_type": "freemail_api",
        "default_auth_mode": "password",
        "enabled": True,
        "category": "selfhost",
        "auth_modes": [{"value": "password", "label": "账号密码"}, {"value": "token", "label": "Admin Token"}],
        "fields": [
            {"key": "freemail_api_url", "label": "API 地址", "placeholder": "https://freemail.example.com", "category": "connection"},
            {"key": "freemail_admin_token", "label": "Admin Token", "secret": True, "category": "auth"},
            {"key": "freemail_username", "label": "用户名", "category": "auth"},
            {"key": "freemail_password", "label": "密码", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "testmail_api",
        "label": "Testmail（namespace 邮箱）",
        "description": "Testmail.app 第三方服务，通过 API Key 和 Namespace 自动拼接邮箱",
        "driver_type": "testmail_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "testmail_api_url", "label": "API 地址（可选）", "placeholder": "https://api.testmail.app", "category": "connection"},
            {"key": "testmail_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "testmail_namespace", "label": "Namespace", "category": "identity"},
            {"key": "testmail_tag_prefix", "label": "Tag 前缀（可选）", "placeholder": "", "category": "identity"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "luckmail_api",
        "label": "LuckMail（创单接码）",
        "description": "LuckMail 第三方服务，通过创建订单分配邮箱并轮询验证码",
        "driver_type": "luckmail_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "luckmail_api_url", "label": "API 地址", "placeholder": "https://your-domain.com", "category": "connection"},
            {"key": "luckmail_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "luckmail_project_code", "label": "项目编码", "placeholder": "twitter", "category": "identity"},
            {"key": "luckmail_email_type", "label": "邮箱类型（可选）", "placeholder": "ms_graph", "category": "identity"},
            {"key": "luckmail_domain", "label": "域名（可选）", "placeholder": "outlook.com", "category": "identity"},
            {"key": "luckmail_variant_mode", "label": "谷歌变种模式（可选）", "placeholder": "dot / plus / mixed / all", "category": "identity"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "laoudo_api",
        "label": "Laoudo（固定邮箱）",
        "description": "laoudo.com 固定域名邮箱，使用已有邮箱地址接收验证码",
        "driver_type": "laoudo_api",
        "default_auth_mode": "token",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "token", "label": "JWT Token"}],
        "fields": [
            {"key": "laoudo_auth", "label": "Auth Token", "secret": True, "category": "auth"},
            {"key": "laoudo_email", "label": "邮箱地址", "placeholder": "your@email.com", "category": "identity"},
            {"key": "laoudo_account_id", "label": "Account ID", "category": "identity"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "aitre_api",
        "label": "Aitre 临时邮箱",
        "description": "mail.aitre.cc 免费临时邮箱，需指定一个固定邮箱地址",
        "driver_type": "aitre_api",
        "default_auth_mode": "",
        "enabled": True,
        "category": "free",
        "auth_modes": [],
        "fields": [
            {"key": "aitre_email", "label": "邮箱地址", "placeholder": "your@email.com", "category": "identity"},
            {"key": "aitre_api_url", "label": "API 地址（可选）", "placeholder": "https://mail.aitre.cc/api/tempmail", "category": "connection"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "ddg_email",
        "label": "DuckDuckGo Email",
        "description": "DuckDuckGo Email Protection，生成 @duck.com 别名，通过 IMAP 从转发邮箱读取验证码",
        "driver_type": "ddg_email",
        "default_auth_mode": "bearer",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "bearer", "label": "Bearer Token"}],
        "fields": [
            {"key": "ddg_bearer", "label": "DDG Bearer Token", "secret": True, "category": "auth"},
            {"key": "ddg_imap_host", "label": "IMAP 服务器（可选）", "placeholder": "自动推断", "category": "connection"},
            {"key": "ddg_imap_user", "label": "IMAP 用户名（转发邮箱）", "placeholder": "your@gmail.com", "category": "auth"},
            {"key": "ddg_imap_pass", "label": "IMAP 密码", "secret": True, "category": "auth"},
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "local_ms_pool",
        "label": "本地微软邮箱池",
        "description": "导入心蓝邮箱助手通用格式账号池，优先使用 Client Id + 刷新令牌通过 Microsoft Graph 收验证码",
        "driver_type": "local_ms_pool",
        "default_auth_mode": "pool",
        "enabled": True,
        "category": "custom",
        "auth_modes": [{"value": "pool", "label": "账号池"}],
        "fields": [
            {
                "key": "local_ms_pool_file",
                "label": "账号池文件路径",
                "placeholder": "/Users/you/ms-mail-pool.txt",
                "category": "connection",
                "hint": "可选；每行一条心蓝邮箱助手通用格式。配置文件路径后无需把账号明文粘贴到设置页。",
            },
            {
                "key": "local_ms_pool_text",
                "label": "账号池文本",
                "type": "textarea",
                "category": "auth",
                "hint": "可选；直接粘贴心蓝邮箱助手通用格式。支持逗号、中文逗号、TAB、---- 分隔。",
            },
            {
                "key": "local_ms_graph_scope",
                "label": "Graph Scope",
                "placeholder": "https://graph.microsoft.com/Mail.Read offline_access",
                "category": "connection",
            },
            {
                "key": "local_ms_pool_state_file",
                "label": "占用状态文件",
                "placeholder": "默认 data/.local_ms_mailbox_pool_state.json",
                "category": "connection",
                "hint": "用于避免同一个邮箱被重复分配；清空该文件可重置账号池占用状态。",
            },
            {
                "key": "local_ms_pool_allow_reuse",
                "label": "允许重复使用邮箱",
                "type": "toggle",
                "category": "connection",
                "hint": "测试时可开启；批量注册建议关闭。",
            },
        ],
    },
    {
        "provider_type": "mailbox",
        "provider_key": "generic_http_mailbox",
        "label": "通用 HTTP 邮箱",
        "description": "通过配置 HTTP 端点和认证方式对接任意邮箱 API，适合高级用户",
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
        "description": "YesCaptcha 云端验证码识别服务，支持 Turnstile 与 CloudFlare5s",
        "driver_type": "yescaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "yescaptcha_key", "label": "Client Key", "secret": True, "category": "auth"},
            {
                "key": "yescaptcha_api_host",
                "label": "API Host（可选）",
                "placeholder": "https://api.yescaptcha.com",
                "category": "connection",
            },
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
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "twocaptcha_key", "label": "API Key", "secret": True},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "ezcaptcha_api",
        "label": "EZ-Captcha",
        "description": "EZ-Captcha 云端验证码识别服务，支持 Turnstile 与 CloudFlare5s",
        "driver_type": "ezcaptcha_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "ezcaptcha_key", "label": "Client Key", "secret": True, "category": "auth"},
            {"key": "ezcaptcha_api_host", "label": "API Host（可选）", "placeholder": "https://api.ez-captcha.com", "category": "connection"},
        ],
    },
    {
        "provider_type": "captcha",
        "provider_key": "captcharun_api",
        "label": "CaptchaRun",
        "description": "CaptchaRun 验证码服务（支持 CloudFlare5s，建议作为5秒盾专用 provider）",
        "driver_type": "captcharun_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "captcharun_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "captcharun_api_host", "label": "API Host（可选）", "placeholder": "https://api.captcha-run.com", "category": "connection"},
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
        "category": "thirdparty",
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
        "category": "thirdparty",
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
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "herosms_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "herosms_default_country", "label": "默认国家", "type": "async-select", "asyncUrl": "/sms/herosms/countries", "asyncValueKey": "id", "asyncLabelKey": "chn", "placeholder": "请选择国家..."},
            {"key": "herosms_default_service", "label": "默认服务", "type": "async-select", "asyncUrl": "/sms/herosms/services", "asyncValueKey": "code", "asyncLabelKey": "name", "placeholder": "请选择服务..."},
            {"key": "herosms_max_price", "label": "最大价格 (可选)", "placeholder": "-1"},
            {"key": "herosms_auto_country", "label": "自动选择最优国家", "type": "toggle", "hint": "启用后忽略默认国家，自动选择价格最低且库存充足的国家"},
            {"key": "herosms_auto_country_min_stock", "label": "自动选国最低库存", "placeholder": "20"},
            {"key": "herosms_auto_country_max_price", "label": "自动选国最高价格", "placeholder": "0 (不限)"},
            {"key": "register_phone_extra_max", "label": "号码复用额外上限", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "复用号码至最大", "type": "toggle"},
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
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "sms_activate_api_key", "label": "API Key", "secret": True},
            {"key": "sms_activate_default_country", "label": "默认国家代码", "placeholder": "ru"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "smsbower_api",
        "label": "SMSBower",
        "description": "SMSBower 接码平台，API 兼容 HeroSMS，支持号码复用和自动重发",
        "driver_type": "smsbower_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "smsbower_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "smsbower_default_country", "label": "默认国家", "type": "async-select", "asyncUrl": "/sms/smsbower/countries", "asyncValueKey": "id", "asyncLabelKey": "chn", "placeholder": "请选择国家..."},
            {"key": "smsbower_default_service", "label": "默认服务", "type": "async-select", "asyncUrl": "/sms/smsbower/services", "asyncValueKey": "code", "asyncLabelKey": "name", "placeholder": "请选择服务..."},
            {"key": "smsbower_max_price", "label": "最大价格 (可选)", "placeholder": "-1"},
            {"key": "smsbower_auto_country", "label": "自动选择最优国家", "type": "toggle", "hint": "启用后忽略默认国家，自动选择价格最低且库存充足的国家"},
            {"key": "register_phone_extra_max", "label": "号码复用额外上限", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "复用号码至最大", "type": "toggle"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "grizzlysms_api",
        "label": "GrizzlySMS",
        "description": "GrizzlySMS 接码平台，API 兼容 HeroSMS，支持国家/项目选择",
        "driver_type": "grizzlysms_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "grizzlysms_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {"key": "grizzlysms_default_service", "label": "默认项目", "type": "async-select", "asyncUrl": "/sms/grizzlysms/services", "asyncValueKey": "code", "asyncLabelKey": "name", "placeholder": "请选择项目..."},
            {
                "key": "grizzlysms_default_country",
                "label": "默认国家",
                "type": "async-select",
                "asyncUrl": "/sms/grizzlysms/countries_with_prices",
                "asyncDependsOn": "grizzlysms_default_service",
                "asyncQueryParam": "service",
                "asyncValueKey": "id",
                "asyncLabelKey": "chn",
                "placeholder": "请选择国家（会随项目展示价格）...",
            },
            {"key": "grizzlysms_max_price", "label": "最大价格 (可选)", "placeholder": "-1"},
            {"key": "register_phone_extra_max", "label": "号码复用额外上限", "placeholder": "3"},
            {"key": "register_reuse_phone_to_max", "label": "复用号码至最大", "type": "toggle"},
        ],
    },
    {
        "provider_type": "sms",
        "provider_key": "fivesim_api",
        "label": "5sim",
        "description": "5sim 接码平台（Bearer Token），支持国家/运营商/项目选择",
        "driver_type": "fivesim_api",
        "default_auth_mode": "apikey",
        "enabled": True,
        "category": "thirdparty",
        "auth_modes": [{"value": "apikey", "label": "API Key"}],
        "fields": [
            {"key": "fivesim_api_key", "label": "API Key", "secret": True, "category": "auth"},
            {
                "key": "fivesim_default_product",
                "label": "默认项目(product)",
                "type": "async-select",
                "asyncUrl": "/sms/fivesim/products",
                "asyncValueKey": "code",
                "asyncLabelKey": "name",
                "placeholder": "请选择项目...",
            },
            {
                "key": "fivesim_default_country",
                "label": "默认国家",
                "type": "async-select",
                "asyncUrl": "/sms/fivesim/countries_with_prices",
                "asyncDependsOn": "fivesim_default_product",
                "asyncQueryParam": "product",
                "asyncValueKey": "code",
                "asyncLabelKey": "name",
                "placeholder": "请选择国家（会随项目展示价格）...",
            },
            {
                "key": "fivesim_default_operator",
                "label": "默认运营商",
                "placeholder": "any",
                "hint": "5sim operator，默认 any（自动选择）。当前国家列表价格为该国最低价(跨运营商)。",
            },
            {"key": "register_phone_extra_max", "label": "号码复用额外上限", "placeholder": "3", "hint": "一个号码最多用于多少个账号（默认 3）"},
            {"key": "register_reuse_phone_to_max", "label": "复用号码至最大", "type": "toggle", "hint": "开启后同一 activation 会复用直到到达上限"},
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
        "category": "thirdparty",
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
        "category": "thirdparty",
        "auth_modes": [],
        "fields": [
            {"key": "proxy_gateway_url", "label": "网关地址", "placeholder": "http://user:pass@gate.example.com:7777"},
        ],
    },
]


class ProviderDefinitionsRepository:

    def ensure_seeded(self) -> None:
        """将内置 provider definition 种子数据写入数据库。

        新增的插入，已存在的更新字段定义（label、description、fields 等），
        确保代码升级后内置 provider 的元数据能同步到数据库。
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
                    # 新增
                    item = ProviderDefinitionModel(
                        provider_type=seed["provider_type"],
                        provider_key=seed["provider_key"],
                        created_at=_utcnow(),
                    )
                    logger.info("种子数据: 新增 %s/%s", seed["provider_type"], seed["provider_key"])

                # 更新元数据（每次启动都同步，确保代码变更生效）
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
                    # 只在 metadata 为空时写入种子值，避免覆盖用户自定义的 pipeline
                    item.set_metadata(dict(seed.get("metadata") or {}))
                item.updated_at = _utcnow()
                session.add(item)
                changed = True

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
