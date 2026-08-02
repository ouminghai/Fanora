"""Persist reusable NFT visual templates.

Revision ID: 20260731_0002
Revises: 20260731_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0002"
down_revision = "20260731_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nft_visual_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=True),
        sa.Column("source_post_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("prompt", sa.String(length=2000), nullable=False),
        sa.Column("preview_image_url", sa.String(length=2048), nullable=False),
        sa.Column("reference_image_urls", sa.JSON(), nullable=False),
        sa.Column("palette", sa.JSON(), nullable=False),
        sa.Column("elements", sa.JSON(), nullable=False),
        sa.Column("forbidden", sa.JSON(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_post_id"], ["community_posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nft_visual_templates_owner_user_id", "nft_visual_templates", ["owner_user_id"])
    op.create_index("ix_nft_visual_templates_source_post_id", "nft_visual_templates", ["source_post_id"])
    op.create_index("ix_nft_visual_templates_name", "nft_visual_templates", ["name"])
    op.create_index("ix_nft_visual_templates_category", "nft_visual_templates", ["category"])
    op.create_index("ix_nft_visual_templates_is_system", "nft_visual_templates", ["is_system"])
    op.create_index("ix_nft_visual_templates_created_at", "nft_visual_templates", ["created_at"])


def downgrade() -> None:
    op.drop_table("nft_visual_templates")
