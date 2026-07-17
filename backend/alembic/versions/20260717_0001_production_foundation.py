"""Create Fanora identity and profile-run tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject", name="uq_auth_identity_provider_subject"),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("address", sa.String(length=42), nullable=False),
        sa.Column("wallet_type", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("chain_family", sa.String(length=20), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("address"),
    )
    op.create_index("ix_wallets_address", "wallets", ["address"], unique=True)
    op.create_index("ix_wallets_is_primary", "wallets", ["is_primary"])
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    op.create_table(
        "fan_profile_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("community_id", sa.String(length=100), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("analysis_source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fan_profile_runs_analysis_source", "fan_profile_runs", ["analysis_source"])
    op.create_index("ix_fan_profile_runs_community_id", "fan_profile_runs", ["community_id"])
    op.create_index("ix_fan_profile_runs_user_id", "fan_profile_runs", ["user_id"])
    op.create_index("ix_fan_profile_runs_wallet_address", "fan_profile_runs", ["wallet_address"])


def downgrade() -> None:
    op.drop_table("fan_profile_runs")
    op.drop_table("wallets")
    op.drop_table("auth_identities")
    op.drop_table("users")

