"""add proposal title and description

Revision ID: 0f88c253aaf0
Revises: e3cb73b3a17b
Create Date: 2026-07-21 05:37:07.756240

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0f88c253aaf0'
down_revision: Union[str, Sequence[str], None] = 'e3cb73b3a17b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('proposals', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('proposals', sa.Column('description', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('proposals', 'description')
    op.drop_column('proposals', 'title')
