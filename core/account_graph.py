from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from typing import Any

from sqlmodel import Session, delete, select

from core.datetime_utils import ensure_utc_datetime, serialize_datetime
from core.db import (
    AccountCredentialModel,
    AccountModel,
    AccountOverviewModel,
    ProviderAccountModel,
    ProviderResourceModel,
)


PLATFORM_CREDENTIAL_TYPES: dict[str, str] = {
    "legacy_token": "token",
    "access_token": "token",
    "refresh_token": "token",
    "session_token": "token",
    "id_token": "token",
    "client_id": "identifier",
    "client_secret": "secret",
    "workspace_id": "identifier",
    "accessToken": "token",
    "refreshToken": "token",
    "sessionToken": "token",
    "idToken": "token",
    "clientId": "identifier",
    "clientSecret": "secret",
    "workspaceId": "identifier",
    "cookies": "cookie",
    "cookie": "cookie",
    "api_key": "secret",
    "wos_session": "token",
    "sso": "cookie",
    "sso_rw": "cookie",
}

PRIMARY_TOKEN_WRITE_KEYS: dict[str, str] = {
    "cursor": "session_token",
    "chatgpt": "access_token",
    "kiro": "accessToken",
    "trae": "legacy_token",
    "openblocklabs": "wos_session",
}

