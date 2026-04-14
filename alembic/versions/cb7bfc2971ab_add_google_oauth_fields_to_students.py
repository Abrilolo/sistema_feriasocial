"""add google oauth fields to students

Revision ID: cb7bfc2971ab
Revises: 9f981c4ae365
Create Date: 2026-04-13 16:28:12.451215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb7bfc2971ab'
down_revision: Union[str, Sequence[str], None] = '9f981c4ae365'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add Google OAuth fields to students table."""
    # Agregar columna career (faltaba en migración original)
    op.add_column('students', sa.Column('career', sa.String(length=50), nullable=True))

    # Agregar columnas para autenticación con Google
    op.add_column('students', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.add_column('students', sa.Column('picture_url', sa.String(length=512), nullable=True))

    # Crear índice único para google_id
    op.create_index(op.f('ix_students_google_id'), 'students', ['google_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema - remove Google OAuth fields."""
    # Eliminar índice
    op.drop_index(op.f('ix_students_google_id'), table_name='students')

    # Eliminar columnas
    op.drop_column('students', 'picture_url')
    op.drop_column('students', 'google_id')
    op.drop_column('students', 'career')
