"""Add Web3Auth sessions, user profiles, roles, and communities."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0002"
down_revision = "20260717_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("bio", sa.String(length=280), nullable=True),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("fan_type", sa.String(length=50), nullable=False),
        sa.Column("profile_visibility", sa.String(length=20), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_user_profiles_username", "user_profiles", ["username"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_role", "user_roles", ["role"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    op.create_table(
        "login_challenges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_challenges_expires_at", "login_challenges", ["expires_at"])
    op.create_index("ix_login_challenges_wallet_address", "login_challenges", ["wallet_address"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "communities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("logo_url", sa.String(length=2048), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_communities_is_public", "communities", ["is_public"])
    op.create_index("ix_communities_name", "communities", ["name"])
    op.create_index("ix_communities_owner_user_id", "communities", ["owner_user_id"])
    op.create_index("ix_communities_slug", "communities", ["slug"], unique=True)

    op.create_table(
        "community_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("community_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_member"),
    )
    op.create_index("ix_community_members_community_id", "community_members", ["community_id"])
    op.create_index("ix_community_members_user_id", "community_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("community_members")
    op.drop_table("communities")
    op.drop_table("user_sessions")
    op.drop_table("login_challenges")
    op.drop_table("user_roles")
    op.drop_table("user_profiles")
