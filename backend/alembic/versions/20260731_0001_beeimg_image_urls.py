"""Store persisted images as hosted URLs.

Revision ID: 20260731_0001
Revises: 20260723_v1
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0001"
down_revision = "20260723_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name, column_name in (
        ("community_posts", "cover_url"),
        ("nft_applications", "image_data"),
        ("user_profiles", "avatar_url"),
    ):
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.Text(),
            type_=sa.String(length=2048),
            existing_nullable=True,
            postgresql_using=f"{column_name}::varchar(2048)",
        )


def downgrade() -> None:
    for table_name, column_name in (
        ("community_posts", "cover_url"),
        ("nft_applications", "image_data"),
        ("user_profiles", "avatar_url"),
    ):
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.String(length=2048),
            type_=sa.Text(),
            existing_nullable=True,
        )
