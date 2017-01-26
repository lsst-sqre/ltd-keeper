"""Add surrogate_key to product

Revision ID: ffdd80058eed
Revises: 0c0c70d73d4b
Create Date: 2017-01-25 16:59:17.456605
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ffdd80058eed'
down_revision = '0c0c70d73d4b'


def upgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('surrogate_key',
                                      sa.String(length=32),
                                      nullable=True))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('surrogate_key')
