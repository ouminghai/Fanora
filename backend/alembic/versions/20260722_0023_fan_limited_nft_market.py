"""Add fan-published limited NFT market fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260722_0023"
down_revision = "20260722_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nft_applications", sa.Column("price_fan_tokens", sa.BigInteger(), server_default="1", nullable=False))
    op.add_column("nft_applications", sa.Column("max_supply", sa.BigInteger(), server_default="1", nullable=False))
    op.add_column("nft_applications", sa.Column("publish_fee_fan_tokens", sa.BigInteger(), server_default="100", nullable=False))
    op.create_check_constraint("ck_nft_applications_price_positive", "nft_applications", "price_fan_tokens > 0")
    op.create_check_constraint("ck_nft_applications_max_supply_positive", "nft_applications", "max_supply > 0")
    op.create_check_constraint("ck_nft_applications_publish_fee_nonnegative", "nft_applications", "publish_fee_fan_tokens >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_nft_applications_publish_fee_nonnegative", "nft_applications", type_="check")
    op.drop_constraint("ck_nft_applications_max_supply_positive", "nft_applications", type_="check")
    op.drop_constraint("ck_nft_applications_price_positive", "nft_applications", type_="check")
    op.drop_column("nft_applications", "publish_fee_fan_tokens")
    op.drop_column("nft_applications", "max_supply")
    op.drop_column("nft_applications", "price_fan_tokens")