NON_LEGACY_EXTRA_KEYS = {
    "account_overview",
    "provider_accounts",
    "provider_resources",
    "identity",
    "verification_mailbox",
    "cashier_url",
    "region",
    "trial_end_time",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _preview_secret(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if len(text) <= 10:
        return text
    return f"{text[:6]}...{text[-4:]}"


def _dedupe_chips(*groups: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for item in group or []:
            chip = _text(item)
            if not chip or chip == "本地未切换" or chip in seen:
                continue
            seen.add(chip)
            result.append(chip)
    return result


def _normalize_plan_state(value: Any) -> str:
    raw = _text(value).lower()
    if not raw:
        return ""
    if raw in {"trial", "trialing", "free_trial", "trial-active", "trial_active"}:
        return "trial"
    if raw in {"expired", "cancelled", "canceled", "inactive", "ended"}:
        return "expired"
    if raw in {"free", "basic", "starter", "hobby"}:
        return "free"
    if raw in {"eligible", "trial_eligible"}:
        return "eligible"
    subscribed_hints = (
        "pro",
        "plus",
        "premium",
        "paid",
        "student",
        "team",
        "business",
        "enterprise",
        "member",
    )
    if any(token in raw for token in subscribed_hints):
        return "subscribed"
    return raw


def _derive_plan_name(overview: dict[str, Any]) -> str:
    return _text(
        overview.get("plan_name")
        or overview.get("plan")
        or overview.get("membership_type")
        or overview.get("individual_membership_type")
    )


def _derive_validity_status(lifecycle_status: str, overview: dict[str, Any]) -> str:
    if lifecycle_status == "invalid":
        return "invalid"
    if "valid" in overview:
        return "valid" if bool(overview.get("valid")) else "invalid"
    return "unknown"


def next_lifecycle_status_after_validity_check(current_lifecycle_status: str, *, valid: bool) -> str | None:
    lifecycle_status = _text(current_lifecycle_status) or "registered"
    if not valid:
        return "invalid"
    if lifecycle_status == "invalid":
        return "registered"
    return None


def _derive_plan_state(
    lifecycle_status: str,
    overview: dict[str, Any],
    trial_end_time: int,
) -> str:
    explicit = _normalize_plan_state(overview.get("plan_state"))
    if explicit:
        return explicit

    candidates = [
        overview.get("membership_type"),
        overview.get("plan"),
        overview.get("plan_name"),
    ]
    for candidate in candidates:
        normalized = _normalize_plan_state(candidate)
        if normalized:
            return normalized

    if lifecycle_status in {"trial", "subscribed", "expired"}:
        return lifecycle_status
    if overview.get("trial_eligible") and not trial_end_time:
        return "eligible"
    return "unknown"


def _derive_display_status(
    lifecycle_status: str,
    validity_status: str,
    plan_state: str,
) -> str:
    if validity_status == "invalid":
        return "invalid"
    if plan_state == "expired" or lifecycle_status == "expired":
        return "expired"
    if plan_state == "subscribed":
        return "subscribed"
    if plan_state == "trial":
        return "trial"
    return lifecycle_status or "registered"


def _parse_checked_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc_datetime(value)
    if isinstance(value, str):
        try:
            return ensure_utc_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


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


def _normalize_overview_summary(
    *,
    platform: str,
    lifecycle_status: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    payload = _safe_dict(summary)
    payload["platform"] = platform

    trial_end_time = int(payload.get("trial_end_time") or 0)
    payload["trial_end_time"] = trial_end_time
    payload["cashier_url"] = _text(payload.get("cashier_url"))
    payload["region"] = _text(payload.get("region"))

    validity_status = _derive_validity_status(lifecycle_status, payload)
    plan_state = _derive_plan_state(lifecycle_status, payload, trial_end_time)
    plan_name = _derive_plan_name(payload)
    display_status = _derive_display_status(lifecycle_status, validity_status, plan_state)

    payload["chips"] = _dedupe_chips(payload.get("chips") or [])
    if bool(payload.get("local_matches_target")) and "当前" not in payload["chips"]:
        payload["chips"].append("当前")

    payload.update(
        {
            "lifecycle_status": lifecycle_status,
            "validity_status": validity_status,
            "plan_state": plan_state,
            "plan_name": plan_name,
            "display_status": display_status,
        }
    )
    payload["remote_email"] = _text(payload.get("remote_email"))
    checked_at = payload.get("checked_at")
    if isinstance(checked_at, datetime):
        payload["checked_at"] = serialize_datetime(checked_at)
    elif checked_at is not None:
        payload["checked_at"] = checked_at
    return payload


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


def _serialize_overview_model(model: AccountOverviewModel) -> dict[str, Any]:
    payload = model.get_summary()
    payload.update(
        {
            "lifecycle_status": model.lifecycle_status,
            "validity_status": model.validity_status,
            "plan_state": model.plan_state,
            "plan_name": model.plan_name,
            "display_status": model.display_status,
            "remote_email": model.remote_email,
            "checked_at": model.checked_at,
        }
    )
    return payload


def _serialize_credential_model(model: AccountCredentialModel) -> dict[str, Any]:
    metadata = model.get_metadata()
    return {
        "id": int(model.id or 0),
        "scope": model.scope,
        "provider_name": model.provider_name,
        "credential_type": model.credential_type,
        "key": model.key,
        "value": model.value,
        "preview": _preview_secret(model.value),
        "is_primary": bool(model.is_primary),
        "source": model.source,
        "metadata": metadata,
    }


def _serialize_provider_account_model(model: ProviderAccountModel) -> dict[str, Any]:
    credentials = model.get_credentials()
    return {
        "id": int(model.id or 0),
        "provider_type": model.provider_type,
        "provider_name": model.provider_name,
        "login_identifier": model.login_identifier,
        "display_name": model.display_name,
        "credentials": credentials,
        "credential_previews": {key: _preview_secret(value) for key, value in credentials.items()},
        "metadata": model.get_metadata(),
    }


def _serialize_provider_resource_model(model: ProviderResourceModel) -> dict[str, Any]:
    return {
        "id": int(model.id or 0),
        "provider_type": model.provider_type,
        "provider_name": model.provider_name,
        "resource_type": model.resource_type,
        "resource_identifier": model.resource_identifier,
        "handle": model.handle,
        "display_name": model.display_name,
        "metadata": model.get_metadata(),
    }


def load_account_graphs(session: Session, account_ids: list[int]) -> dict[int, dict[str, Any]]:
    normalized_ids = [int(account_id) for account_id in account_ids if int(account_id or 0) > 0]
    if not normalized_ids:
        return {}

    graphs: dict[int, dict[str, Any]] = {
        account_id: {
            "overview": {},
            "credentials": [],
            "provider_accounts": [],
            "provider_resources": [],
        }
        for account_id in normalized_ids
    }

    for item in session.exec(select(AccountOverviewModel).where(AccountOverviewModel.account_id.in_(normalized_ids))).all():
        graphs[int(item.account_id)]["overview"] = _serialize_overview_model(item)
    for item in session.exec(select(AccountCredentialModel).where(AccountCredentialModel.account_id.in_(normalized_ids))).all():
        graphs[int(item.account_id)]["credentials"].append(_serialize_credential_model(item))
    for item in session.exec(select(ProviderAccountModel).where(ProviderAccountModel.account_id.in_(normalized_ids))).all():
        graphs[int(item.account_id)]["provider_accounts"].append(_serialize_provider_account_model(item))
    for item in session.exec(select(ProviderResourceModel).where(ProviderResourceModel.account_id.in_(normalized_ids))).all():
        graphs[int(item.account_id)]["provider_resources"].append(_serialize_provider_resource_model(item))

    for account_id, payload in graphs.items():
        overview = _safe_dict(payload.get("overview"))
        payload["lifecycle_status"] = _text(overview.get("lifecycle_status") or "registered") or "registered"
        payload["validity_status"] = _text(overview.get("validity_status") or "unknown") or "unknown"
        payload["plan_state"] = _text(overview.get("plan_state") or "unknown") or "unknown"
        payload["plan_name"] = _text(overview.get("plan_name"))
        payload["display_status"] = _text(overview.get("display_status") or payload["lifecycle_status"]) or "registered"
        payload["verification_mailbox"] = next(
            (
                resource
                for resource in payload["provider_resources"]
                if resource.get("resource_type") == "mailbox"
            ),
            None,
        )
    return graphs


def _graph_for_account(session: Session, account_id: int) -> dict[str, Any]:
    return load_account_graphs(session, [account_id]).get(
        account_id,
        {
            "overview": {},
            "credentials": [],
            "provider_accounts": [],
            "provider_resources": [],
            "lifecycle_status": "registered",
            "validity_status": "unknown",
            "plan_state": "unknown",
            "plan_name": "",
            "display_status": "registered",
            "verification_mailbox": None,
        },
    )


def _persist_account_graph(
    session: Session,
    *,
    account_id: int,
    platform: str,
    summary: dict[str, Any],
    platform_credentials: list[dict[str, Any]],
    provider_accounts: list[dict[str, Any]],
    provider_resources: list[dict[str, Any]],
) -> None:
    normalized_summary = _normalize_overview_summary(
        platform=platform,
        lifecycle_status=_text(summary.get("lifecycle_status") or "registered") or "registered",
        summary=summary,
    )
    overview = session.exec(
        select(AccountOverviewModel).where(AccountOverviewModel.account_id == account_id)
    ).first()
    if not overview:
        overview = AccountOverviewModel(account_id=account_id)
    overview.lifecycle_status = normalized_summary["lifecycle_status"]
    overview.validity_status = normalized_summary["validity_status"]
    overview.plan_state = normalized_summary["plan_state"]
    overview.plan_name = normalized_summary["plan_name"]
    overview.display_status = normalized_summary["display_status"]
    overview.remote_email = _text(normalized_summary.get("remote_email"))
    overview.checked_at = _parse_checked_at(normalized_summary.get("checked_at"))
    overview.set_summary(normalized_summary)
    overview.updated_at = _utcnow()
    session.add(overview)

    session.exec(delete(AccountCredentialModel).where(AccountCredentialModel.account_id == account_id))
    for item in _normalize_platform_credentials(platform, platform_credentials):
        session.add(
            AccountCredentialModel(
                account_id=account_id,
                scope="platform",
                provider_name=platform,
                credential_type=item["credential_type"],
                key=item["key"],
                value=item["value"],
                is_primary=bool(item.get("is_primary")),
                source=item.get("source", ""),
                metadata_json=json.dumps(item.get("metadata") or {}, ensure_ascii=False),
            )
        )

    session.exec(delete(ProviderResourceModel).where(ProviderResourceModel.account_id == account_id))
    session.exec(delete(ProviderAccountModel).where(ProviderAccountModel.account_id == account_id))
    for item in provider_accounts:
        provider_account = ProviderAccountModel(
            account_id=account_id,
            provider_type=item["provider_type"],
            provider_name=item["provider_name"],
            login_identifier=item["login_identifier"],
            display_name=item["display_name"],
        )
        provider_account.set_credentials(item.get("credentials") or {})
        provider_account.set_metadata(item.get("metadata") or {})
        session.add(provider_account)
    for item in provider_resources:
        provider_resource = ProviderResourceModel(
            account_id=account_id,
            provider_type=item["provider_type"],
            provider_name=item["provider_name"],
            resource_type=item["resource_type"],
            resource_identifier=item["resource_identifier"],
            handle=item["handle"],
            display_name=item["display_name"],
        )
        provider_resource.set_metadata(item.get("metadata") or {})
        session.add(provider_resource)


def sync_legacy_account_graph(
    session: Session,
    *,
    account_id: int,
    platform: str,
    lifecycle_status: str,
    region: str = "",
    legacy_token: str = "",
    trial_end_time: int = 0,
    cashier_url: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    if account_id <= 0:
        return

    current = _graph_for_account(session, account_id)
    payload_extra = _safe_dict(extra)
    legacy_summary = _safe_dict(payload_extra.get("account_overview"))
    legacy_summary.update(
        {
            "trial_end_time": int(trial_end_time or 0),
            "cashier_url": _text(cashier_url),
            "region": _text(region),
        }
    )
    legacy_extra = _legacy_extra_payload(payload_extra)
    if legacy_extra:
        merged_legacy_extra = {
            **_safe_dict(legacy_summary.get("legacy_extra")),
            **legacy_extra,
        }
        legacy_summary["legacy_extra"] = merged_legacy_extra
    legacy_summary = _normalize_overview_summary(
        platform=platform,
        lifecycle_status=_text(lifecycle_status) or "registered",
        summary=legacy_summary,
    )

    existing_summary = _safe_dict(current.get("overview"))
    summary = dict(legacy_summary)
    summary.update(existing_summary)
    if summary.get("legacy_extra") or legacy_summary.get("legacy_extra"):
        summary["legacy_extra"] = {
            **_safe_dict(legacy_summary.get("legacy_extra")),
            **_safe_dict(existing_summary.get("legacy_extra")),
        }
    summary["chips"] = _dedupe_chips(legacy_summary.get("chips") or [], existing_summary.get("chips") or [])
    summary["lifecycle_status"] = _text(current.get("lifecycle_status")) or _text(legacy_summary.get("lifecycle_status")) or "registered"

    existing_credentials = [item for item in current.get("credentials") or [] if item.get("scope") == "platform"]
    incoming_credentials = _platform_credentials_from_extra({**payload_extra, "platform": platform}, legacy_token=_text(legacy_token))
    credentials = _merge_platform_credentials(platform, existing_credentials, incoming_credentials, prefer_existing=True)

    provider_accounts = _merge_provider_accounts(
        current.get("provider_accounts") or [],
        _provider_accounts_from_extra(payload_extra),
        prefer_existing=True,
    )
    provider_resources = _merge_provider_resources(
        current.get("provider_resources") or [],
        _provider_resources_from_extra(payload_extra),
        prefer_existing=True,
    )

    _persist_account_graph(
        session,
        account_id=account_id,
        platform=platform,
        summary=summary,
        platform_credentials=credentials,
        provider_accounts=provider_accounts,
        provider_resources=provider_resources,
    )


def sync_account_graph(session: Session, model: AccountModel) -> None:
    account_id = int(model.id or 0)
    if account_id <= 0:
        return

    current = _graph_for_account(session, account_id)
    summary = _safe_dict(current.get("overview"))
    summary["lifecycle_status"] = _text(current.get("lifecycle_status")) or _text(summary.get("lifecycle_status")) or "registered"
    summary["chips"] = _dedupe_chips(summary.get("chips") or [])

    platform = model.platform
    credentials = [item for item in current.get("credentials") or [] if item.get("scope") == "platform"]
    provider_accounts = list(current.get("provider_accounts") or [])
    provider_resources = list(current.get("provider_resources") or [])

    _persist_account_graph(
        session,
        account_id=account_id,
        platform=platform,
        summary=summary,
        platform_credentials=credentials,
        provider_accounts=provider_accounts,
        provider_resources=provider_resources,
    )


def sync_platform_account_graph(session: Session, model: AccountModel, account: Any) -> None:
    account_id = int(model.id or 0)
    if account_id <= 0:
        return

    current = _graph_for_account(session, account_id)
    extra = _safe_dict(getattr(account, "extra", {}) or {})
    incoming_summary = _safe_dict(extra.get("account_overview"))
    incoming_summary.update(
        {
            "trial_end_time": int(getattr(account, "trial_end_time", 0) or 0),
            "cashier_url": _text(extra.get("cashier_url")),
            "region": _text(getattr(account, "region", "")),
        }
    )
    legacy_extra = _legacy_extra_payload(extra)
    if legacy_extra:
        incoming_summary["legacy_extra"] = {
            **_safe_dict(incoming_summary.get("legacy_extra")),
            **legacy_extra,
        }
    lifecycle_status = _text(getattr(getattr(account, "status", None), "value", getattr(account, "status", ""))) or "registered"
    existing_summary = _safe_dict(current.get("overview"))
    summary = dict(existing_summary)
    summary.update(incoming_summary)
    if summary.get("legacy_extra") or existing_summary.get("legacy_extra"):
        summary["legacy_extra"] = {
            **_safe_dict(existing_summary.get("legacy_extra")),
            **_safe_dict(incoming_summary.get("legacy_extra")),
        }
    summary["chips"] = _dedupe_chips(existing_summary.get("chips") or [], incoming_summary.get("chips") or [])
    summary["lifecycle_status"] = lifecycle_status

    platform = model.platform
    existing_credentials = [item for item in current.get("credentials") or [] if item.get("scope") == "platform"]
    incoming_credentials = _platform_credentials_from_extra({**extra, "platform": platform}, legacy_token=_text(getattr(account, "token", "")))
    credentials = _merge_platform_credentials(platform, existing_credentials, incoming_credentials, prefer_existing=False)

    provider_accounts = _merge_provider_accounts(
        current.get("provider_accounts") or [],
        _provider_accounts_from_extra(extra),
        prefer_existing=False,
    )
    provider_resources = _merge_provider_resources(
        current.get("provider_resources") or [],
        _provider_resources_from_extra(extra),
        prefer_existing=False,
    )

    _persist_account_graph(
        session,
        account_id=account_id,
        platform=platform,
        summary=summary,
        platform_credentials=credentials,
        provider_accounts=provider_accounts,
        provider_resources=provider_resources,
    )


def patch_account_graph(
    session: Session,
    model: AccountModel,
    *,
    lifecycle_status: str | None = None,
    primary_token: str | None = None,
    cashier_url: str | None = None,
    region: str | None = None,
    trial_end_time: int | None = None,
    summary_updates: dict[str, Any] | None = None,
    credential_updates: dict[str, Any] | None = None,
    provider_accounts: list[dict[str, Any]] | None = None,
    provider_resources: list[dict[str, Any]] | None = None,
    replace_provider_accounts: bool = False,
    replace_provider_resources: bool = False,
) -> None:
    account_id = int(model.id or 0)
    if account_id <= 0:
        return

    current = _graph_for_account(session, account_id)
    summary = _safe_dict(current.get("overview"))
    if summary_updates:
        summary.update(summary_updates)
    if cashier_url is not None:
        summary["cashier_url"] = cashier_url
    if region is not None:
        summary["region"] = region
    if trial_end_time is not None:
        summary["trial_end_time"] = int(trial_end_time or 0)
    effective_lifecycle = _text(lifecycle_status) or _text(current.get("lifecycle_status")) or "registered"
    summary["lifecycle_status"] = effective_lifecycle

    existing_credentials = [item for item in current.get("credentials") or [] if item.get("scope") == "platform"]
    incoming_credentials: list[dict[str, Any]] = []
    if credential_updates:
        for key, value in credential_updates.items():
            text = _text(value)
            if not text:
                continue
            incoming_credentials.append(
                {
                    "scope": "platform",
                    "provider_name": model.platform,
                    "credential_type": _infer_credential_type(key),
                    "key": key,
                    "value": text,
                    "is_primary": False,
                    "source": "runtime.patch",
                    "metadata": {},
                }
            )
    if primary_token is not None:
        token_key = next(
            (
                item.get("key")
                for item in existing_credentials
                if item.get("is_primary")
            ),
            "",
        ) or _default_primary_token_key(model.platform)
        incoming_credentials.append(
            {
                "scope": "platform",
                "provider_name": model.platform,
                "credential_type": "token",
                "key": token_key,
                "value": _text(primary_token),
                "is_primary": True,
                "source": "accounts.api",
                "metadata": {},
            }
        )
    credentials = _merge_platform_credentials(model.platform, existing_credentials, incoming_credentials, prefer_existing=False)

    current_provider_accounts = current.get("provider_accounts") or []
    next_provider_accounts = current_provider_accounts
    if provider_accounts is not None:
        next_provider_accounts = (
            _provider_accounts_from_extra({"provider_accounts": provider_accounts})
            if replace_provider_accounts
            else _merge_provider_accounts(current_provider_accounts, provider_accounts, prefer_existing=False)
        )

    current_provider_resources = current.get("provider_resources") or []
    next_provider_resources = current_provider_resources
    if provider_resources is not None:
        next_provider_resources = (
            _provider_resources_from_extra({"provider_resources": provider_resources})
            if replace_provider_resources
            else _merge_provider_resources(current_provider_resources, provider_resources, prefer_existing=False)
        )

    _persist_account_graph(
        session,
        account_id=account_id,
        platform=model.platform,
        summary=summary,
        platform_credentials=credentials,
        provider_accounts=next_provider_accounts,
        provider_resources=next_provider_resources,
    )


def sync_all_account_graphs(session: Session) -> None:
    accounts = session.exec(select(AccountModel)).all()
    for model in accounts:
        if model.id is None:
            continue
        sync_account_graph(session, model)


def purge_account_graph(session: Session, account_id: int) -> None:
    session.exec(delete(AccountCredentialModel).where(AccountCredentialModel.account_id == account_id))
    session.exec(delete(ProviderResourceModel).where(ProviderResourceModel.account_id == account_id))
    session.exec(delete(ProviderAccountModel).where(ProviderAccountModel.account_id == account_id))
    session.exec(delete(AccountOverviewModel).where(AccountOverviewModel.account_id == account_id))


def matches_status_filter(graph: dict[str, Any], status: str) -> bool:
    expected = _text(status)
    if not expected:
        return True
    return expected in {
        _text(graph.get("display_status")),
        _text(graph.get("lifecycle_status")),
        _text(graph.get("plan_state")),
        _text(graph.get("validity_status")),
    }


def compute_account_stats(graphs: list[dict[str, Any]], platforms: list[str]) -> dict[str, dict[str, int]]:
    by_platform: dict[str, int] = defaultdict(int)
    by_lifecycle_status: dict[str, int] = defaultdict(int)
    by_plan_state: dict[str, int] = defaultdict(int)
    by_validity_status: dict[str, int] = defaultdict(int)
    by_display_status: dict[str, int] = defaultdict(int)

    for platform in platforms:
        by_platform[platform] += 1
    for graph in graphs:
        by_lifecycle_status[_text(graph.get("lifecycle_status") or "registered")] += 1
        by_plan_state[_text(graph.get("plan_state") or "unknown")] += 1
        by_validity_status[_text(graph.get("validity_status") or "unknown")] += 1
        by_display_status[_text(graph.get("display_status") or "registered")] += 1

    return {
        "by_platform": dict(by_platform),
        "by_lifecycle_status": dict(by_lifecycle_status),
        "by_plan_state": dict(by_plan_state),
        "by_validity_status": dict(by_validity_status),
        "by_display_status": dict(by_display_status),
    }
