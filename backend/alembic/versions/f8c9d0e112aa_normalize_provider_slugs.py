"""normalize legacy uppercase provider slugs

Revision ID: f8c9d0e112aa
Revises: f7b8c9d0e111
Create Date: 2026-06-15 27:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "f8c9d0e112aa"
down_revision: Union[str, Sequence[str], None] = "f7b8c9d0e111"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE ai_agent_config SET provider = lower(provider)")


def downgrade() -> None:
    pass
