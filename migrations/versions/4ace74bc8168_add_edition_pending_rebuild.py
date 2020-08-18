"""Add Edition.pending_rebuild

Revision ID: 4ace74bc8168
Revises: aae44dcdaf52
Create Date: 2018-04-21 14:35:28.865972
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4ace74bc8168"
down_revision = "aae44dcdaf52"


def upgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "pending_rebuild",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.drop_column("pending_rebuild")
