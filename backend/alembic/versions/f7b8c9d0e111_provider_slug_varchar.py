"""convert ai_agent_config.provider from enum to varchar

Revision ID: f7b8c9d0e111
Revises: e6a7b8c9d010
Create Date: 2026-06-15 26:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7b8c9d0e111"
down_revision: Union[str, Sequence[str], None] = "e6a7b8c9d010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE ai_agent_config ALTER COLUMN provider TYPE VARCHAR(64)")
    op.execute("DROP TYPE IF EXISTS aiprovider")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE aiprovider AS ENUM "
        "('openai', 'anthropic', 'gemini', 'groq', 'openrouter')"
    )
    op.execute(
        "ALTER TABLE ai_agent_config "
        "ALTER COLUMN provider TYPE aiprovider "
        "USING provider::aiprovider"
    )
