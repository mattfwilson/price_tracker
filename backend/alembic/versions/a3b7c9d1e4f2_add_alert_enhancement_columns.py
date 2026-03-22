"""add alert enhancement columns

Revision ID: a3b7c9d1e4f2
Revises: 6e00987c7dbb
Create Date: 2026-03-22 22:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b7c9d1e4f2'
down_revision: Union[str, Sequence[str], None] = '6e00987c7dbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pct_drop_threshold, alert_cooldown_hours to watch_queries; alert_type to alerts."""
    with op.batch_alter_table('watch_queries') as batch_op:
        batch_op.add_column(sa.Column('pct_drop_threshold', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('alert_cooldown_hours', sa.Integer(), server_default='24', nullable=False))

    with op.batch_alter_table('alerts') as batch_op:
        batch_op.add_column(sa.Column('alert_type', sa.String(50), server_default='threshold', nullable=False))


def downgrade() -> None:
    """Remove alert enhancement columns."""
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.drop_column('alert_type')

    with op.batch_alter_table('watch_queries') as batch_op:
        batch_op.drop_column('alert_cooldown_hours')
        batch_op.drop_column('pct_drop_threshold')
