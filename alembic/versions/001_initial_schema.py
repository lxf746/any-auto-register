"""Initial schema — all 13 SQLModel tables.

Revision ID: 001
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── accounts ──────────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_platform", "accounts", ["platform"])
    op.create_index("ix_accounts_email", "accounts", ["email"])

    # ── account_overviews ─────────────────────────────────────────────
    op.create_table(
        "account_overviews",
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            primary_key=True,
        ),
        sa.Column("lifecycle_status", sa.String(), server_default="registered"),
        sa.Column("validity_status", sa.String(), server_default="unknown"),
        sa.Column("plan_state", sa.String(), server_default="unknown"),
        sa.Column("plan_name", sa.String(), server_default=""),
        sa.Column("display_status", sa.String(), server_default="registered"),
        sa.Column("remote_email", sa.String(), server_default=""),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_account_overviews_lifecycle_status",
        "account_overviews",
        ["lifecycle_status"],
    )
    op.create_index(
        "ix_account_overviews_validity_status",
        "account_overviews",
        ["validity_status"],
    )
    op.create_index(
        "ix_account_overviews_plan_state",
        "account_overviews",
        ["plan_state"],
    )
    op.create_index(
        "ix_account_overviews_display_status",
        "account_overviews",
        ["display_status"],
    )

    # ── account_credentials ───────────────────────────────────────────
    op.create_table(
        "account_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(), server_default="platform"),
        sa.Column("provider_name", sa.String(), server_default=""),
        sa.Column("credential_type", sa.String(), server_default="secret"),
        sa.Column("key", sa.String(), server_default=""),
        sa.Column("value", sa.String(), server_default=""),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("source", sa.String(), server_default=""),
        sa.Column("metadata_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_account_credentials_account_id",
        "account_credentials",
        ["account_id"],
    )
    op.create_index("ix_account_credentials_scope", "account_credentials", ["scope"])
    op.create_index(
        "ix_account_credentials_provider_name",
        "account_credentials",
        ["provider_name"],
    )
    op.create_index(
        "ix_account_credentials_credential_type",
        "account_credentials",
        ["credential_type"],
    )
    op.create_index("ix_account_credentials_key", "account_credentials", ["key"])

    # ── provider_accounts ─────────────────────────────────────────────
    op.create_table(
        "provider_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("provider_type", sa.String(), server_default="mailbox"),
        sa.Column("provider_name", sa.String(), server_default=""),
        sa.Column("login_identifier", sa.String(), server_default=""),
        sa.Column("display_name", sa.String(), server_default=""),
        sa.Column("credentials_json", sa.String(), server_default="{}"),
        sa.Column("metadata_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_provider_accounts_account_id", "provider_accounts", ["account_id"]
    )
    op.create_index(
        "ix_provider_accounts_provider_type",
        "provider_accounts",
        ["provider_type"],
    )
    op.create_index(
        "ix_provider_accounts_provider_name",
        "provider_accounts",
        ["provider_name"],
    )
    op.create_index(
        "ix_provider_accounts_login_identifier",
        "provider_accounts",
        ["login_identifier"],
    )

    # ── provider_resources ────────────────────────────────────────────
    op.create_table(
        "provider_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("provider_type", sa.String(), server_default="mailbox"),
        sa.Column("provider_name", sa.String(), server_default=""),
        sa.Column("resource_type", sa.String(), server_default="resource"),
        sa.Column("resource_identifier", sa.String(), server_default=""),
        sa.Column("handle", sa.String(), server_default=""),
        sa.Column("display_name", sa.String(), server_default=""),
        sa.Column("metadata_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_provider_resources_account_id", "provider_resources", ["account_id"]
    )
    op.create_index(
        "ix_provider_resources_provider_type",
        "provider_resources",
        ["provider_type"],
    )
    op.create_index(
        "ix_provider_resources_provider_name",
        "provider_resources",
        ["provider_name"],
    )
    op.create_index(
        "ix_provider_resources_resource_type",
        "provider_resources",
        ["resource_type"],
    )
    op.create_index(
        "ix_provider_resources_resource_identifier",
        "provider_resources",
        ["resource_identifier"],
    )

    # ── provider_definitions ──────────────────────────────────────────
    op.create_table(
        "provider_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("provider_key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), server_default=""),
        sa.Column("description", sa.String(), server_default=""),
        sa.Column("driver_type", sa.String(), server_default=""),
        sa.Column("default_auth_mode", sa.String(), server_default=""),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("category", sa.String(), server_default=""),
        sa.Column("auth_modes_json", sa.String(), server_default="[]"),
        sa.Column("fields_json", sa.String(), server_default="[]"),
        sa.Column("metadata_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_type", "provider_key", name="uq_provider_definitions_type_key"
        ),
    )
    op.create_index(
        "ix_provider_definitions_provider_type",
        "provider_definitions",
        ["provider_type"],
    )
    op.create_index(
        "ix_provider_definitions_provider_key",
        "provider_definitions",
        ["provider_key"],
    )

    # ── provider_settings ─────────────────────────────────────────────
    op.create_table(
        "provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("provider_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), server_default=""),
        sa.Column("auth_mode", sa.String(), server_default=""),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("config_json", sa.String(), server_default="{}"),
        sa.Column("auth_json", sa.String(), server_default="{}"),
        sa.Column("metadata_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_type", "provider_key", name="uq_provider_settings_type_key"
        ),
    )
    op.create_index(
        "ix_provider_settings_provider_type",
        "provider_settings",
        ["provider_type"],
    )
    op.create_index(
        "ix_provider_settings_provider_key",
        "provider_settings",
        ["provider_key"],
    )

    # ── platform_capability_overrides ─────────────────────────────────
    op.create_table(
        "platform_capability_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("capabilities_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "platform_name",
            name="uq_platform_capability_overrides_platform",
        ),
    )
    op.create_index(
        "ix_platform_capability_overrides_platform_name",
        "platform_capability_overrides",
        ["platform_name"],
    )

    # ── task_logs ─────────────────────────────────────────────────────
    op.create_table(
        "task_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.String(), server_default=""),
        sa.Column("detail_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tasks ─────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), server_default=""),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("payload_json", sa.String(), server_default="{}"),
        sa.Column("result_json", sa.String(), server_default="{}"),
        sa.Column("progress_current", sa.Integer(), server_default=sa.text("0")),
        sa.Column("progress_total", sa.Integer(), server_default=sa.text("0")),
        sa.Column("success_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("error", sa.String(), server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tasks_type", "tasks", ["type"])
    op.create_index("ix_tasks_platform", "tasks", ["platform"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # ── task_events ───────────────────────────────────────────────────
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), server_default="log"),
        sa.Column("level", sa.String(), server_default="info"),
        sa.Column("message", sa.String(), server_default=""),
        sa.Column("detail_json", sa.String(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_events_task_id", "task_events", ["task_id"])
    op.create_index("ix_task_events_type", "task_events", ["type"])

    # ── proxies ───────────────────────────────────────────────────────
    op.create_table(
        "proxies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("region", sa.String(), server_default=""),
        sa.Column("success_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("fail_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=True),
    )

    # ── schema_version ────────────────────────────────────────────────
    op.create_table(
        "schema_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(), nullable=False, unique=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schema_version_version", "schema_version", ["version"])


def downgrade() -> None:
    op.drop_table("schema_version")
    op.drop_table("proxies")
    op.drop_table("task_events")
    op.drop_table("tasks")
    op.drop_table("task_logs")
    op.drop_table("platform_capability_overrides")
    op.drop_table("provider_settings")
    op.drop_table("provider_definitions")
    op.drop_table("provider_resources")
    op.drop_table("provider_accounts")
    op.drop_table("account_credentials")
    op.drop_table("account_overviews")
    op.drop_table("accounts")
