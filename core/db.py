"""Database models - SQLite via SQLModel"""
import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy import UniqueConstraint, inspect
from sqlmodel import Field, SQLModel, Session, create_engine, select

from core.datetime_utils import _utcnow


# ---------------------------------------------------------------------------
# Password encryption at rest
# ---------------------------------------------------------------------------

_FERNET = None


def _get_fernet():
    """Lazy-init Fernet cipher from ACCOUNT_ENCRYPTION_KEY env var."""
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    from cryptography.fernet import Fernet

    raw_key = os.getenv("ACCOUNT_ENCRYPTION_KEY", "")
    if not raw_key:
        # Derive a deterministic key from a passphrase (not truly secure for
        # production, but better than plaintext; set ACCOUNT_ENCRYPTION_KEY
        # in production).
        raw_key = hashlib.pbkdf2_hmac(
            "sha256",
            b"any-auto-register-default-key",
            b"any-auto-register-salt",
            100_000,
        )
        key = base64.urlsafe_b64encode(raw_key)
    else:
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac("sha256", raw_key.encode(), b"any-auto-register-salt", 100_000)
        )
    _FERNET = Fernet(key)
    return _FERNET


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password for storage. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password. Handles both encrypted and legacy plaintext."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Legacy plaintext — return as-is
        return ciphertext


# ---------------------------------------------------------------------------
# SQL injection prevention for _ensure_column
# ---------------------------------------------------------------------------

_VALID_TABLES = frozenset({
    "accounts",
    "account_overviews",
    "account_credentials",
    "provider_accounts",
    "provider_resources",
    "provider_definitions",
    "provider_settings",
    "platform_capability_overrides",
    "task_logs",
    "tasks",
    "task_events",
    "proxies",
})

_VALID_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _default_database_url() -> str:
    database_path = Path(__file__).resolve().parent.parent / "account_manager.db"
    return f"sqlite:///{database_path}"


DATABASE_URL = os.getenv("ACCOUNT_MANAGER_DATABASE_URL", _default_database_url())
engine = create_engine(DATABASE_URL)


class AccountModel(SQLModel, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)
    email: str = Field(index=True)
    password: str
    user_id: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class AccountOverviewModel(SQLModel, table=True):
    __tablename__ = "account_overviews"

    account_id: int = Field(primary_key=True, foreign_key="accounts.id")
    lifecycle_status: str = Field(default="registered", index=True)
    validity_status: str = Field(default="unknown", index=True)
    plan_state: str = Field(default="unknown", index=True)
    plan_name: str = ""
    display_status: str = Field(default="registered", index=True)
    remote_email: str = ""
    checked_at: Optional[datetime] = None
    summary_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_summary(self) -> dict:
        return json.loads(self.summary_json or "{}")

    def set_summary(self, data: dict):
        self.summary_json = json.dumps(data or {}, ensure_ascii=False)


class AccountCredentialModel(SQLModel, table=True):
    __tablename__ = "account_credentials"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True, foreign_key="accounts.id")
    scope: str = Field(default="platform", index=True)
    provider_name: str = Field(default="", index=True)
    credential_type: str = Field(default="secret", index=True)
    key: str = Field(default="", index=True)
    value: str = ""
    is_primary: bool = False
    source: str = ""
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json or "{}")

    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)


class ProviderAccountModel(SQLModel, table=True):
    __tablename__ = "provider_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True, foreign_key="accounts.id")
    provider_type: str = Field(default="mailbox", index=True)
    provider_name: str = Field(default="", index=True)
    login_identifier: str = Field(default="", index=True)
    display_name: str = ""
    credentials_json: str = "{}"
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_credentials(self) -> dict:
        return json.loads(self.credentials_json or "{}")

    def set_credentials(self, data: dict):
        self.credentials_json = json.dumps(data or {}, ensure_ascii=False)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json or "{}")

    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)


