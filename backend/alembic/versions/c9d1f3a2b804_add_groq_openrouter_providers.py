"""add_groq_openrouter_providers

Revision ID: c9d1f3a2b804
Revises: b8c4e2f1a903
Create Date: 2026-06-15 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c9d1f3a2b804"
down_revision: Union[str, Sequence[str], None] = "b8c4e2f1a903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'groq'")
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'openrouter'")
    op.add_column(
        "ai_agent_config",
        sa.Column(
            "groq_api_key_encrypted",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
    )
    op.add_column(
        "ai_agent_config",
        sa.Column(
            "openrouter_api_key_encrypted",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_agent_config", "openrouter_api_key_encrypted")
    op.drop_column("ai_agent_config", "groq_api_key_encrypted")
