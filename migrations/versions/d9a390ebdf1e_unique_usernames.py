"""unique usernames

Revision ID: d9a390ebdf1e
Revises: aa9e2d2736c8
Create Date: 2016-04-29 13:35:12.711786

"""

# revision identifiers, used by Alembic.
revision = 'd9a390ebdf1e'
down_revision = 'aa9e2d2736c8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_index('ix_users_username', table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
