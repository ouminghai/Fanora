"""Add paid official membership status and payment receipts."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0007"
down_revision = "20260720_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("is_official_member", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "user_profiles",
        sa.Column("official_member_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_user_profiles_is_official_member",
        "user_profiles",
        ["is_official_member"],
    )

    op.create_table(
        "official_membership_payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("treasury_address", sa.String(length=42), nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("amount_wei", sa.BigInteger(), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_wei > 0", name="ck_official_membership_payment_amount_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_hash", name="uq_official_membership_payment_transaction"),
        sa.UniqueConstraint("user_id", name="uq_official_membership_payment_user"),
    )
    op.create_index(
        "ix_official_membership_payments_chain_id",
        "official_membership_payments",
        ["chain_id"],
    )
    op.create_index(
        "ix_official_membership_payments_status",
        "official_membership_payments",
        ["status"],
    )
    op.create_index(
        "ix_official_membership_payments_transaction_hash",
        "official_membership_payments",
        ["transaction_hash"],
    )
    op.create_index(
        "ix_official_membership_payments_user_id",
        "official_membership_payments",
        ["user_id"],
    )
    op.create_index(
        "ix_official_membership_payments_wallet_address",
        "official_membership_payments",
        ["wallet_address"],
    )


def downgrade() -> None:
    op.drop_index("ix_official_membership_payments_wallet_address", table_name="official_membership_payments")
    op.drop_index("ix_official_membership_payments_user_id", table_name="official_membership_payments")
    op.drop_index("ix_official_membership_payments_transaction_hash", table_name="official_membership_payments")
    op.drop_index("ix_official_membership_payments_status", table_name="official_membership_payments")
    op.drop_index("ix_official_membership_payments_chain_id", table_name="official_membership_payments")
    op.drop_table("official_membership_payments")
    op.drop_index("ix_user_profiles_is_official_member", table_name="user_profiles")
    op.drop_column("user_profiles", "official_member_since")
    op.drop_column("user_profiles", "is_official_member")
