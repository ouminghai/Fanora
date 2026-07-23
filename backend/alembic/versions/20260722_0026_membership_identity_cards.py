"""Track downloadable membership identity cards."""

import sqlalchemy as sa

from alembic import op

revision = "20260722_0026"
down_revision = "20260722_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "membership_identity_nfts",
        sa.Column("is_member_card", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("membership_identity_nfts", sa.Column("card_level_code", sa.String(length=50), nullable=True))
    op.add_column("membership_identity_nfts", sa.Column("card_content_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "membership_identity_nfts",
        sa.Column("card_fee_fan_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("membership_identity_nfts", sa.Column("card_created_at", sa.DateTime(), nullable=True))
    op.add_column("membership_identity_nfts", sa.Column("card_updated_at", sa.DateTime(), nullable=True))
    op.create_index("ix_membership_identity_nfts_is_member_card", "membership_identity_nfts", ["is_member_card"])
    op.create_check_constraint(
        "ck_membership_identity_card_fee_nonnegative",
        "membership_identity_nfts",
        "card_fee_fan_tokens >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_membership_identity_card_fee_nonnegative",
        "membership_identity_nfts",
        type_="check",
    )
    op.drop_index("ix_membership_identity_nfts_is_member_card", table_name="membership_identity_nfts")
    op.drop_column("membership_identity_nfts", "card_updated_at")
    op.drop_column("membership_identity_nfts", "card_created_at")
    op.drop_column("membership_identity_nfts", "card_fee_fan_tokens")
    op.drop_column("membership_identity_nfts", "card_content_hash")
    op.drop_column("membership_identity_nfts", "card_level_code")
    op.drop_column("membership_identity_nfts", "is_member_card")
