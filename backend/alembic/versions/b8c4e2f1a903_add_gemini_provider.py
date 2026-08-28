"""add_gemini_provider

Revision ID: b8c4e2f1a903
Revises: 030cb1d54852
Create Date: 2026-06-15 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c4e2f1a903"
down_revision: Union[str, Sequence[str], None] = "030cb1d54852"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'gemini'")
    op.add_column(
        "ai_agent_config",
        sa.Column(
            "gemini_api_key_encrypted",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_agent_config", "gemini_api_key_encrypted")
    # PostgreSQL does not support removing enum values without recreating the type.
