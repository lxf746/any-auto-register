from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from core.config_store import config_store
from core.db import ProviderSettingModel, engine
from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProviderSettingsRepository:
    def __init__(self, definitions: ProviderDefinitionsRepository | None = None):
        self.definitions = definitions or ProviderDefinitionsRepository()

    def list_by_type(self, provider_type: str) -> list[ProviderSettingModel]:
        self._ensure_seeded(provider_type)
        with Session(engine) as session:
            return session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == provider_type)
                .order_by(ProviderSettingModel.id)
            ).all()

    def get(self, setting_id: int) -> ProviderSettingModel | None:
        with Session(engine) as session:
            return session.get(ProviderSettingModel, setting_id)

    def get_by_key(self, provider_type: str, provider_key: str) -> ProviderSettingModel | None:
        self._ensure_seeded(provider_type)
        with Session(engine) as session:
            return session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == provider_type)
                .where(ProviderSettingModel.provider_key == provider_key)
            ).first()

    def resolve_runtime_settings(self, provider_type: str, provider_key: str, overrides: dict | None = None) -> dict:
        item = self.get_by_key(provider_type, provider_key)
        payload: dict = {}
        if item:
            payload.update(item.get_config())
            payload.update(item.get_auth())
        payload.update(dict(overrides or {}))
        return payload

    def list_enabled(self, provider_type: str) -> list[ProviderSettingModel]:
        self._ensure_seeded(provider_type)
        with Session(engine) as session:
            items = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == provider_type)
                .where(ProviderSettingModel.enabled == True)  # noqa: E712
                .order_by(ProviderSettingModel.id)
            ).all()
        return sorted(items, key=lambda item: (not bool(item.is_default), int(item.id or 0)))

    def get_enabled_captcha_order(self, fallback_order: list[str] | tuple[str, ...] | None = None) -> list[str]:
        configured = [
            item.provider_key
            for item in self.list_enabled("captcha")
            if item.provider_key not in {"", "manual", "local_solver"}
        ]
        merged: list[str] = []
        for key in configured + list(fallback_order or []):
            normalized = str(key or "").strip()
            if not normalized or normalized in {"manual", "local_solver"} or normalized in merged:
                continue
            merged.append(normalized)
        return merged

    def delete(self, setting_id: int) -> bool:
        with Session(engine) as session:
            item = session.get(ProviderSettingModel, setting_id)
            if not item:
                return False
            provider_type = item.provider_type
            is_default = bool(item.is_default)
            session.delete(item)
            session.commit()

            remaining = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == provider_type)
                .order_by(ProviderSettingModel.id)
            ).all()
            if is_default and remaining:
                fallback = remaining[0]
                fallback.is_default = True
                fallback.updated_at = _utcnow()
                session.add(fallback)
                session.commit()
                self._sync_legacy_config(provider_type, fallback)
            return True

    def save(
        self,
        *,
        setting_id: int | None,
        provider_type: str,
        provider_key: str,
        display_name: str,
        auth_mode: str,
        enabled: bool,
        is_default: bool,
        config: dict,
        auth: dict,
        metadata: dict,
    ) -> ProviderSettingModel:
        definition = self.definitions.get_by_key(provider_type, provider_key)
        if not definition:
            raise ValueError(f"未知 provider: {provider_type}/{provider_key}")

        with Session(engine) as session:
            if setting_id:
                item = session.get(ProviderSettingModel, setting_id)
                if not item:
                    raise ValueError("provider setting 不存在")
            else:
                item = session.exec(
                    select(ProviderSettingModel)
                    .where(ProviderSettingModel.provider_type == provider_type)
                    .where(ProviderSettingModel.provider_key == provider_key)
                ).first()
                if not item:
                    item = ProviderSettingModel(
                        provider_type=provider_type,
                        provider_key=provider_key,
                    )
                    item.created_at = _utcnow()

            if is_default:
                for other in session.exec(
                    select(ProviderSettingModel).where(ProviderSettingModel.provider_type == provider_type)
                ).all():
                    if other.id != item.id and other.is_default:
                        other.is_default = False
                        other.updated_at = _utcnow()
                        session.add(other)

            item.display_name = display_name or definition.label or provider_key
            item.auth_mode = auth_mode or definition.default_auth_mode or ""
            item.enabled = bool(enabled)
            item.is_default = bool(is_default)
            item.set_config(config or {})
            item.set_auth(auth or {})
            item.set_metadata(metadata or {})
            item.updated_at = _utcnow()
            session.add(item)
            session.commit()
            session.refresh(item)

        self._sync_legacy_config(provider_type, item)
        return item

    def _ensure_seeded(self, provider_type: str) -> None:
        definitions = self.definitions.list_by_type(provider_type, enabled_only=True)
        if not definitions:
            return

        legacy_all = config_store.get_all()
        default_key = ""
        if provider_type == "mailbox":
            default_key = legacy_all.get("mail_provider", "")
        elif provider_type == "captcha":
            default_key = legacy_all.get("default_captcha_solver", "")

        with Session(engine) as session:
            existing_items = session.exec(
                select(ProviderSettingModel).where(ProviderSettingModel.provider_type == provider_type)
            ).all()
            existing = {item.provider_key: item for item in existing_items}
            has_default = any(bool(item.is_default) for item in existing_items)
            changed = False
            for definition in definitions:
                provider_key = str(definition.provider_key or "")
                if not provider_key or provider_key in existing:
                    continue
                config, auth = self._extract_legacy_payload(definition, legacy_all)
                item = ProviderSettingModel(
                    provider_type=provider_type,
                    provider_key=provider_key,
                    display_name=definition.label or provider_key,
                    auth_mode=definition.default_auth_mode or "",
                    enabled=True,
                    is_default=(not has_default and provider_key == default_key),
                )
                item.set_config(config)
                item.set_auth(auth)
                item.set_metadata({})
                session.add(item)
                changed = True
            if changed:
                session.commit()

    def _extract_legacy_payload(self, definition, legacy_all: dict[str, str]) -> tuple[dict, dict]:
        config: dict[str, str] = {}
        auth: dict[str, str] = {}
        for field in definition.get_fields():
            key = str(field.get("key") or "")
            if not key:
                continue
            value = str(legacy_all.get(key, "") or "")
            if not value:
                continue
            target = auth if field.get("category") == "auth" else config
            target[key] = value
        return config, auth

    def _sync_legacy_config(self, provider_type: str, item: ProviderSettingModel) -> None:
        definition = self.definitions.get_by_key(provider_type, item.provider_key)
        if not definition:
            return
        flat: dict[str, str] = {}
        merged = {}
        merged.update(item.get_config())
        merged.update(item.get_auth())
        for field in definition.get_fields():
            key = str(field.get("key") or "")
            if not key:
                continue
            flat[key] = str(merged.get(key, "") or "")

        if provider_type == "mailbox" and item.is_default:
            flat["mail_provider"] = item.provider_key
        if provider_type == "captcha" and item.is_default:
            flat["default_captcha_solver"] = item.provider_key

        if flat:
            config_store.set_many(flat)
