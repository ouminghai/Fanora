"""Add NFT metadata, chain operations, identities, collectibles, and applications."""

from alembic import op
import sqlalchemy as sa

revision = "20260721_0020"
down_revision = "20260721_0019"
branch_labels = None
depends_on = None


def _indexes(table: str, columns: list[str], unique: set[str] | None = None) -> None:
    unique = unique or set()
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column], unique=column in unique)


def upgrade() -> None:
    op.add_column("membership_levels", sa.Column("badge_image_cid", sa.String(255), nullable=True))
    op.add_column("membership_levels", sa.Column("badge_image_pin_id", sa.String(255), nullable=True))
    op.add_column("membership_levels", sa.Column("badge_image_content_hash", sa.String(64), nullable=True))
    op.add_column("fan_profile_runs", sa.Column("rule_version", sa.String(50), server_default="fan-profile-v2", nullable=False))
    op.add_column("fan_profile_runs", sa.Column("prompt_version", sa.String(50), server_default="fan-profile-prompt-v2", nullable=False))
    op.add_column("fan_profile_runs", sa.Column("model_id", sa.String(100), server_default="rules", nullable=False))
    op.add_column("fan_profile_runs", sa.Column("degraded", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_fan_profile_runs_degraded", "fan_profile_runs", ["degraded"])
    op.create_table(
        "collectible_token_types",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("token_id", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("metadata_cid", sa.String(255), nullable=False),
        sa.Column("max_supply", sa.BigInteger(), nullable=False),
        sa.Column("minted_supply", sa.BigInteger(), nullable=False),
        sa.Column("per_wallet_limit", sa.BigInteger(), nullable=False),
        sa.Column("mint_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mint_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transferable", sa.Boolean(), nullable=False),
        sa.Column("metadata_frozen", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("max_supply > 0", name="ck_collectible_max_supply_positive"),
        sa.CheckConstraint("per_wallet_limit > 0", name="ck_collectible_wallet_limit_positive"),
        sa.UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_collectible_token_type"),
    )
    _indexes("collectible_token_types", ["token_id", "category", "chain_id", "contract_address", "source_id", "status", "active"])

    op.create_table(
        "chain_operations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("operation_type", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("operation_hash", sa.String(66), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("token_id", sa.BigInteger(), nullable=True),
        sa.Column("metadata_cid", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("transaction_hash", sa.String(66), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("confirmations", sa.Integer(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_chain_operation_idempotency_key"),
    )
    _indexes("chain_operations", ["user_id", "operation_type", "idempotency_key", "operation_hash", "chain_id", "contract_address", "status", "transaction_hash"], {"operation_hash"})

    op.create_table(
        "nft_metadata_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("subject_type", sa.String(30), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("image_cid", sa.String(255), nullable=False),
        sa.Column("image_pin_id", sa.String(255), nullable=True),
        sa.Column("metadata_cid", sa.String(255), nullable=False),
        sa.Column("metadata_pin_id", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("pin_status", sa.String(20), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subject_type", "subject_id", "version", name="uq_nft_metadata_version"),
    )
    _indexes("nft_metadata_versions", ["subject_type", "subject_id", "metadata_cid", "pin_status", "created_by_user_id"])

    op.create_table(
        "collectible_ownerships",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("token_type_id", sa.String(), sa.ForeignKey("collectible_token_types.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("claim_key", sa.String(66), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("chain_operation_id", sa.String(), sa.ForeignKey("chain_operations.id"), nullable=True),
        sa.Column("minted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_type_id", "user_id", name="uq_collectible_ownership"),
    )
    _indexes("collectible_ownerships", ["token_type_id", "user_id", "wallet_address", "claim_key", "status"], {"claim_key"})

    op.create_table(
        "membership_identity_nfts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("token_id", sa.BigInteger(), nullable=True),
        sa.Column("level_id", sa.BigInteger(), nullable=False),
        sa.Column("level_code", sa.String(50), nullable=False),
        sa.Column("metadata_version", sa.Integer(), nullable=False),
        sa.Column("metadata_cid", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("chain_operation_id", sa.String(), sa.ForeignKey("chain_operations.id"), nullable=True),
        sa.Column("minted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_membership_identity_user"),
        sa.UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_membership_identity_token"),
    )
    _indexes("membership_identity_nfts", ["user_id", "wallet_address", "chain_id", "contract_address", "status"])

    op.create_table(
        "nft_applications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("theme", sa.String(120), nullable=False),
        sa.Column("public_attributes", sa.JSON(), nullable=False),
        sa.Column("copyright_declaration", sa.String(500), nullable=False),
        sa.Column("image_data", sa.Text(), nullable=True),
        sa.Column("image_mime_type", sa.String(100), nullable=False),
        sa.Column("image_size_bytes", sa.Integer(), nullable=False),
        sa.Column("image_width", sa.Integer(), nullable=False),
        sa.Column("image_height", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("internal_review_note", sa.String(1000), nullable=True),
        sa.Column("metadata_version_id", sa.String(), sa.ForeignKey("nft_metadata_versions.id"), nullable=True),
        sa.Column("collectible_token_type_id", sa.String(), sa.ForeignKey("collectible_token_types.id"), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    _indexes("nft_applications", ["user_id", "status"])


def downgrade() -> None:
    for table in ["nft_applications", "membership_identity_nfts", "collectible_ownerships", "nft_metadata_versions", "chain_operations", "collectible_token_types"]:
        op.drop_table(table)
    op.drop_index("ix_fan_profile_runs_degraded", table_name="fan_profile_runs")
    op.drop_column("fan_profile_runs", "degraded")
    op.drop_column("fan_profile_runs", "model_id")
    op.drop_column("fan_profile_runs", "prompt_version")
    op.drop_column("fan_profile_runs", "rule_version")
    op.drop_column("membership_levels", "badge_image_content_hash")
    op.drop_column("membership_levels", "badge_image_pin_id")
    op.drop_column("membership_levels", "badge_image_cid")
