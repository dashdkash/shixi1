"""add source_task_id column for resume training

Revision ID: add_source_task_id
Revises: 510febb52ba6
Create Date: 2026-07-13 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_source_task_id'
down_revision: Union[str, None] = '510febb52ba6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'training_tasks',
        sa.Column(
            'source_task_id',
            sa.Integer(),
            nullable=True,
            comment='续训来源任务ID',
        ),
    )
    op.create_foreign_key(
        'fk_training_tasks_source_task_id',
        'training_tasks',
        'training_tasks',
        ['source_task_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_training_tasks_source_task_id'),
        'training_tasks',
        ['source_task_id'],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_training_tasks_source_task_id'), table_name='training_tasks')
    op.drop_constraint('fk_training_tasks_source_task_id', 'training_tasks', type_='foreignkey')
    op.drop_column('training_tasks', 'source_task_id')