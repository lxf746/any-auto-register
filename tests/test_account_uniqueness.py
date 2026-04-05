from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine, select

import core.db as db_module
import infrastructure.accounts_repository as accounts_repo_module
from domain.accounts import AccountCreateCommand, AccountImportLine
from infrastructure.accounts_repository import AccountsRepository


class _EnginePatchMixin:
    def _patch_engine(self, test_engine):
        self._origin_db_engine = db_module.engine
        self._origin_repo_engine = accounts_repo_module.engine
        db_module.engine = test_engine
        accounts_repo_module.engine = test_engine

    def _restore_engine(self):
        db_module.engine = self._origin_db_engine
        accounts_repo_module.engine = self._origin_repo_engine


class AccountUniquenessRepositoryTests(unittest.TestCase, _EnginePatchMixin):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "repo.db"
        self._engine = create_engine(f"sqlite:///{db_path}")
        self._patch_engine(self._engine)
        SQLModel.metadata.create_all(self._engine)

    def tearDown(self):
        self._restore_engine()
        self._engine.dispose()
        self._tmpdir.cleanup()

    def test_create_uses_upsert_for_same_platform_email(self):
        repo = AccountsRepository()
        first = repo.create(
            AccountCreateCommand(
                platform="chatgpt",
                email="dup@example.com",
                password="p1",
                user_id="u1",
            )
        )
        second = repo.create(
            AccountCreateCommand(
                platform="chatgpt",
                email="dup@example.com",
                password="p2",
                user_id="u2",
            )
        )

        with Session(db_module.engine) as session:
            rows = session.exec(
                select(db_module.AccountModel)
                .where(db_module.AccountModel.platform == "chatgpt")
                .where(db_module.AccountModel.email == "dup@example.com")
            ).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(rows[0].password, "p2")
        self.assertEqual(rows[0].user_id, "u2")

    def test_import_uses_upsert_for_same_platform_email(self):
        repo = AccountsRepository()
        repo.create(
            AccountCreateCommand(
                platform="chatgpt",
                email="exists@example.com",
                password="old-pass",
            )
        )

        created = repo.import_lines(
            "chatgpt",
            [
                AccountImportLine(email="exists@example.com", password="new-pass"),
                AccountImportLine(email="new@example.com", password="p3"),
                AccountImportLine(email="new@example.com", password="p4"),
            ],
        )
        self.assertEqual(created, 1)

        with Session(db_module.engine) as session:
            rows = session.exec(
                select(db_module.AccountModel)
                .where(db_module.AccountModel.platform == "chatgpt")
                .order_by(db_module.AccountModel.email.asc())
            ).all()
            by_email = {row.email: row for row in rows}
        self.assertEqual(len(rows), 2)
        self.assertEqual(by_email["exists@example.com"].password, "new-pass")
        self.assertEqual(by_email["new@example.com"].password, "p4")


class AccountUniquenessMigrationTests(unittest.TestCase, _EnginePatchMixin):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "migration.db"
        self._engine = create_engine(f"sqlite:///{db_path}")
        self._patch_engine(self._engine)

        with self._engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE accounts (
                    id INTEGER NOT NULL PRIMARY KEY,
                    platform VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    password VARCHAR NOT NULL,
                    user_id VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )

        SQLModel.metadata.create_all(self._engine)
        with self._engine.begin() as connection:
            connection.exec_driver_sql(
                """
                INSERT INTO accounts (id, platform, email, password, user_id, created_at, updated_at)
                VALUES
                    (1, 'chatgpt', 'dup@example.com', 'old-pass', 'u1', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
                    (2, 'chatgpt', 'dup@example.com', 'new-pass', 'u2', '2026-01-02T00:00:00Z', '2026-01-02T00:00:00Z')
                """
            )
            connection.exec_driver_sql(
                """
                INSERT INTO account_credentials (account_id, scope, provider_name, credential_type, key, value, is_primary, source, metadata_json, created_at, updated_at)
                VALUES (1, 'platform', 'chatgpt', 'token', 'access_token', 't1', 1, 'import', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
                """
            )

    def tearDown(self):
        self._restore_engine()
        self._engine.dispose()
        self._tmpdir.cleanup()

    def test_migration_dedupes_and_enforces_unique(self):
        db_module._ensure_accounts_platform_email_unique()

        with Session(db_module.engine) as session:
            accounts = session.exec(select(db_module.AccountModel)).all()
            credentials = session.exec(select(db_module.AccountCredentialModel)).all()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].id, 2)
        self.assertEqual(credentials[0].account_id, 2)

        indices = inspect(db_module.engine).get_indexes("accounts")
        unique_index_names = {
            str(item.get("name") or "")
            for item in indices
            if bool(item.get("unique"))
        }
        self.assertIn("uq_accounts_platform_email", unique_index_names)

        with Session(db_module.engine) as session:
            session.add(
                db_module.AccountModel(
                    platform="chatgpt",
                    email="dup@example.com",
                    password="should-fail",
                    user_id="x",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
