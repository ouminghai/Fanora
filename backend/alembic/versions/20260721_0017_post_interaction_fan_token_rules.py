"""Add one-token rules for replying to and liking community posts."""

from alembic import op

revision = "20260721_0017"
down_revision = "20260721_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO fan_token_rules
            (code, name, description, category, token_delta, verification_method, repeat_policy,
             daily_limit, monthly_limit, requires_review, is_active, sort_order, created_at, updated_at)
        VALUES
            ('post-reply', '回复帖子', '发布一条符合长度要求的帖子评论或回复', 'content', 1,
             'system', 'once-per-reply', NULL, NULL, FALSE, TRUE, 61, NOW(), NOW()),
            ('post-like', '点赞帖子', '首次点赞一篇社区帖子', 'content', 1,
             'system', 'once-per-user-post', NULL, NULL, FALSE, TRUE, 62, NOW(), NOW())
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            token_delta = EXCLUDED.token_delta,
            verification_method = EXCLUDED.verification_method,
            repeat_policy = EXCLUDED.repeat_policy,
            daily_limit = EXCLUDED.daily_limit,
            monthly_limit = EXCLUDED.monthly_limit,
            requires_review = EXCLUDED.requires_review,
            is_active = EXCLUDED.is_active,
            updated_at = NOW();
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM fan_token_rules WHERE code IN ('post-reply', 'post-like')")
