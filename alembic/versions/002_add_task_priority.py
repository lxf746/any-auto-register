"""Add priority column to tasks table.

Revision ID: 002
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("priority", sa.String(), server_default="normal"),
    )
    op.create_index("ix_tasks_priority", "tasks", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_tasks_priority", "tasks")
    op.drop_column("tasks", "priority")
