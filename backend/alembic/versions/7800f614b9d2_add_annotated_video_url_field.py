"""add annotated_video_url field

Revision ID: 7800f614b9d2
Revises: 75482e6a5b04
Create Date: 2026-07-15 19:17:28.768213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7800f614b9d2'
down_revision: Union[str, Sequence[str], None] = '75482e6a5b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('detection_tasks', sa.Column('annotated_video_url', sa.String(length=500), nullable=True, comment='标注视频 URL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('detection_tasks', 'annotated_video_url')
