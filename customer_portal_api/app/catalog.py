from __future__ import annotations


EXECUTOR_LABELS = {
    "protocol": "Protocol Mode",
    "headless": "Headless Browser Automation",
    "headed": "Headed Browser Automation",
}

IDENTITY_MODE_LABELS = {
    "mailbox": "System Mailbox",
    "oauth_browser": "Third-Party Account",
}

OAUTH_PROVIDER_LABELS = {
    "google": "Google",
    "github": "GitHub",
    "microsoft": "Microsoft",
    "linkedin": "LinkedIn",
    "apple": "Apple",
    "x": "X",
    "builderid": "Builder ID",
}

PLATFORM_SEEDS: list[dict] = [
    {
        "platform_code": "chatgpt",
        "display_name": "ChatGPT",
        "version": "1.0.0",
        "supported_executors": ["protocol", "headless", "headed"],
        "supported_identity_modes": ["mailbox", "oauth_browser"],
        "supported_oauth_providers": ["google", "github", "microsoft"],
    },
    {
        "platform_code": "cursor",
        "display_name": "Cursor",
        "version": "1.0.0",
        "supported_executors": ["headless", "headed"],
        "supported_identity_modes": ["oauth_browser"],
        "supported_oauth_providers": ["google", "github"],
    },
    {
        "platform_code": "kiro",
        "display_name": "Kiro",
        "version": "1.0.0",
        "supported_executors": ["headless", "headed"],
        "supported_identity_modes": ["oauth_browser"],
        "supported_oauth_providers": ["google", "github", "builderid"],
    },
    {
        "platform_code": "blink",
        "display_name": "Blink",
        "version": "1.0.0",
        "supported_executors": ["protocol", "headless", "headed"],
        "supported_identity_modes": ["mailbox"],
        "supported_oauth_providers": [],
    },
    {
        "platform_code": "trae",
        "display_name": "Trae",
        "version": "1.0.0",
        "supported_executors": ["headless", "headed"],
        "supported_identity_modes": ["oauth_browser"],
        "supported_oauth_providers": ["google", "github"],
    },
    {
        "platform_code": "tavily",
        "display_name": "Tavily",
        "version": "1.0.0",
        "supported_executors": ["protocol"],
        "supported_identity_modes": ["mailbox"],
        "supported_oauth_providers": [],
    },
    {
        "platform_code": "openblocklabs",
        "display_name": "OpenBlockLabs",
        "version": "1.0.0",
        "supported_executors": ["protocol"],
        "supported_identity_modes": ["mailbox"],
        "supported_oauth_providers": [],
    },
    {
        "platform_code": "grok",
        "display_name": "Grok",
        "version": "1.0.0",
        "supported_executors": ["headless", "headed"],
        "supported_identity_modes": ["oauth_browser"],
        "supported_oauth_providers": ["google", "x"],
    },
    {
        "platform_code": "blackbox",
        "display_name": "Blackbox AI",
        "version": "1.0.0",
        "supported_executors": ["headless", "headed"],
        "supported_identity_modes": ["mailbox", "oauth_browser"],
        "supported_oauth_providers": ["google"],
    },
]

PERMISSION_SEEDS: list[dict] = [
    {"permission_code": "admin:*", "permission_name": "All Admin Permissions"},
    {"permission_code": "admin:user:read", "permission_name": "View Users"},
    {"permission_code": "admin:user:write", "permission_name": "Edit Users"},
    {"permission_code": "admin:platform:read", "permission_name": "View Platforms"},
    {"permission_code": "admin:config:read", "permission_name": "View Config"},
    {"permission_code": "admin:config:write", "permission_name": "Edit Config"},
    {"permission_code": "admin:task:read", "permission_name": "View Tasks"},
    {"permission_code": "admin:account:read", "permission_name": "View Accounts"},
    {"permission_code": "admin:account:write", "permission_name": "Edit Accounts"},
    {"permission_code": "admin:proxy:read", "permission_name": "View Proxies"},
    {"permission_code": "admin:proxy:write", "permission_name": "Edit Proxies"},
    {"permission_code": "admin:order:read", "permission_name": "View Orders"},
    {"permission_code": "admin:subscription:read", "permission_name": "View Subscriptions"},
    {"permission_code": "app:platform:view", "permission_name": "View User Platforms"},
    {"permission_code": "app:task:create", "permission_name": "Create User Tasks"},
    {"permission_code": "app:task:view_self", "permission_name": "View Own Tasks"},
    {"permission_code": "app:order:view_self", "permission_name": "View Own Orders"},
    {"permission_code": "app:order:create", "permission_name": "Create Own Orders"},
    {"permission_code": "app:payment:submit", "permission_name": "Submit Own Payments"},
    {"permission_code": "app:subscription:view_self", "permission_name": "View Own Subscriptions"},
    {"permission_code": "app:profile:view_self", "permission_name": "View Own Profile"},
    {"permission_code": "app:profile:update_self", "permission_name": "Update Own Profile"},
    {"permission_code": "payment:callback", "permission_name": "Payment Callback"},
]

