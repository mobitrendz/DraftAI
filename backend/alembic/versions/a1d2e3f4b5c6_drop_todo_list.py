"""Drop demo todo_list table removed in DraftAI Sprint 0."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1d2e3f4b5c6"
down_revision: str | Sequence[str] | None = "fbe7be3bfe7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_todo_list_user_id"), table_name="todo_list")
    op.drop_table("todo_list")
    sa.Enum(name="todopriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="todostatus").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    import sqlmodel

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
