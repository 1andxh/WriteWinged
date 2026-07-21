"""add comments table

Revision ID: 9a94ad7baf70
Revises: 012df0ad1e19
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9a94ad7baf70'
down_revision: Union[str, Sequence[str], None] = '012df0ad1e19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('proposal_id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('inline', sa.Boolean(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.CheckConstraint(
            'length(text) > 0 AND length(text) <= 2000', name='chk_comment_text_length'
        ),
        sa.CheckConstraint(
            'inline = FALSE OR line_number IS NOT NULL',
            name='chk_comment_line_number_required_if_inline',
        ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_comments_author_id'), 'comments', ['author_id'], unique=False
    )
    op.create_index(
        op.f('ix_comments_created_at'), 'comments', ['created_at'], unique=False
    )
    op.create_index(
        op.f('ix_comments_proposal_id'), 'comments', ['proposal_id'], unique=False
    )
    op.create_index(
        'ix_comments_proposal_unresolved',
        'comments',
        ['proposal_id', 'resolved'],
        unique=False,
        postgresql_where=sa.text('resolved = false'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_comments_proposal_unresolved', table_name='comments')
    op.drop_index(op.f('ix_comments_proposal_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_created_at'), table_name='comments')
    op.drop_index(op.f('ix_comments_author_id'), table_name='comments')
    op.drop_table('comments')
