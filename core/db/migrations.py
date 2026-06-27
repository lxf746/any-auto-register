"""Database migration logic."""
import logging

from sqlmodel import Session, select

from core.db.engine import (
    _accounts_columns,
    _load_json,
    engine,
)
from core.db.models import (
    ProviderDefinitionModel,
    ProviderSettingModel,
    SchemaVersionModel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Migration tracking
# ---------------------------------------------------------------------------

LEGACY_ACCOUNT_COLUMNS = (
    "region",
    "token",
    "status",
    "trial_end_time",
    "cashier_url",
    "extra_json",
)

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


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


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
