from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session, create_engine, select

import infrastructure.provider_settings_repository as repository_module
from core.db import ProviderSettingModel, SQLModel
from infrastructure.provider_settings_repository import ProviderSettingsRepository


class _FakeDefinition:
    def __init__(self, provider_key: str, label: str):
        self.provider_key = provider_key
        self.label = label
        self.default_auth_mode = ""

    def get_fields(self):
        return []


class _FakeDefinitionsRepository:
    def __init__(self, definitions):
        self._definitions = definitions

    def list_by_type(self, provider_type: str, enabled_only: bool = False):
        return list(self._definitions)


class ProviderSettingsRepositoryTests(unittest.TestCase):
    def setUp(self):
        self._original_engine = repository_module.engine
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "provider-settings-test.db"
        self._engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self._engine, tables=[ProviderSettingModel.__table__])
        repository_module.engine = self._engine

    def tearDown(self):
        repository_module.engine = self._original_engine
        self._engine.dispose()
        self._tmpdir.cleanup()

    def test_seed_missing_definition_when_existing_settings_present_without_overriding_default(self):
        with Session(self._engine) as session:
            existing = ProviderSettingModel(
                provider_type="mailbox",
                provider_key="old_mail",
                display_name="Old Mail",
                auth_mode="",
                enabled=True,
                is_default=True,
            )
            existing.set_config({})
            existing.set_auth({})
            existing.set_metadata({})
            session.add(existing)
            session.commit()

        repository = ProviderSettingsRepository(
            definitions=_FakeDefinitionsRepository(
                definitions=[
                    _FakeDefinition("old_mail", "Old Mail"),
                    _FakeDefinition("new_mail", "New Mail"),
                ]
            )
        )

        with patch.object(repository_module.config_store, "get_all", return_value={"mail_provider": "new_mail"}):
            repository._ensure_seeded("mailbox")

        with Session(self._engine) as session:
            items = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == "mailbox")
                .order_by(ProviderSettingModel.provider_key)
            ).all()

        self.assertEqual([item.provider_key for item in items], ["new_mail", "old_mail"])
        self.assertFalse(next(item for item in items if item.provider_key == "new_mail").is_default)
        self.assertTrue(next(item for item in items if item.provider_key == "old_mail").is_default)


if __name__ == "__main__":
    unittest.main(verbosity=2)
