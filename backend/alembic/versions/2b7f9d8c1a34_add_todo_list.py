"""Add todo list

Revision ID: 2b7f9d8c1a34
Revises: 9898d21271e3
Create Date: 2026-05-04 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b7f9d8c1a34"
down_revision: str | Sequence[str] | None = "9898d21271e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "todo_list",
        sa.Column(
            "title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False
        ),
        sa.Column(
            "description",
            sqlmodel.sql.sqltypes.AutoString(length=1000),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                name="todostatus",
            ),
            nullable=False,
        ),
        sa.Column("due_date_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("HIGH", "MEDIUM", "LOW", name="todopriority"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_todo_list_user_id"), "todo_list", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_todo_list_user_id"), table_name="todo_list")
    op.drop_table("todo_list")
    sa.Enum(name="todopriority").drop(op.get_bind())
    sa.Enum(name="todostatus").drop(op.get_bind())
