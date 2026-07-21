"""Add a five-token rule for publishing community posts."""

from alembic import op

revision = "20260721_0018"
down_revision = "20260721_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO fan_token_rules
            (code, name, description, category, token_delta, verification_method, repeat_policy,
             daily_limit, monthly_limit, requires_review, is_active, sort_order, created_at, updated_at)
        VALUES
            ('post-publish', '发布帖子', '成功发布一篇社区帖子', 'content', 5,
             'system', 'once-per-post', NULL, NULL, FALSE, TRUE, 63, NOW(), NOW())
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
    op.execute("DELETE FROM fan_token_rules WHERE code = 'post-publish'")
