"""add_cover_image_model

Revision ID: d4e5f6a7b809
Revises: c9d1f3a2b804
Create Date: 2026-06-15 24:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "d4e5f6a7b809"
down_revision: Union[str, Sequence[str], None] = "c9d1f3a2b804"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_agent_config",
        sa.Column(
            "cover_image_model",
            sqlmodel.sql.sqltypes.AutoString(length=128),
            nullable=False,
            server_default="gemini-3-pro-image",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_agent_config", "cover_image_model")
