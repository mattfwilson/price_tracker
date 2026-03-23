"""add scrape_url_attempts table

Revision ID: b5e1f3a8c7d9
Revises: a3b7c9d1e4f2
Create Date: 2026-03-23 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e1f3a8c7d9'
down_revision: Union[str, Sequence[str], None] = 'a3b7c9d1e4f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create scrape_url_attempts table with composite index."""
    op.create_table(
        'scrape_url_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('retailer_url_id', sa.Integer(), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('is_success', sa.Boolean(), default=False, nullable=False),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['retailer_url_id'], ['retailer_urls.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_scrape_url_attempts_url_time',
        'scrape_url_attempts',
        ['retailer_url_id', sa.text('scraped_at DESC')],
    )


def downgrade() -> None:
    """Drop scrape_url_attempts table."""
    op.drop_index('ix_scrape_url_attempts_url_time', table_name='scrape_url_attempts')
    op.drop_table('scrape_url_attempts')
