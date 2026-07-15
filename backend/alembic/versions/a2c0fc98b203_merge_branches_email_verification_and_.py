"""merge branches: email verification and knowledge tables

Revision ID: a2c0fc98b203
Revises: c3d4e5f6g7h8, f1466777177b
Create Date: 2026-07-15 11:17:20.104501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c0fc98b203'
down_revision: Union[str, Sequence[str], None] = ('c3d4e5f6g7h8', 'f1466777177b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
