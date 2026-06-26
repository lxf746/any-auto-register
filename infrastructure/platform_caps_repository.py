from __future__ import annotations

from sqlmodel import Session, select

from core.datetime_utils import _utcnow
from core.db import PlatformCapabilityOverrideModel, engine
from core.registry import list_platforms
from domain.platform_caps import PlatformCapabilitiesUpdate


class PlatformCapabilitiesRepository:
    ALLOWED_KEYS = {"supported_executors", "supported_identity_modes", "supported_oauth_providers", "capabilities"}

    def list_platforms(self) -> list[dict]:
        return list_platforms()

    def update(self, name: str, update: PlatformCapabilitiesUpdate) -> dict:
        payload = {
            "supported_executors": update.supported_executors,
            "supported_identity_modes": update.supported_identity_modes,
            "supported_oauth_providers": update.supported_oauth_providers,
            "capabilities": update.capabilities,
        }
        safe = {key: value for key, value in payload.items() if key in self.ALLOWED_KEYS}
        with Session(engine) as session:
            item = session.exec(
                select(PlatformCapabilityOverrideModel)
                .where(PlatformCapabilityOverrideModel.platform_name == name)
            ).first()
            if not item:
                item = PlatformCapabilityOverrideModel(platform_name=name)
                item.created_at = _utcnow()
            item.set_capabilities(safe)
            item.updated_at = _utcnow()
            session.add(item)
            session.commit()
        return {"ok": True}

    def reset(self, name: str) -> dict:
        with Session(engine) as session:
            item = session.exec(
                select(PlatformCapabilityOverrideModel)
                .where(PlatformCapabilityOverrideModel.platform_name == name)
            ).first()
            if item:
                session.delete(item)
                session.commit()
        return {"ok": True}
