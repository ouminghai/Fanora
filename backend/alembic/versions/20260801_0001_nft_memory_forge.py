"""Add the auditable NFT Memory Forge game state.

Revision ID: 20260801_0001
Revises: 20260731_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260801_0001"
down_revision = "20260731_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nft_forge_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(length=80), nullable=True),
        sa.Column("template_id", sa.String(length=64), nullable=True),
        sa.Column("visual_style", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("story_summary", sa.String(length=1500), nullable=False),
        sa.Column("image_prompt", sa.String(length=2500), nullable=False),
        sa.Column("reference_image_urls", sa.JSON(), nullable=False),
        sa.Column("suggested_attributes", sa.JSON(), nullable=False),
        sa.Column("supply", sa.BigInteger(), nullable=False),
        sa.Column("price_fan_tokens", sa.BigInteger(), nullable=False),
        sa.Column("forge_mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rules_version", sa.String(length=30), nullable=False),
        sa.Column("generated_versions", sa.JSON(), nullable=False),
        sa.Column("selected_version_id", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "conversation_id", "forge_mode", "status", "created_at"):
        op.create_index(f"ix_nft_forge_sessions_{column}", "nft_forge_sessions", [column])

    op.create_table(
        "nft_ai_analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("forge_session_id", sa.String(), nullable=False),
        sa.Column("rare_score", sa.Integer(), nullable=False),
        sa.Column("rarity_level", sa.String(length=20), nullable=False),
        sa.Column("originality", sa.Integer(), nullable=False),
        sa.Column("visual_quality", sa.Integer(), nullable=False),
        sa.Column("fan_emotion", sa.Integer(), nullable=False),
        sa.Column("scarcity", sa.Integer(), nullable=False),
        sa.Column("community_potential", sa.Integer(), nullable=False),
        sa.Column("recommend_supply_min", sa.Integer(), nullable=False),
        sa.Column("recommend_supply_max", sa.Integer(), nullable=False),
        sa.Column("recommend_supply_default", sa.Integer(), nullable=False),
        sa.Column("recommend_price_min", sa.Integer(), nullable=False),
        sa.Column("recommend_price_max", sa.Integer(), nullable=False),
        sa.Column("recommend_price_default", sa.Integer(), nullable=False),
        sa.Column("suggestions", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["forge_session_id"], ["nft_forge_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("forge_session_id", name="uq_nft_ai_analysis_session"),
    )
    op.create_index("ix_nft_ai_analyses_forge_session_id", "nft_ai_analyses", ["forge_session_id"])

    op.create_table(
        "nft_forge_attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("forge_session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("forge_mode", sa.String(length=20), nullable=False),
        sa.Column("payment_source", sa.String(length=20), nullable=False),
        sa.Column("fan_cost", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("perfect_rate", sa.Float(), nullable=False),
        sa.Column("random_roll", sa.Float(), nullable=False),
        sa.Column("perfect_roll", sa.Float(), nullable=True),
        sa.Column("server_seed_hash", sa.String(length=64), nullable=False),
        sa.Column("server_seed_reveal", sa.String(length=128), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("refund_status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("rules_version", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["forge_session_id"], ["nft_forge_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_nft_forge_attempt_idempotency"),
    )
    for column in ("forge_session_id", "user_id", "idempotency_key", "forge_mode", "result", "created_at"):
        op.create_index(f"ix_nft_forge_attempts_{column}", "nft_forge_attempts", [column])

    op.create_table(
        "user_fragment_balances",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("stable_credits", sa.Integer(), nullable=False),
        sa.Column("focused_credits", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_fragment_balance_user"),
    )
    op.create_index("ix_user_fragment_balances_user_id", "user_fragment_balances", ["user_id"])

    op.create_table(
        "fragment_ledgers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("forge_attempt_id", sa.String(), nullable=True),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["forge_attempt_id"], ["nft_forge_attempts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_fragment_ledger_idempotency"),
    )
    for column in ("user_id", "forge_attempt_id", "source_type", "idempotency_key", "created_at"):
        op.create_index(f"ix_fragment_ledgers_{column}", "fragment_ledgers", [column])

    op.create_table(
        "nft_generation_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("forge_attempt_id", sa.String(), nullable=False),
        sa.Column("forge_session_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("image_prompt", sa.String(length=2500), nullable=False),
        sa.Column("output_versions", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["forge_attempt_id"], ["nft_forge_attempts.id"]),
        sa.ForeignKeyConstraint(["forge_session_id"], ["nft_forge_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("forge_attempt_id", "forge_session_id", "status"):
        op.create_index(f"ix_nft_generation_jobs_{column}", "nft_generation_jobs", [column])

    op.add_column("nft_applications", sa.Column("forge_session_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_nft_applications_forge_session_id",
        "nft_applications",
        "nft_forge_sessions",
        ["forge_session_id"],
        ["id"],
    )
    op.create_index("ix_nft_applications_forge_session_id", "nft_applications", ["forge_session_id"])
    op.create_unique_constraint("uq_nft_application_forge_session", "nft_applications", ["forge_session_id"])


def downgrade() -> None:
    op.drop_constraint("uq_nft_application_forge_session", "nft_applications", type_="unique")
    op.drop_index("ix_nft_applications_forge_session_id", table_name="nft_applications")
    op.drop_constraint("fk_nft_applications_forge_session_id", "nft_applications", type_="foreignkey")
    op.drop_column("nft_applications", "forge_session_id")
    op.drop_table("nft_generation_jobs")
    op.drop_table("fragment_ledgers")
    op.drop_table("user_fragment_balances")
    op.drop_table("nft_forge_attempts")
    op.drop_table("nft_ai_analyses")
    op.drop_table("nft_forge_sessions")
