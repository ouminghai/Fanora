"""Add the official community's off-chain posts, tasks, check-ins, and Fan Token ledger."""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0008"
down_revision = "20260720_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_security_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("wallet_address", sa.String(length=42), nullable=True),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("created_at", "event", "outcome", "user_id", "wallet_address"):
        op.create_index(f"ix_auth_security_events_{column}", "auth_security_events", [column])

    op.create_table(
        "community_posts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("community_id", sa.String(), nullable=False),
        sa.Column("author_user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cover_url", sa.String(length=2048), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("author_user_id", "category", "community_id", "created_at", "status", "title"):
        op.create_index(f"ix_community_posts_{column}", "community_posts", [column])

    op.create_table(
        "community_replies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("author_user_id", sa.String(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("author_user_id", "created_at", "post_id", "status"):
        op.create_index(f"ix_community_replies_{column}", "community_replies", [column])

    op.create_table(
        "fan_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("community_id", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_fan_tokens", sa.Integer(), nullable=False),
        sa.Column("target_post_id", sa.String(), nullable=True),
        sa.Column("validation_rule", sa.JSON(), nullable=False),
        sa.Column("participation_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reward_fan_tokens > 0", name="ck_fan_tasks_positive_reward"),
        sa.CheckConstraint(
            "participation_limit IS NULL OR participation_limit > 0",
            name="ck_fan_tasks_participation_limit",
        ),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_post_id"], ["community_posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "community_id",
        "created_at",
        "created_by_user_id",
        "end_at",
        "start_at",
        "status",
        "target_post_id",
        "task_type",
        "title",
    ):
        op.create_index(f"ix_fan_tasks_{column}", "fan_tasks", [column])

    op.create_table(
        "task_participations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reward_snapshot", sa.Integer(), nullable=False),
        sa.Column("reply_id", sa.String(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reply_id"], ["community_replies.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fan_tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_participation_user"),
    )
    for column in ("reply_id", "status", "task_id", "user_id"):
        op.create_index(f"ix_task_participations_{column}", "task_participations", [column])

    op.create_table(
        "task_audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("participation_id", sa.String(), nullable=True),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["participation_id"], ["task_participations.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fan_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("actor_user_id", "created_at", "event", "participation_id", "task_id"):
        op.create_index(f"ix_task_audit_logs_{column}", "task_audit_logs", [column])

    op.create_table(
        "daily_check_ins",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("reward_fan_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "check_in_date", name="uq_daily_check_in_user_date"),
    )
    for column in ("check_in_date", "created_at", "user_id"):
        op.create_index(f"ix_daily_check_ins_{column}", "daily_check_ins", [column])

    op.create_table(
        "fan_token_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("balance_after >= 0", name="ck_fan_token_ledger_nonnegative_balance"),
        sa.CheckConstraint("delta <> 0", name="ck_fan_token_ledger_nonzero_delta"),
        sa.ForeignKeyConstraint(["task_id"], ["fan_tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_fan_token_ledger_idempotency_key"),
    )
    for column in ("created_at", "idempotency_key", "source_id", "source_type", "task_id", "user_id"):
        op.create_index(
            f"ix_fan_token_ledger_{column}",
            "fan_token_ledger",
            [column],
            unique=column == "idempotency_key",
        )

    op.execute(
        """
        INSERT INTO users (id, display_name, status, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Fanora 官方', 'system', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO communities (id, owner_user_id, slug, name, description, logo_url, is_public, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000001',
            'fanora-official',
            'Fanora 官方社区',
            '围绕音乐、现场与长期支持展开的唯一官方粉丝社区。',
            '/img/logo.png',
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (slug) DO NOTHING;

        INSERT INTO community_posts
            (id, community_id, author_user_id, title, body, cover_url, category, status, reply_count, created_at, updated_at)
        VALUES
            (
                '00000000-0000-0000-0000-000000000003',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '你与喜欢的音乐，第一次相遇在什么时候？',
                '欢迎来到 Fanora。分享你第一次被一首歌、一次舞台或一句歌词打动的故事。认真回复即可完成对应粉丝任务，无需等待人工审核。',
                '/img/fanora/activity-community.jpg',
                'story', 'published', 0, NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000004',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '本周循环：安利一首你舍不得切掉的歌',
                '留下歌名和推荐理由，也可以说说它陪你走过了怎样的一段时间。回复发布成功后，已领取任务会由系统直接验证。',
                '/img/fanora/activity-music.jpg',
                'music', 'published', 0, NOW(), NOW()
            )
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO fan_tasks
            (id, community_id, created_by_user_id, title, description, task_type, status, reward_fan_tokens,
             target_post_id, validation_rule, created_at, updated_at)
        VALUES
            (
                '00000000-0000-0000-0000-000000000005',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '写下你的入坑故事',
                '领取任务后，在指定帖子回复不少于 10 个字，系统会立即确认完成。',
                'post_reply', 'published', 60,
                '00000000-0000-0000-0000-000000000003',
                '{"minimum_reply_length": 10}'::json,
                NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000006',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '安利一首循环单曲',
                '领取任务后，在每周歌单帖子回复歌名与推荐理由即可完成。',
                'post_reply', 'published', 40,
                '00000000-0000-0000-0000-000000000004',
                '{"minimum_reply_length": 10}'::json,
                NOW(), NOW()
            )
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("fan_token_ledger")
    op.drop_table("daily_check_ins")
    op.drop_table("task_audit_logs")
    op.drop_table("task_participations")
    op.drop_table("fan_tasks")
    op.drop_table("community_replies")
    op.drop_table("community_posts")
    op.drop_table("auth_security_events")
