"""add password reset fields to users

Revision ID: b2c3d4e5f6g7
Revises: ed14438701a2
Create Date: 2026-07-14 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'ed14438701a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 reset_token 字段
    op.add_column('users', sa.Column('reset_token', sa.String(length=100), nullable=True, comment='密码重置令牌'))
    # 添加 reset_token_expires_at 字段
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True, comment='重置令牌过期时间'))
    # 为 reset_token 创建索引
    op.create_index(op.f('ix_users_reset_token'), 'users', ['reset_token'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除索引
    op.drop_index(op.f('ix_users_reset_token'), table_name='users')
    # 删除字段
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token')
