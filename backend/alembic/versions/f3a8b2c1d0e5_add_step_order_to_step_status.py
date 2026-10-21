"""add step_order to step_status

Revision ID: f3a8b2c1d0e5
Revises: e71b2d398f01
Create Date: 2026-10-20 10:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a8b2c1d0e5'
down_revision: Union[str, Sequence[str], None] = 'e71b2d398f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'step_status',
        sa.Column('step_order', sa.Integer(), server_default='1', nullable=False)
    )
    op.create_index(op.f('ix_step_status_step_order'), 'step_status', ['step_order'], unique=False)
    # 依步驟名稱更新對應 step_order 序號 (1~6)
    op.execute("""
        UPDATE step_status SET step_order = CASE step_name
            WHEN 'UNPACK_AND_VALIDATE' THEN 1
            WHEN 'PARSE_AND_GRAPH' THEN 2
            WHEN 'RULE_SELECTION' THEN 3
            WHEN 'HEURISTIC_CHECK' THEN 4
            WHEN 'LLM_REASONING' THEN 5
            WHEN 'GENERATE_REPORT' THEN 6
            ELSE 1
        END;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_step_status_step_order'), table_name='step_status')
    op.drop_column('step_status', 'step_order')
