"""Add fan NFT like and favorite reactions."""

import sqlalchemy as sa

from alembic import op

revision = "20260722_0024"
down_revision = "20260722_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nft_creation_reactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("application_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("favorited", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["nft_applications.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "user_id", name="uq_nft_creation_reaction_user"),
    )
    for column in ("application_id", "user_id", "liked", "favorited"):
        op.create_index(f"ix_nft_creation_reactions_{column}", "nft_creation_reactions", [column])


def downgrade() -> None:
    op.drop_table("nft_creation_reactions")
