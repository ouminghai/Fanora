"""Add post reactions, reply likes, image creations, and two-level comments."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0009"
down_revision = "20260720_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "community_posts",
        "cover_url",
        existing_type=sa.String(length=2048),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.add_column("community_replies", sa.Column("parent_reply_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_community_replies_parent_reply_id",
        "community_replies",
        "community_replies",
        ["parent_reply_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_community_replies_parent_reply_id", "community_replies", ["parent_reply_id"])

    op.create_table(
        "community_post_reactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("bookmarked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_post_reaction_user"),
    )
    for column in ("bookmarked", "liked", "post_id", "user_id"):
        op.create_index(f"ix_community_post_reactions_{column}", "community_post_reactions", [column])

    op.create_table(
        "community_reply_likes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("reply_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reply_id"], ["community_replies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reply_id", "user_id", name="uq_community_reply_like_user"),
    )
    op.create_index("ix_community_reply_likes_reply_id", "community_reply_likes", ["reply_id"])
    op.create_index("ix_community_reply_likes_user_id", "community_reply_likes", ["user_id"])


def downgrade() -> None:
    op.drop_table("community_reply_likes")
    op.drop_table("community_post_reactions")
    op.drop_index("ix_community_replies_parent_reply_id", table_name="community_replies")
    op.drop_constraint("fk_community_replies_parent_reply_id", "community_replies", type_="foreignkey")
    op.drop_column("community_replies", "parent_reply_id")
    op.alter_column(
        "community_posts",
        "cover_url",
        existing_type=sa.Text(),
        type_=sa.String(length=2048),
        existing_nullable=True,
    )