ROLE_SEEDS: list[dict] = [
    {
        "role_code": "admin",
        "role_name": "Administrator",
        "permissions": [
            "admin:*",
            "admin:user:read",
            "admin:user:write",
            "admin:platform:read",
            "admin:config:read",
            "admin:config:write",
            "admin:task:read",
            "admin:account:read",
            "admin:account:write",
            "admin:proxy:read",
            "admin:proxy:write",
            "admin:order:read",
            "admin:subscription:read",
            "payment:callback",
            "app:platform:view",
            "app:task:view_self",
            "app:order:view_self",
            "app:subscription:view_self",
            "app:profile:view_self",
            "app:profile:update_self",
        ],
    },
    {
        "role_code": "user",
        "role_name": "Regular User",
        "permissions": [
            "app:platform:view",
            "app:task:create",
            "app:task:view_self",
            "app:order:view_self",
            "app:order:create",
            "app:payment:submit",
            "app:subscription:view_self",
            "app:profile:view_self",
            "app:profile:update_self",
        ],
    },
]

CONFIG_DEFAULTS: dict[str, str] = {
    "default_executor": "protocol",
    "default_identity_provider": "mailbox",
    "default_oauth_provider": "",
    "oauth_email_hint": "",
    "chrome_user_data_dir": "",
    "chrome_cdp_url": "",
}


def choice_options(values: list[str], labels: dict[str, str]) -> list[dict]:
    return [{"value": value, "label": labels.get(value, value)} for value in values if str(value or "").strip()]


def platform_payload(item: dict) -> dict:
    supported_executors = list(item.get("supported_executors", []) or [])
    supported_identity_modes = list(item.get("supported_identity_modes", []) or [])
    supported_oauth_providers = list(item.get("supported_oauth_providers", []) or [])
    return {
        "name": item["platform_code"],
        "display_name": item["display_name"],
        "version": item.get("version", "1.0.0"),
        "supported_executors": supported_executors,
        "supported_identity_modes": supported_identity_modes,
        "supported_oauth_providers": supported_oauth_providers,
        "supported_executor_options": choice_options(supported_executors, EXECUTOR_LABELS),
        "supported_identity_mode_options": choice_options(supported_identity_modes, IDENTITY_MODE_LABELS),
        "supported_oauth_provider_options": choice_options(supported_oauth_providers, OAUTH_PROVIDER_LABELS),
    }


def collect_platform_choice_options(platforms: list[dict]) -> dict[str, list[dict]]:
    executor_values: list[str] = []
    identity_values: list[str] = []
    oauth_values: list[str] = []
    for item in platforms:
        for value in item.get("supported_executors", []) or []:
            if value not in executor_values:
                executor_values.append(value)
        for value in item.get("supported_identity_modes", []) or []:
            if value not in identity_values:
                identity_values.append(value)
        for value in item.get("supported_oauth_providers", []) or []:
            if value not in oauth_values:
                oauth_values.append(value)
    return {
        "executor_options": choice_options(executor_values, EXECUTOR_LABELS),
        "identity_mode_options": choice_options(identity_values, IDENTITY_MODE_LABELS),
        "oauth_provider_options": choice_options(oauth_values, OAUTH_PROVIDER_LABELS),
    }
