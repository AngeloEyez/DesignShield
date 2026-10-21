"""add is_mp_mode to drc_tasks

Revision ID: e71b2d398f01
Revises: da56c5887e04
Create Date: 2026-10-20 08:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e71b2d398f01'
down_revision: Union[str, Sequence[str], None] = 'da56c5887e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'drc_tasks',
        sa.Column('is_mp_mode', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drc_tasks', 'is_mp_mode')
