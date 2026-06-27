"""core.db package — re-exports everything for backward compatibility."""

from core.db.encryption import (
    decrypt_password,
    encrypt_password,
)
from core.db.engine import (
    DATABASE_URL,
    _create_async_engine,
    _create_sync_engine,
    _ensure_column,
    _is_postgresql,
    engine,
    get_session,
    init_db,
    save_account,
)
from core.db.migrations import (
    LEGACY_ACCOUNT_COLUMNS,
    _cleanup_empty_provider_settings,
    _cleanup_non_real_providers,
    _migrate_legacy_accounts_schema,
    _migrate_legacy_provider_keys,
)
from core.db.models import (
    AccountCredentialModel,
    AccountModel,
    AccountOverviewModel,
    PlatformCapabilityOverrideModel,
    ProxyModel,
    ProviderAccountModel,
    ProviderDefinitionModel,
    ProviderResourceModel,
    ProviderSettingModel,
    SchemaVersionModel,
    TaskEventModel,
    TaskLog,
    TaskModel,
    _VALID_IDENTIFIER_RE,
    _VALID_TABLES,
)

__all__ = [
    # encryption
    "decrypt_password",
    "encrypt_password",
    # engine
    "_create_async_engine",
    "_create_sync_engine",
    "_is_postgresql",
    "DATABASE_URL",
    "engine",
    "get_session",
    "init_db",
    "save_account",
    # migrations
    "LEGACY_ACCOUNT_COLUMNS",
    "_cleanup_empty_provider_settings",
    "_cleanup_non_real_providers",
    "_ensure_column",
    "_migrate_legacy_accounts_schema",
    "_migrate_legacy_provider_keys",
    # models
    "AccountCredentialModel",
    "AccountModel",
    "AccountOverviewModel",
    "PlatformCapabilityOverrideModel",
    "ProxyModel",
    "ProviderAccountModel",
    "ProviderDefinitionModel",
    "ProviderResourceModel",
    "ProviderSettingModel",
    "SchemaVersionModel",
    "TaskEventModel",
    "TaskLog",
    "TaskModel",
    "_VALID_IDENTIFIER_RE",
    "_VALID_TABLES",
]
