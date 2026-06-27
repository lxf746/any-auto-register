"""SQLModel table definitions."""
import json
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from core.datetime_utils import _utcnow


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


# ---------------------------------------------------------------------------
# Table models
# ---------------------------------------------------------------------------


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
