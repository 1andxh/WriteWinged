"""add document category

Revision ID: a38924a1f3fe
Revises: 0f88c253aaf0
Create Date: 2026-07-21 06:09:23.429050

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a38924a1f3fe'
down_revision: Union[str, Sequence[str], None] = '0f88c253aaf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('documents', sa.Column('category', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'category')
