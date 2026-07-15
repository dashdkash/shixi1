"""add reset verification code fields

Revision ID: 75482e6a5b04
Revises: a2c0fc98b203
Create Date: 2026-07-15 15:22:11.697015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '75482e6a5b04'
down_revision: Union[str, Sequence[str], None] = 'a2c0fc98b203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('reset_verification_code', sa.String(length=10), nullable=True, comment='密码重置验证码'))
    op.add_column('users', sa.Column('reset_verification_code_expires_at', sa.DateTime(), nullable=True, comment='验证码过期时间'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'reset_verification_code_expires_at')
    op.drop_column('users', 'reset_verification_code')