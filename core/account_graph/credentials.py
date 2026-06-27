from __future__ import annotations

from typing import Any

from core.account_graph.overview import (
    NON_LEGACY_EXTRA_KEYS,
    PLATFORM_CREDENTIAL_TYPES,
    PRIMARY_TOKEN_WRITE_KEYS,
    _safe_dict,
    _safe_list,
    _text,
)


def _infer_credential_type(key: str) -> str:
    if key in PLATFORM_CREDENTIAL_TYPES:
        return PLATFORM_CREDENTIAL_TYPES[key]
    lower = key.lower()
    if "cookie" in lower:
        return "cookie"
    if "token" in lower:
        return "token"
    if "secret" in lower:
        return "secret"
    if "client" in lower or "workspace" in lower or lower.endswith("_id"):
        return "identifier"
    return "credential"


def _default_primary_token_key(platform: str) -> str:
    return PRIMARY_TOKEN_WRITE_KEYS.get(platform, "legacy_token")


def _legacy_extra_payload(extra: dict[str, Any]) -> dict[str, Any]:
    legacy_extra = {
        key: value
        for key, value in extra.items()
        if key not in PLATFORM_CREDENTIAL_TYPES
        and key not in NON_LEGACY_EXTRA_KEYS
        and value not in (None, "", [], {})
    }
    return legacy_extra


def _platform_credentials_from_extra(extra: dict[str, Any], *, legacy_token: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(key: str, value: Any, *, source: str) -> None:
        text = _text(value)
        if not text or key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "scope": "platform",
                "provider_name": _text(extra.get("platform")) or "",
                "credential_type": _infer_credential_type(key),
                "key": key,
                "value": text,
                "is_primary": False,
                "source": source,
                "metadata": {},
            }
        )

    if legacy_token:
        push("legacy_token", legacy_token, source="accounts.token")
    for key in PLATFORM_CREDENTIAL_TYPES:
        if key in extra:
            push(key, extra.get(key), source="accounts.extra")

    primary_key = _default_primary_token_key(_text(extra.get("platform")))
    if any(item["key"] == primary_key for item in rows):
        for item in rows:
            item["is_primary"] = item["key"] == primary_key
    elif rows:
        token_keys = [item["key"] for item in rows if item["credential_type"] == "token"]
        primary = token_keys[0] if token_keys else rows[0]["key"]
        for item in rows:
            item["is_primary"] = item["key"] == primary
    return rows


