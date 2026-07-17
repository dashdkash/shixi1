"""merge_all_branches

Revision ID: dcc694724965
Revises: 7800f614b9d2, add_source_task_id
Create Date: 2026-07-16 19:43:52.320436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcc694724965'
down_revision: Union[str, Sequence[str], None] = ('7800f614b9d2', 'add_source_task_id')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
