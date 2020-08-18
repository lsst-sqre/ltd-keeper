"""length 255 unicode columns

Revision ID: 0c0c70d73d4b
Revises: 1ba709663f26
Create Date: 2016-08-02 09:35:32.422391

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0c0c70d73d4b"
down_revision = "1ba709663f26"


def upgrade():
    with op.batch_alter_table("builds", schema=None) as batch_op:
        batch_op.alter_column(
            "github_requester",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "slug",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )

    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "bucket_name",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "doc_repo",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "root_domain",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "root_fastly_domain",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "slug",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "title",
            existing_type=sa.VARCHAR(length=256),
            type_=sa.Unicode(length=255),
            existing_nullable=False,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.VARCHAR(length=64),
            type_=sa.Unicode(length=255),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=64),
            existing_nullable=True,
        )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "title",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "slug",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "root_fastly_domain",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "root_domain",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "doc_repo",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "bucket_name",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=True,
        )

    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )

    with op.batch_alter_table("builds", schema=None) as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "github_requester",
            existing_type=sa.Unicode(length=255),
            type_=sa.VARCHAR(length=256),
            existing_nullable=True,
        )
