"""Add organization aws_region and public read

Revision ID: 8fa19dcad1d1
Revises: f8eeb27a49e7
Create Date: 2022-03-25 13:46:29.088536
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8fa19dcad1d1"
down_revision = "f8eeb27a49e7"


def upgrade():
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("aws_region", sa.Unicode(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("bucket_public_read", sa.Boolean(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_column("bucket_public_read")
        batch_op.drop_column("aws_region")
