"""add version label and message

Revision ID: e3cb73b3a17b
Revises: 9a94ad7baf70
Create Date: 2026-07-21 05:04:59.117956

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3cb73b3a17b'
down_revision: Union[str, Sequence[str], None] = '9a94ad7baf70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('versions', sa.Column('label', sa.String(length=128), nullable=True))
    op.add_column('versions', sa.Column('message', sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('versions', 'message')
    op.drop_column('versions', 'label')
