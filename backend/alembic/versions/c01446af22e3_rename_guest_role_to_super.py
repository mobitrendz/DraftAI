"""rename guest role to super

Revision ID: c01446af22e3
Revises: 2f30471845e6
Create Date: 2026-05-09 18:40:28.582355

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c01446af22e3"
down_revision: str | Sequence[str] | None = "2f30471845e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename 'guest', 'GUEST', or 'super' to 'SUPER' in the userrole enum
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'userrole' AND e.enumlabel = 'guest') THEN
                ALTER TYPE userrole RENAME VALUE 'guest' TO 'SUPER';
            ELSIF EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'userrole' AND e.enumlabel = 'GUEST') THEN
                ALTER TYPE userrole RENAME VALUE 'GUEST' TO 'SUPER';
            ELSIF EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'userrole' AND e.enumlabel = 'super') THEN
                ALTER TYPE userrole RENAME VALUE 'super' TO 'SUPER';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    # Rename 'SUPER' back to 'GUEST'
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'userrole' AND e.enumlabel = 'SUPER') THEN
                ALTER TYPE userrole RENAME VALUE 'SUPER' TO 'GUEST';
            ELSIF EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'userrole' AND e.enumlabel = 'super') THEN
                ALTER TYPE userrole RENAME VALUE 'super' TO 'GUEST';
            END IF;
        END
        $$;
    """)
