"""allow user-owned custom AI providers

Revision ID: a9b0c1d2e334
Revises: f8c9d0e112aa
Create Date: 2026-06-15 28:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e334"
down_revision: Union[str, Sequence[str], None] = "f8c9d0e112aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ai_provider_user_custom_slug_uidx",
        "ai_provider",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text(
            "user_id IS NOT NULL AND parent_provider_id IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("ai_provider_user_custom_slug_uidx", table_name="ai_provider")
