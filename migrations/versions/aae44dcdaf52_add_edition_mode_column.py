"""Add Edition.mode column

Revision ID: aae44dcdaf52
Revises: ffdd80058eed
Create Date: 2017-11-17 11:12:43.148696
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aae44dcdaf52"
down_revision = "ffdd80058eed"


def upgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mode", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.drop_column("mode")
