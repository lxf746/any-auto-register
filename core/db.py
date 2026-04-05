"""数据库模型 - SQLite via SQLModel"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import UniqueConstraint, inspect
from sqlmodel import Field, SQLModel, create_engine, Session, select
import json


def _utcnow():
    return datetime.now(timezone.utc)

DATABASE_URL = "sqlite:///account_manager.db"
engine = create_engine(DATABASE_URL)


class AccountModel(SQLModel, table=True):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("platform", "email", name="uq_accounts_platform_email"),
    )

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


def save_account(account) -> 'AccountModel':
    """从 base_platform.Account 存入数据库（同平台同邮箱则更新）"""
    from core.account_graph import sync_platform_account_graph

    with Session(engine) as session:
        existing = session.exec(
            select(AccountModel)
            .where(AccountModel.platform == account.platform)
            .where(AccountModel.email == account.email)
        ).first()
        if existing:
            existing.password = account.password
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
            password=account.password,
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


def _accounts_has_platform_email_unique() -> bool:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "accounts" not in tables:
        return False

    expected = ["platform", "email"]
    for item in inspector.get_unique_constraints("accounts"):
        columns = list(item.get("column_names") or [])
        if columns == expected:
            return True
    for item in inspector.get_indexes("accounts"):
        if not item.get("unique"):
            continue
        columns = list(item.get("column_names") or [])
        if columns == expected:
            return True
    return False


def _dedupe_accounts_platform_email() -> None:
    # Keep the newest id for each (platform, email) pair and merge child rows to it.
    with Session(engine) as session:
        accounts = session.exec(select(AccountModel).order_by(AccountModel.id.desc())).all()
        keeper_by_key: dict[tuple[str, str], int] = {}
        remaps: list[tuple[int, int]] = []
        for account in accounts:
            source_id = int(account.id or 0)
            if source_id <= 0:
                continue
            key = (str(account.platform or ""), str(account.email or ""))
            target_id = keeper_by_key.get(key, 0)
            if target_id <= 0:
                keeper_by_key[key] = source_id
                continue
            remaps.append((source_id, target_id))

        if not remaps:
            return

        for source_id, target_id in remaps:
            if source_id == target_id:
                continue

            source_overview = session.get(AccountOverviewModel, source_id)
            target_overview = session.get(AccountOverviewModel, target_id)
            if source_overview:
                if target_overview:
                    session.delete(source_overview)
                else:
                    source_overview.account_id = target_id
                    session.add(source_overview)

            credentials = session.exec(
                select(AccountCredentialModel).where(AccountCredentialModel.account_id == source_id)
            ).all()
            for row in credentials:
                row.account_id = target_id
                session.add(row)

            provider_accounts = session.exec(
                select(ProviderAccountModel).where(ProviderAccountModel.account_id == source_id)
            ).all()
            for row in provider_accounts:
                row.account_id = target_id
                session.add(row)

            provider_resources = session.exec(
                select(ProviderResourceModel).where(ProviderResourceModel.account_id == source_id)
            ).all()
            for row in provider_resources:
                row.account_id = target_id
                session.add(row)

            duplicate = session.get(AccountModel, source_id)
            if duplicate:
                session.delete(duplicate)

        session.commit()


def _ensure_accounts_platform_email_unique() -> None:
    _dedupe_accounts_platform_email()
    if _accounts_has_platform_email_unique():
        return

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_platform_email ON accounts (platform, email)"
        )


def _migrate_legacy_accounts_schema() -> None:
    columns = _accounts_columns()
    if not columns or not any(column in columns for column in LEGACY_ACCOUNT_COLUMNS):
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
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_accounts_platform_email UNIQUE (platform, email)
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


def init_db():
    SQLModel.metadata.create_all(engine)
    from core.account_graph import sync_all_account_graphs
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository

    _migrate_legacy_accounts_schema()
    _ensure_accounts_platform_email_unique()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        ProviderDefinitionsRepository().ensure_seeded()
        sync_all_account_graphs(session)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
