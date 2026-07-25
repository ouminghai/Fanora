"""Allow community posts to link published fan NFT creations."""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0029"
down_revision = "20260723_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("community_posts", sa.Column("linked_nft_creation_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_community_posts_linked_nft_creation_id",
        "community_posts",
        "nft_applications",
        ["linked_nft_creation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_community_posts_linked_nft_creation_id",
        "community_posts",
        ["linked_nft_creation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_community_posts_linked_nft_creation_id", table_name="community_posts")
    op.drop_constraint("fk_community_posts_linked_nft_creation_id", "community_posts", type_="foreignkey")
    op.drop_column("community_posts", "linked_nft_creation_id")
