from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlmodel import Session, select

from core.datetime_utils import serialize_datetime
from core.db import AccountModel, engine
from core.account_graph import (
    compute_account_stats,
    load_account_graphs,
    matches_status_filter,
    patch_account_graph,
    purge_account_graph,
    sync_account_graph,
)
from core.platform_accounts import resolve_primary_token
from domain.accounts import (
    AccountCreateCommand,
    AccountExportSelection,
    AccountImportLine,
    AccountQuery,
    AccountRecord,
    AccountStats,
    AccountUpdateCommand,
)


def _build_summary_updates(
    overview: dict | None,
    *,
    cashier_url: str | None = None,
    region: str | None = None,
    trial_end_time: int | None = None,
) -> dict | None:
    summary = dict(overview or {})
    if cashier_url is not None:
        summary["cashier_url"] = cashier_url
    if region is not None:
        summary["region"] = region
    if trial_end_time is not None:
        summary["trial_end_time"] = int(trial_end_time or 0)
    return summary or None


def _build_credential_updates(
    credentials: dict | None,
) -> dict | None:
    return dict(credentials or {}) or None


def _to_record(model: AccountModel, graph: dict | None = None) -> AccountRecord:
    graph = graph or {}
    overview = graph.get("overview") or {}
    return AccountRecord(
        id=int(model.id or 0),
        platform=model.platform,
        email=model.email,
        password=model.password,
        user_id=model.user_id,
        primary_token=resolve_primary_token(model, graph),
        trial_end_time=int(overview.get("trial_end_time") or 0),
        cashier_url=str(overview.get("cashier_url") or ""),
        lifecycle_status=graph.get("lifecycle_status") or "registered",
        validity_status=graph.get("validity_status") or "unknown",
        plan_state=graph.get("plan_state") or "unknown",
        plan_name=graph.get("plan_name") or "",
        display_status=graph.get("display_status") or "registered",
        overview=overview,
        credentials=list(graph.get("credentials") or []),
        provider_accounts=list(graph.get("provider_accounts") or []),
        provider_resources=list(graph.get("provider_resources") or []),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class AccountsRepository:
    @staticmethod
    def _get_by_platform_email(session: Session, *, platform: str, email: str) -> AccountModel | None:
        return session.exec(
            select(AccountModel)
            .where(AccountModel.platform == platform)
            .where(AccountModel.email == email)
        ).first()

    @staticmethod
    def _load_records(session: Session, models: list[AccountModel]) -> list[AccountRecord]:
        account_ids = [int(model.id or 0) for model in models if model.id]
        graphs = load_account_graphs(session, account_ids)
        missing = [model for model in models if int(model.id or 0) not in graphs]
        if missing:
            for model in missing:
                sync_account_graph(session, model)
            session.commit()
            graphs = load_account_graphs(session, account_ids)
        return [_to_record(model, graphs.get(int(model.id or 0), {})) for model in models]

    def list(self, query: AccountQuery) -> tuple[int, list[AccountRecord]]:
        page = max(query.page, 1)
        page_size = max(query.page_size, 1)
        with Session(engine) as session:
            statement = select(AccountModel)
            if query.platform:
                statement = statement.where(AccountModel.platform == query.platform)
            if query.email:
                statement = statement.where(AccountModel.email.contains(query.email))
            statement = statement.order_by(AccountModel.created_at.desc(), AccountModel.id.desc())
            models = session.exec(statement).all()
            records = self._load_records(session, models)
            if query.status:
                records = [item for item in records if matches_status_filter({
                    "display_status": item.display_status,
                    "lifecycle_status": item.lifecycle_status,
                    "plan_state": item.plan_state,
                    "validity_status": item.validity_status,
                }, query.status)]
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        return total, records[start:end]

    def get(self, account_id: int) -> AccountRecord | None:
        with Session(engine) as session:
            model = session.get(AccountModel, account_id)
            if not model:
                return None
            records = self._load_records(session, [model])
            return records[0] if records else None

    def select_for_export(self, selection: AccountExportSelection) -> list[AccountRecord]:
        with Session(engine) as session:
            statement = select(AccountModel)
            if selection.platform:
                statement = statement.where(AccountModel.platform == selection.platform)
            if selection.search_filter:
                statement = statement.where(AccountModel.email.contains(selection.search_filter))
            if not selection.select_all and selection.ids:
                statement = statement.where(AccountModel.id.in_(selection.ids))
            statement = statement.order_by(AccountModel.created_at.desc(), AccountModel.id.desc())
            models = session.exec(statement).all()
            records = self._load_records(session, models)
        if selection.status_filter:
            records = [item for item in records if matches_status_filter({
                "display_status": item.display_status,
                "lifecycle_status": item.lifecycle_status,
                "plan_state": item.plan_state,
                "validity_status": item.validity_status,
            }, selection.status_filter)]
        return records

    def create(self, command: AccountCreateCommand) -> AccountRecord:
        with Session(engine) as session:
            model = self._get_by_platform_email(session, platform=command.platform, email=command.email)
            if model:
                model.password = command.password
                model.user_id = command.user_id
                model.updated_at = datetime.now(timezone.utc)
            else:
                model = AccountModel(
                    platform=command.platform,
                    email=command.email,
                    password=command.password,
                    user_id=command.user_id,
                )
            session.add(model)
            session.commit()
            session.refresh(model)
            patch_account_graph(
                session,
                model,
                lifecycle_status=command.lifecycle_status,
                primary_token=command.primary_token or None,
                cashier_url=command.cashier_url or None,
                region=command.region or None,
                trial_end_time=command.trial_end_time or None,
                summary_updates=_build_summary_updates(
                    command.overview,
                    cashier_url=command.cashier_url or None,
                    region=command.region or None,
                    trial_end_time=command.trial_end_time or None,
                ),
                credential_updates=_build_credential_updates(command.credentials),
                provider_accounts=command.provider_accounts or None,
                provider_resources=command.provider_resources or None,
                replace_provider_accounts=bool(command.provider_accounts),
                replace_provider_resources=bool(command.provider_resources),
            )
            session.commit()
            return self._load_records(session, [model])[0]

    def update(self, account_id: int, command: AccountUpdateCommand) -> AccountRecord | None:
        with Session(engine) as session:
            model = session.get(AccountModel, account_id)
            if not model:
                return None
            if command.password is not None:
                model.password = command.password
            if command.user_id is not None:
                model.user_id = command.user_id
            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            session.commit()
            session.refresh(model)
            patch_account_graph(
                session,
                model,
                lifecycle_status=command.lifecycle_status,
                primary_token=command.primary_token,
                cashier_url=command.cashier_url,
                region=command.region,
                trial_end_time=command.trial_end_time,
                summary_updates=_build_summary_updates(
                    command.overview,
                    cashier_url=command.cashier_url,
                    region=command.region,
                    trial_end_time=command.trial_end_time,
                ),
                credential_updates=_build_credential_updates(command.credentials),
                provider_accounts=command.provider_accounts,
                provider_resources=command.provider_resources,
                replace_provider_accounts=command.replace_provider_accounts,
                replace_provider_resources=command.replace_provider_resources,
            )
            session.commit()
            return self._load_records(session, [model])[0]

    def delete(self, account_id: int) -> bool:
        with Session(engine) as session:
            model = session.get(AccountModel, account_id)
            if not model:
                return False
            purge_account_graph(session, account_id)
            session.delete(model)
            session.commit()
            return True

    def import_lines(self, platform: str, lines: list[AccountImportLine]) -> int:
        created = 0
        with Session(engine) as session:
            for line in lines:
                model = self._get_by_platform_email(session, platform=platform, email=line.email)
                if model:
                    model.password = line.password
                    model.updated_at = datetime.now(timezone.utc)
                else:
                    model = AccountModel(
                        platform=platform,
                        email=line.email,
                        password=line.password,
                    )
                    created += 1
                session.add(model)
                session.flush()

                extra = dict(line.extra or {})
                summary_updates = dict(extra.get("overview") or extra.get("summary") or {})
                for key in ("trial_end_time", "cashier_url", "region", "remote_email", "checked_at"):
                    if key in extra and key not in summary_updates:
                        summary_updates[key] = extra[key]
                legacy_extra = {
                    key: value
                    for key, value in extra.items()
                    if key not in {
                        "overview",
                        "summary",
                        "primary_token",
                        "token",
                        "lifecycle_status",
                        "status",
                        "cashier_url",
                        "trial_end_time",
                        "region",
                        "remote_email",
                        "checked_at",
                        "credentials",
                        "provider_accounts",
                        "provider_resources",
                    }
                    and value not in (None, "", [], {})
                }
                if legacy_extra:
                    summary_updates["legacy_extra"] = legacy_extra
                credential_updates = dict(extra.get("credentials") or {})
                for key in (
                    "access_token",
                    "refresh_token",
                    "session_token",
                    "id_token",
                    "accessToken",
                    "refreshToken",
                    "sessionToken",
                    "idToken",
                    "cookies",
                    "cookie",
                    "api_key",
                    "wos_session",
                    "sso",
                    "sso_rw",
                ):
                    if key in extra and key not in credential_updates:
                        credential_updates[key] = extra[key]
                primary_token = extra.get("primary_token")
                if primary_token in (None, ""):
                    primary_token = extra.get("token")
                lifecycle_status_raw = str(extra.get("lifecycle_status") or extra.get("status") or "").strip()
                lifecycle_status = lifecycle_status_raw or None
                patch_account_graph(
                    session,
                    model,
                    lifecycle_status=lifecycle_status,
                    primary_token=str(primary_token or "") or None,
                    cashier_url=str(extra.get("cashier_url") or "") or None,
                    summary_updates=summary_updates or None,
                    credential_updates=credential_updates or None,
                    provider_accounts=list(extra.get("provider_accounts") or []) or None,
                    provider_resources=list(extra.get("provider_resources") or []) or None,
                    replace_provider_accounts=bool(extra.get("provider_accounts")),
                    replace_provider_resources=bool(extra.get("provider_resources")),
                )
            session.commit()
        return created

    def stats(self) -> AccountStats:
        with Session(engine) as session:
            accounts = session.exec(select(AccountModel).order_by(AccountModel.created_at.desc(), AccountModel.id.desc())).all()
            records = self._load_records(session, accounts)
        stats = compute_account_stats(
            [
                {
                    "lifecycle_status": item.lifecycle_status,
                    "plan_state": item.plan_state,
                    "validity_status": item.validity_status,
                    "display_status": item.display_status,
                }
                for item in records
            ],
            [item.platform for item in records],
        )
        return AccountStats(
            total=len(records),
            by_platform=stats["by_platform"],
            by_status=stats["by_display_status"],
            by_lifecycle_status=stats["by_lifecycle_status"],
            by_plan_state=stats["by_plan_state"],
            by_validity_status=stats["by_validity_status"],
            by_display_status=stats["by_display_status"],
        )

    def export_csv(self, query: AccountQuery) -> str:
        _, items = self.list(query)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "platform",
                "email",
                "password",
                "user_id",
                "display_status",
                "lifecycle_status",
                "plan_state",
                "validity_status",
                "cashier_url",
                "created_at",
            ]
        )
        for item in items:
            writer.writerow([
                item.platform,
                item.email,
                item.password,
                item.user_id,
                item.display_status,
                item.lifecycle_status,
                item.plan_state,
                item.validity_status,
                item.cashier_url,
                serialize_datetime(item.created_at) or "",
            ])
        return output.getvalue()
