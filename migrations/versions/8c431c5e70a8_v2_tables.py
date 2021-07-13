"""v2 tables

Revision ID: 8c431c5e70a8
Revises: 4ace74bc8168
Create Date: 2021-07-05 21:59:13.575188

"""

# revision identifiers, used by Alembic.
revision = "8c431c5e70a8"
down_revision = "4ace74bc8168"

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "default_dashboard_template_id", sa.Integer(), nullable=True
        ),
        sa.Column("slug", sa.Unicode(length=255), nullable=False),
        sa.Column("title", sa.Unicode(length=255), nullable=False),
        sa.Column("layout", sa.Integer(), nullable=False),
        sa.Column("fastly_support", sa.Boolean(), nullable=False),
        sa.Column("root_domain", sa.Unicode(length=255), nullable=False),
        sa.Column("root_path_prefix", sa.Unicode(length=255), nullable=False),
        sa.Column("fastly_domain", sa.Unicode(length=255), nullable=True),
        sa.Column(
            "fastly_encrypted_api_key", sa.String(length=255), nullable=True
        ),
        sa.Column("fastly_service_id", sa.Unicode(length=255), nullable=True),
        sa.Column("bucket_name", sa.Unicode(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    # Create a default organization to associate with any existing
    # products
    op.execute(
        ""
        "INSERT INTO organizations (\n"
        "    slug,\n"
        "    title,\n"
        "    layout,\n"
        "    fastly_support,\n"
        "    root_domain,\n"
        "    root_path_prefix\n"
        ")\n"
        "VALUES\n"
        "    (\n"
        "        'default',\n"
        "        'Default',\n"
        "        1,\n"
        "        false,\n"
        "        'example.com',\n"
        "        '/'\n"
        ");\n"
    )
    op.create_table(
        "dashboardtemplates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.UnicodeText(), nullable=True),
        sa.Column("bucket_prefix", sa.Unicode(length=255), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("date_created", sa.DateTime(), nullable=False),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.Column("date_deleted", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket_prefix"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("slug", sa.Unicode(length=255), nullable=False),
        sa.Column("title", sa.Unicode(length=255), nullable=False),
        sa.Column("comment", sa.UnicodeText(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "organization_id"),
        sa.UniqueConstraint("title", "organization_id"),
    )
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_tags_organization_id"),
            ["organization_id"],
            unique=False,
        )

    op.create_table(
        "producttags",
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("tag_id", "product_id"),
    )
    with op.batch_alter_table("builds", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("git_ref", sa.Unicode(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("uploaded_by_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(None, "users", ["uploaded_by_id"], ["id"])

    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.Integer(), nullable=True))
    # Insert defaults (main for main edition; draft for all others)
    op.execute("UPDATE editions SET kind = 3 WHERE editions.slug != 'main'")
    op.execute("UPDATE editions SET kind = 1 WHERE editions.slug = 'main'")
    # Make editions.kind non-nullable
    op.alter_column("editions", "kind", nullable=False)

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            None, "organizations", ["organization_id"], ["id"]
        )
    # Insert default organization in any existing products
    op.execute("UPDATE products SET organization_id = 1")
    # Make products.organization_id non-nullable
    op.alter_column("products", "organization_id", nullable=False)


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("editions", schema=None) as batch_op:
        batch_op.drop_column("kind")

    with op.batch_alter_table("builds", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("uploaded_by_id")
        batch_op.drop_column("git_ref")

    op.drop_table("producttags")
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tags_organization_id"))

    op.drop_table("tags")
    op.drop_table("dashboardtemplates")
    op.drop_table("organizations")
