from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from core.account_graph.overview import (
    _dedupe_chips,
    _normalize_overview_summary,
    _safe_dict,
    _text,
)
from core.account_graph.credentials import (
    _default_primary_token_key,
    _infer_credential_type,
    _legacy_extra_payload,
    _merge_platform_credentials,
    _merge_provider_accounts,
    _merge_provider_resources,
    _platform_credentials_from_extra,
    _provider_accounts_from_extra,
    _provider_resources_from_extra,
)
from core.account_graph.graph_ops import (
    _graph_for_account,
    _persist_account_graph,
)
from core.db import AccountModel


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
