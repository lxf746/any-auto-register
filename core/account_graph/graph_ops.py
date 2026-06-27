from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, delete, select

from core.account_graph.overview import (
    _normalize_overview_summary,
    _parse_checked_at,
    _preview_secret,
    _safe_dict,
    _text,
)
from core.account_graph.credentials import _normalize_platform_credentials
from core.db import (
    AccountCredentialModel,
    AccountModel,
    AccountOverviewModel,
    ProviderAccountModel,
    ProviderResourceModel,
)
from core.datetime_utils import _utcnow


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


def purge_account_graph(session: Session, account_id: int) -> None:
    session.exec(delete(AccountCredentialModel).where(AccountCredentialModel.account_id == account_id))
    session.exec(delete(ProviderResourceModel).where(ProviderResourceModel.account_id == account_id))
    session.exec(delete(ProviderAccountModel).where(ProviderAccountModel.account_id == account_id))
    session.exec(delete(AccountOverviewModel).where(AccountOverviewModel.account_id == account_id))
