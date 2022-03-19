"""Add Edition tracked_ref column

Revision ID: f8eeb27a49e7
Revises: febbe2d7e47b
Create Date: 2022-03-19 18:02:05.929442
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f8eeb27a49e7"
down_revision = "febbe2d7e47b"


def upgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tracked_ref", sa.Unicode(length=255), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.drop_column("tracked_ref")
