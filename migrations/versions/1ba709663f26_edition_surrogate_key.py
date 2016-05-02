"""edition surrogate key

Revision ID: 1ba709663f26
Revises: d9a390ebdf1e
Create Date: 2016-04-29 15:59:12.144102

"""

# revision identifiers, used by Alembic.
revision = '1ba709663f26'
down_revision = 'd9a390ebdf1e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('editions', sa.Column('surrogate_key', sa.String(length=32)))


def downgrade():
    op.drop_column('editions', 'surrogate_key')
