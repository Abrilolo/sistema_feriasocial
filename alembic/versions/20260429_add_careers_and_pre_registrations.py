"""add careers and pre_registrations tables

Revision ID: 20260429001
Revises: dde89a55ea07
Create Date: 2026-04-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260429001'
down_revision: Union[str, Sequence[str], None] = 'dde89a55ea07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create careers table
    op.create_table('careers',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('nombre_carrera', sa.String(length=255), nullable=False),
    sa.Column('siglas', sa.String(length=50), nullable=False),
    sa.Column('escuela', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_careers_siglas'), 'careers', ['siglas'], unique=True)

    # Create pre_registrations table
    op.create_table('pre_registrations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('matricula', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('career_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['career_id'], ['careers.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pre_registrations_matricula'), 'pre_registrations', ['matricula'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pre_registrations_matricula'), table_name='pre_registrations')
    op.drop_table('pre_registrations')
    op.drop_index(op.f('ix_careers_siglas'), table_name='careers')
    op.drop_table('careers')
