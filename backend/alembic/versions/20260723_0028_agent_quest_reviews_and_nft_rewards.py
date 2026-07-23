"""Add Agent Quest reviews and idempotent task NFT reward records."""

import copy

import sqlalchemy as sa
from alembic import op

revision = "20260723_0028"
down_revision = "20260722_0027"
branch_labels = None
depends_on = None

FEAR_TASK_ID = "00000000-0000-0000-0000-000000000020"


def upgrade() -> None:
    op.create_table(
        "task_content_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("participation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("review_source", sa.String(length=20), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("quality_score >= 0", name="ck_task_content_review_score_min"),
        sa.CheckConstraint("quality_score <= 100", name="ck_task_content_review_score_max"),
        sa.ForeignKeyConstraint(["participation_id"], ["task_participations.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fan_tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("task_id", "participation_id", "user_id", "source_type", "source_id", "decision", "review_source", "degraded", "created_at"):
        op.create_index(f"ix_task_content_reviews_{column}", "task_content_reviews", [column], unique=False)

    op.create_table(
        "task_nft_rewards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("participation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("reward_version", sa.Integer(), nullable=False),
        sa.Column("token_type_id", sa.String(), nullable=True),
        sa.Column("ownership_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("reward_version >= 1", name="ck_task_nft_reward_version_positive"),
        sa.ForeignKeyConstraint(["ownership_id"], ["collectible_ownerships.id"]),
        sa.ForeignKeyConstraint(["participation_id"], ["task_participations.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fan_tasks.id"]),
        sa.ForeignKeyConstraint(["token_type_id"], ["collectible_token_types.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participation_id", "reward_version", name="uq_task_nft_reward_participation_version"),
        sa.UniqueConstraint("task_id", "user_id", "reward_version", name="uq_task_nft_reward_user_version"),
    )
    for column in ("task_id", "participation_id", "user_id", "token_type_id", "ownership_id", "status"):
        op.create_index(f"ix_task_nft_rewards_{column}", "task_nft_rewards", [column], unique=False)

    task_table = sa.table(
        "fan_tasks",
        sa.column("id", sa.String()),
        sa.column("description", sa.String()),
        sa.column("validation_rule", sa.JSON()),
    )
    connection = op.get_bind()
    current = connection.execute(
        sa.select(task_table.c.validation_rule).where(task_table.c.id == FEAR_TASK_ID)
    ).scalar_one_or_none()
    if current is not None:
        validation_rule = copy.deepcopy(current)
        validation_rule["minimum_content_length"] = 10
        validation_rule["nft_reward"] = {
            "enabled": True,
            "version": 1,
            "category": "CONCERT_CARD",
            "name": "FEAR and DREAMS 纪念票",
            "description": "由 Fanora 为完成 FEAR and DREAMS 粉丝记忆任务的成员发行的限量 ERC-1155 演唱会纪念票。",
            "image_path": "/img/fanora/eason-concert.webp",
            "max_supply": 10000,
            "per_wallet_limit": 1,
            "mint_window_days": 3650,
            "transferable": False,
        }
        presentation = validation_rule.setdefault("presentation", {})
        presentation["image_url"] = "/img/fanora/eason-concert.webp"
        connection.execute(
            sa.update(task_table)
            .where(task_table.c.id == FEAR_TASK_ID)
            .values(
                description="写下真实现场记忆，通过 AI Agent 内容审核后领取 FAN，并获得一张链上 FEAR and DREAMS 纪念票。",
                validation_rule=validation_rule,
            )
        )


def downgrade() -> None:
    op.drop_table("task_nft_rewards")
    op.drop_table("task_content_reviews")
