"""Add story images to fan NFT applications."""

import sqlalchemy as sa

from alembic import op

revision = "20260722_0025"
down_revision = "20260722_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nft_applications",
        sa.Column("story_image_urls", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.alter_column("nft_applications", "story_image_urls", server_default=None)


def downgrade() -> None:
    op.drop_column("nft_applications", "story_image_urls")
