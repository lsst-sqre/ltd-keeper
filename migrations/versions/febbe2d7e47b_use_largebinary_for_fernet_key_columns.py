"""Use LargeBinary for fernet key columns.

Revision ID: febbe2d7e47b
Revises: 8c431c5e70a8
Create Date: 2022-03-19 11:40:07.203662
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "febbe2d7e47b"
down_revision = "8c431c5e70a8"


def upgrade():
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_column("fastly_encrypted_api_key")
        batch_op.drop_column("aws_encrypted_secret_key")

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "fastly_encrypted_api_key", sa.LargeBinary(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "aws_encrypted_secret_key", sa.LargeBinary(), nullable=True
            )
        )


def downgrade():
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_column("fastly_encrypted_api_key")
        batch_op.drop_column("aws_encrypted_secret_key")

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "fastly_encrypted_api_key",
                sa.VARCHAR(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "aws_encrypted_secret_key",
                sa.VARCHAR(length=255),
                nullable=True,
            )
        )
