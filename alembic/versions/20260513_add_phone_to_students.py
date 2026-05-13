"""add phone to students

Revision ID: 20260513001
Revises: 20260429001
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260513001"
down_revision: Union[str, Sequence[str], None] = "20260429001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("students", sa.Column("phone", sa.String(length=20), nullable=True))
    op.execute("""
        UPDATE students
        SET phone = pre_registrations.phone
        FROM pre_registrations
        WHERE students.phone IS NULL
          AND (
            students.email = pre_registrations.email
            OR students.matricula = pre_registrations.matricula
          )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("students", "phone")