class ProviderResourceModel(SQLModel, table=True):
    __tablename__ = "provider_resources"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True, foreign_key="accounts.id")
    provider_type: str = Field(default="mailbox", index=True)
    provider_name: str = Field(default="", index=True)
    resource_type: str = Field(default="resource", index=True)
    resource_identifier: str = Field(default="", index=True)
    handle: str = ""
    display_name: str = ""
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json or "{}")

    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)


class ProviderDefinitionModel(SQLModel, table=True):
    __tablename__ = "provider_definitions"
    __table_args__ = (
        UniqueConstraint("provider_type", "provider_key", name="uq_provider_definitions_type_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    provider_type: str = Field(index=True)
    provider_key: str = Field(index=True)
    label: str = ""
    description: str = ""
    driver_type: str = ""
    default_auth_mode: str = ""
    enabled: bool = True
    is_builtin: bool = False
    category: str = ""  # "free" | "selfhost" | "custom"
    auth_modes_json: str = "[]"
    fields_json: str = "[]"
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_auth_modes(self) -> list[dict]:
        return json.loads(self.auth_modes_json or "[]")

    def set_auth_modes(self, data: list[dict]):
        self.auth_modes_json = json.dumps(data or [], ensure_ascii=False)

    def get_fields(self) -> list[dict]:
        return json.loads(self.fields_json or "[]")

    def set_fields(self, data: list[dict]):
        self.fields_json = json.dumps(data or [], ensure_ascii=False)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json or "{}")

    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)


class ProviderSettingModel(SQLModel, table=True):
    __tablename__ = "provider_settings"
    __table_args__ = (
        UniqueConstraint("provider_type", "provider_key", name="uq_provider_settings_type_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    provider_type: str = Field(index=True)
    provider_key: str = Field(index=True)
    display_name: str = ""
    auth_mode: str = ""
    enabled: bool = True
    is_default: bool = False
    config_json: str = "{}"
    auth_json: str = "{}"
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_config(self) -> dict:
        return json.loads(self.config_json or "{}")

    def set_config(self, data: dict):
        self.config_json = json.dumps(data or {}, ensure_ascii=False)

    def get_auth(self) -> dict:
        return json.loads(self.auth_json or "{}")

    def set_auth(self, data: dict):
        self.auth_json = json.dumps(data or {}, ensure_ascii=False)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json or "{}")

    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)


class PlatformCapabilityOverrideModel(SQLModel, table=True):
    __tablename__ = "platform_capability_overrides"
    __table_args__ = (
        UniqueConstraint("platform_name", name="uq_platform_capability_overrides_platform"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    platform_name: str = Field(index=True)
    capabilities_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_capabilities(self) -> dict:
        return json.loads(self.capabilities_json or "{}")

    def set_capabilities(self, data: dict):
        self.capabilities_json = json.dumps(data or {}, ensure_ascii=False)


class TaskLog(SQLModel, table=True):
    __tablename__ = "task_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    email: str
    status: str        # success | failed
    error: str = ""
    detail_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)


class TaskModel(SQLModel, table=True):
    __tablename__ = "tasks"

    id: str = Field(primary_key=True)
    type: str = Field(index=True)
    platform: str = Field(default="", index=True)
    status: str = Field(default="pending", index=True)
    payload_json: str = "{}"
    result_json: str = "{}"
    progress_current: int = 0
    progress_total: int = 0
    success_count: int = 0
    error_count: int = 0
    error: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def get_payload(self) -> dict:
        return json.loads(self.payload_json or "{}")

    def set_payload(self, data: dict):
        self.payload_json = json.dumps(data or {}, ensure_ascii=False)

    def get_result(self) -> dict:
        return json.loads(self.result_json or "{}")

    def set_result(self, data: dict):
        self.result_json = json.dumps(data or {}, ensure_ascii=False)


class TaskEventModel(SQLModel, table=True):
    __tablename__ = "task_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    type: str = Field(default="log", index=True)
    level: str = "info"
    message: str = ""
    detail_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)

    def get_detail(self) -> dict:
        return json.loads(self.detail_json or "{}")

    def set_detail(self, data: dict):
        self.detail_json = json.dumps(data or {}, ensure_ascii=False)