def _normalize_platform_credentials(
    platform: str,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for raw in items:
        key = _text(raw.get("key"))
        value = raw.get("value")
        if not key or value in (None, ""):
            continue
        normalized[key] = {
            "scope": "platform",
            "provider_name": platform,
            "credential_type": _text(raw.get("credential_type")) or _infer_credential_type(key),
            "key": key,
            "value": _text(value),
            "is_primary": bool(raw.get("is_primary")),
            "source": _text(raw.get("source")),
            "metadata": _safe_dict(raw.get("metadata")),
        }

    primary_key = next((key for key, item in normalized.items() if item.get("is_primary")), "")
    if not primary_key:
        preferred = _default_primary_token_key(platform)
        if preferred in normalized:
            primary_key = preferred
        else:
            primary_key = next(
                (
                    key
                    for key, item in normalized.items()
                    if item.get("credential_type") == "token"
                ),
                "",
            )
    if primary_key:
        for key, item in normalized.items():
            item["is_primary"] = key == primary_key
    return list(normalized.values())


def _merge_platform_credentials(
    platform: str,
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    *,
    prefer_existing: bool,
) -> list[dict[str, Any]]:
    if prefer_existing:
        merged = list(incoming) + list(existing)
    else:
        merged = list(existing) + list(incoming)
    return _normalize_platform_credentials(platform, merged)


def _provider_accounts_from_extra(extra: dict[str, Any]) -> list[dict[str, Any]]:
    items = _safe_list(extra.get("provider_accounts"))
    identity = _safe_dict(extra.get("identity"))
    if isinstance(identity.get("provider_account"), dict):
        items.append(identity["provider_account"])
    identity_mailbox = _safe_dict(identity.get("mailbox"))
    if identity_mailbox:
        items.append(
            {
                "provider_type": "mailbox",
                "provider_name": identity_mailbox.get("provider"),
                "login_identifier": identity_mailbox.get("email"),
                "display_name": identity_mailbox.get("email"),
                "metadata": {"account_id": identity_mailbox.get("account_id")},
            }
        )

    mailbox = _safe_dict(extra.get("verification_mailbox"))
    if mailbox:
        items.append(
            {
                "provider_type": "mailbox",
                "provider_name": mailbox.get("provider"),
                "login_identifier": mailbox.get("email"),
                "display_name": mailbox.get("email"),
                "metadata": {"account_id": mailbox.get("account_id")},
            }
        )

    normalized: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in items:
        item = _safe_dict(raw)
        provider_type = _text(item.get("provider_type") or "mailbox") or "mailbox"
        provider_name = _text(item.get("provider_name") or item.get("provider"))
        login_identifier = _text(item.get("login_identifier") or item.get("email") or item.get("username"))
        display_name = _text(item.get("display_name") or login_identifier or provider_name)
        credentials = _safe_dict(item.get("credentials"))
        metadata = _safe_dict(item.get("metadata"))
        for field in ("email", "username", "account_id", "api_url", "login_url", "auth_type"):
            text = _text(item.get(field))
            if text and field not in metadata:
                metadata[field] = text
        key = (provider_type, provider_name, login_identifier)
        existing = normalized.get(key)
        if existing:
            existing["credentials"].update({k: v for k, v in credentials.items() if _text(v)})
            existing["metadata"].update(
                {k: v for k, v in metadata.items() if _text(v) or isinstance(v, (dict, list))}
            )
        else:
            normalized[key] = {
                "provider_type": provider_type,
                "provider_name": provider_name,
                "login_identifier": login_identifier,
                "display_name": display_name,
                "credentials": {k: v for k, v in credentials.items() if _text(v)},
                "metadata": metadata,
            }
    return list(normalized.values())


def _provider_resources_from_extra(extra: dict[str, Any]) -> list[dict[str, Any]]:
    items = _safe_list(extra.get("provider_resources"))
    identity = _safe_dict(extra.get("identity"))
    if isinstance(identity.get("provider_resource"), dict):
        items.append(identity["provider_resource"])
    identity_mailbox = _safe_dict(identity.get("mailbox"))
    if identity_mailbox:
        items.append(
            {
                "provider_type": "mailbox",
                "provider_name": identity_mailbox.get("provider"),
                "resource_type": "mailbox",
                "resource_identifier": identity_mailbox.get("account_id"),
                "handle": identity_mailbox.get("email"),
                "display_name": identity_mailbox.get("email"),
                "metadata": {
                    "account_id": identity_mailbox.get("account_id"),
                    "email": identity_mailbox.get("email"),
                },
            }
        )
    mailbox = _safe_dict(extra.get("verification_mailbox"))
    if mailbox:
        items.append(
            {
                "provider_type": "mailbox",
                "provider_name": mailbox.get("provider"),
                "resource_type": "mailbox",
                "resource_identifier": mailbox.get("account_id"),
                "handle": mailbox.get("email"),
                "display_name": mailbox.get("email"),
                "metadata": {
                    "account_id": mailbox.get("account_id"),
                    "email": mailbox.get("email"),
                },
            }
        )

    normalized: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for raw in items:
        item = _safe_dict(raw)
        provider_type = _text(item.get("provider_type") or "mailbox") or "mailbox"
        provider_name = _text(item.get("provider_name") or item.get("provider"))
        resource_type = _text(item.get("resource_type") or "resource") or "resource"
        resource_identifier = _text(
            item.get("resource_identifier")
            or item.get("account_id")
            or item.get("external_id")
            or item.get("id")
        )
        handle = _text(item.get("handle") or item.get("email") or item.get("address"))
        display_name = _text(item.get("display_name") or handle or resource_identifier)
        metadata = _safe_dict(item.get("metadata"))
        for field in ("email", "account_id", "address", "api_url"):
            text = _text(item.get(field))
            if text and field not in metadata:
                metadata[field] = text
        key = (provider_type, provider_name, resource_type, resource_identifier or handle)
        normalized[key] = {
            "provider_type": provider_type,
            "provider_name": provider_name,
            "resource_type": resource_type,
            "resource_identifier": resource_identifier,
            "handle": handle,
            "display_name": display_name,
            "metadata": metadata,
        }
    return list(normalized.values())


def _merge_provider_accounts(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    *,
    prefer_existing: bool,
) -> list[dict[str, Any]]:
    if prefer_existing:
        return _provider_accounts_from_extra({"provider_accounts": list(incoming) + list(existing)})
    return _provider_accounts_from_extra({"provider_accounts": list(existing) + list(incoming)})


def _merge_provider_resources(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    *,
    prefer_existing: bool,
) -> list[dict[str, Any]]:
    if prefer_existing:
        return _provider_resources_from_extra({"provider_resources": list(incoming) + list(existing)})
    return _provider_resources_from_extra({"provider_resources": list(existing) + list(incoming)})