class ProxyModel(SQLModel, table=True):
    __tablename__ = "proxies"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    region: str = ""
    success_count: int = 0
    fail_count: int = 0
    is_active: bool = True
    last_checked: Optional[datetime] = None


class SchemaVersionModel(SQLModel, table=True):
    __tablename__ = "schema_version"

    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(unique=True, index=True)
    applied_at: datetime = Field(default_factory=_utcnow)


def _migration_applied(session: Session, version: str) -> bool:
    """Check if a migration has already been applied."""
    existing = session.exec(
        select(SchemaVersionModel).where(SchemaVersionModel.version == version)
    ).first()
    return existing is not None


def _mark_migration_applied(session: Session, version: str) -> None:
    """Record that a migration has been applied."""
    session.add(SchemaVersionModel(version=version))
    session.commit()


def save_account(account) -> 'AccountModel':
    """Persist base_platform.Account to database (update if same platform and email)"""
    from core.account_graph import sync_platform_account_graph

    with Session(engine) as session:
        existing = session.exec(
            select(AccountModel)
            .where(AccountModel.platform == account.platform)
            .where(AccountModel.email == account.email)
        ).first()
        if existing:
            existing.password = encrypt_password(account.password)
            existing.user_id = account.user_id or ""
            existing.updated_at = _utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            sync_platform_account_graph(session, existing, account)
            session.commit()
            return existing
        m = AccountModel(
            platform=account.platform,
            email=account.email,
            password=encrypt_password(account.password),
            user_id=account.user_id or "",
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        sync_platform_account_graph(session, m, account)
        session.commit()
        return m


LEGACY_ACCOUNT_COLUMNS = (
    "region",
    "token",
    "status",
    "trial_end_time",
    "cashier_url",
    "extra_json",
)


def _load_json(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _accounts_columns() -> set[str]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "accounts" not in tables:
        return set()
    return {column["name"] for column in inspector.get_columns("accounts")}


def _migrate_legacy_accounts_schema() -> None:
    """Migrate legacy accounts table schema. Runs only once (tracked via schema_version)."""
    with Session(engine) as session:
        if _migration_applied(session, "legacy_accounts_schema_v1"):
            return

    columns = _accounts_columns()
    if not columns or not any(column in columns for column in LEGACY_ACCOUNT_COLUMNS):
        # No legacy columns — mark as applied to skip future checks
        with Session(engine) as session:
            _mark_migration_applied(session, "legacy_accounts_schema_v1")
        return

    from core.account_graph import sync_legacy_account_graph

    with engine.begin() as connection:
        rows = connection.exec_driver_sql(
            """
            SELECT
                id,
                platform,
                COALESCE(region, '') AS region,
                COALESCE(token, '') AS token,
                COALESCE(status, 'registered') AS status,
                COALESCE(trial_end_time, 0) AS trial_end_time,
                COALESCE(cashier_url, '') AS cashier_url,
                COALESCE(extra_json, '{}') AS extra_json
            FROM accounts
            """
        ).mappings().all()

    with Session(engine) as session:
        for row in rows:
            sync_legacy_account_graph(
                session,
                account_id=int(row["id"] or 0),
                platform=str(row["platform"] or ""),
                lifecycle_status=str(row["status"] or "registered"),
                region=str(row["region"] or ""),
                legacy_token=str(row["token"] or ""),
                trial_end_time=int(row["trial_end_time"] or 0),
                cashier_url=str(row["cashier_url"] or ""),
                extra=_load_json(str(row["extra_json"] or "{}")),
            )
        session.commit()

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql(
            """
            CREATE TABLE accounts__new (
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
        connection.exec_driver_sql(
            """
            INSERT INTO accounts__new (id, platform, email, password, user_id, created_at, updated_at)
            SELECT id, platform, email, password, user_id, created_at, updated_at
            FROM accounts
            """
        )
        connection.exec_driver_sql("DROP TABLE accounts")
        connection.exec_driver_sql("ALTER TABLE accounts__new RENAME TO accounts")
        connection.exec_driver_sql("CREATE INDEX ix_accounts_platform ON accounts (platform)")
        connection.exec_driver_sql("CREATE INDEX ix_accounts_email ON accounts (email)")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")

    with Session(engine) as session:
        _mark_migration_applied(session, "legacy_accounts_schema_v1")


def init_db():
    SQLModel.metadata.create_all(engine)
    from core.account_graph import sync_all_account_graphs
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository

    _migrate_legacy_accounts_schema()
    _ensure_column("provider_definitions", "category", "TEXT DEFAULT ''")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        ProviderDefinitionsRepository().ensure_seeded()
        _migrate_legacy_provider_keys()
        _cleanup_non_real_providers()
        _cleanup_empty_provider_settings()
        sync_all_account_graphs(session)
        session.commit()


def _ensure_column(table: str, column: str, col_type: str):
    """Safely add a column to an existing table (SQLite does not support IF NOT EXISTS ADD COLUMN).

    Validates table and column names against an allowlist to prevent SQL injection.
    """
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table name: {table!r}")
    if not _VALID_IDENTIFIER_RE.match(column):
        raise ValueError(f"Invalid column name: {column!r}")
    if not _VALID_IDENTIFIER_RE.match(col_type.split()[0]):
        raise ValueError(f"Invalid column type: {col_type!r}")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if table not in tables:
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    logger.info("Added column %s.%s", table, column)


def _cleanup_empty_provider_settings():
    """Clean up empty ProviderSettings auto-created by PR #42 in v1.0.7/v1.0.8.

    Condition: when config / auth / metadata are all empty dicts,
    AND the provider is disabled AND not default,
    the user never edited them and they can be safely deleted.
    After deletion, users can re-select the provider via the frontend "Add" button."""
    with Session(engine) as session:
        items = session.exec(select(ProviderSettingModel)).all()
        removed = 0
        for item in items:
            # Keep enabled/default providers even if config is empty —
            # user explicitly turned them on (e.g. free mail providers)
            if item.enabled or item.is_default:
                continue
            config = item.get_config() or {}
            auth = item.get_auth() or {}
            metadata = item.get_metadata() or {}
            if not config and not auth and not metadata:
                session.delete(item)
                removed += 1
        if removed:
            session.commit()


# Legacy provider_key → new provider_key mapping
_LEGACY_PROVIDER_KEY_MAP: dict[tuple[str, str], str] = {
    # mailbox
    ("mailbox", "moemail"): "moemail_api",
    ("mailbox", "generic_http"): "generic_http_mailbox",
    ("mailbox", "tempmail_lol"): "tempmail_lol_api",
    ("mailbox", "tempmail_web"): "tempmail_web_api",
    ("mailbox", "duckmail"): "duckmail_api",
    ("mailbox", "freemail"): "freemail_api",
    ("mailbox", "cfworker"): "cfworker_admin_api",
    ("mailbox", "testmail"): "testmail_api",
    ("mailbox", "laoudo"): "laoudo_api",
    ("mailbox", "mailtm"): "mailtm_api",
    # sms
    ("sms", "sms_activate"): "sms_activate_api",
    ("sms", "herosms"): "herosms_api",
    # captcha
    ("captcha", "yescaptcha"): "yescaptcha_api",
    ("captcha", "twocaptcha"): "twocaptcha_api",
}

# Legacy auth_mode → new auth_mode value mapping
_LEGACY_AUTH_MODE_MAP: dict[str, str] = {
    "endpoint_only": "password",
    "manual_login": "password",
    "bearer_token": "bearer",
    "jwt_token": "token",
    "admin_token": "token",
    "api_key": "apikey",
}


def _migrate_legacy_provider_keys():
    """Migrate legacy provider_key and auth_mode to new naming.

    Runs only once (tracked via schema_version).
    """
    with Session(engine) as session:
        if _migration_applied(session, "legacy_provider_keys_v1"):
            return

    with Session(engine) as session:
        migrated = 0

        # 1. Migrate provider_key
        for (ptype, old_key), new_key in _LEGACY_PROVIDER_KEY_MAP.items():
            # --- provider_settings ---
            old_setting = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == ptype)
                .where(ProviderSettingModel.provider_key == old_key)
            ).first()
            if old_setting:
                new_setting = session.exec(
                    select(ProviderSettingModel)
                    .where(ProviderSettingModel.provider_type == ptype)
                    .where(ProviderSettingModel.provider_key == new_key)
                ).first()
                if new_setting:
                    session.delete(old_setting)
                else:
                    old_setting.provider_key = new_key
                    session.add(old_setting)
                migrated += 1

            # --- provider_definitions ---
            old_defn = session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == ptype)
                .where(ProviderDefinitionModel.provider_key == old_key)
            ).first()
            if old_defn:
                new_defn = session.exec(
                    select(ProviderDefinitionModel)
                    .where(ProviderDefinitionModel.provider_type == ptype)
                    .where(ProviderDefinitionModel.provider_key == new_key)
                ).first()
                if new_defn:
                    session.delete(old_defn)
                else:
                    old_defn.provider_key = new_key
                    session.add(old_defn)
                migrated += 1

        if migrated:
            session.commit()
            logger.info("Migrated %d legacy provider keys", migrated)

        # 2. Fix auth_mode values
        fixed = 0
        all_settings = session.exec(select(ProviderSettingModel)).all()
        for item in all_settings:
            old_mode = item.auth_mode or ""
            if not old_mode:
                continue
            # Look up corresponding definition
            defn = session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == item.provider_type)
                .where(ProviderDefinitionModel.provider_key == item.provider_key)
            ).first()
            if not defn:
                continue
            valid_modes = {m.get("value") for m in defn.get_auth_modes()}
            if not valid_modes or old_mode in valid_modes:
                # Current value already valid, skip
                continue
            # Try mapping
            new_mode = _LEGACY_AUTH_MODE_MAP.get(old_mode)
            if new_mode and new_mode in valid_modes:
                item.auth_mode = new_mode
            elif defn.default_auth_mode:
                item.auth_mode = defn.default_auth_mode
            else:
                continue
            session.add(item)
            fixed += 1

        if fixed:
            session.commit()
            logger.info("Fixed %d legacy auth_mode entries", fixed)

        _mark_migration_applied(session, "legacy_provider_keys_v1")


def _cleanup_non_real_providers():
    """generic_http is not a real mailbox; remove its definition and empty settings from DB."""
    remove_keys = [("mailbox", "generic_http")]
    with Session(engine) as session:
        for pt, pk in remove_keys:
            setting = session.exec(
                select(ProviderSettingModel)
                .where(ProviderSettingModel.provider_type == pt)
                .where(ProviderSettingModel.provider_key == pk)
            ).first()
            if setting:
                config = setting.get_config() or {}
                auth = setting.get_auth() or {}
                if not config and not auth:
                    session.delete(setting)
            defn = session.exec(
                select(ProviderDefinitionModel)
                .where(ProviderDefinitionModel.provider_type == pt)
                .where(ProviderDefinitionModel.provider_key == pk)
            ).first()
            if defn:
                remaining = session.exec(
                    select(ProviderSettingModel)
                    .where(ProviderSettingModel.provider_type == pt)
                    .where(ProviderSettingModel.provider_key == pk)
                ).first()
                if not remaining:
                    session.delete(defn)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
