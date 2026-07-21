"""Add bookmark-received and membership NFT mint Fan Token rules."""

from alembic import op

revision = "20260721_0019"
down_revision = "20260721_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO fan_token_rules
            (code, name, description, category, token_delta, verification_method, repeat_policy,
             daily_limit, monthly_limit, requires_review, is_active, sort_order, created_at, updated_at)
        VALUES
            ('post-bookmark-received', '帖子被收藏', '帖子被不同用户首次收藏时奖励作者，每篇最多奖励 10 次',
             'content', 1, 'system', 'up-to-10-per-post', NULL, NULL, FALSE, TRUE, 64, NOW(), NOW()),
            ('membership-nft-mint', '首次铸造会员 NFT', '用户的 ERC-721 会员身份 NFT 首次链上铸造成功',
             'onchain', 50, 'onchain-receipt', 'once-per-user', NULL, NULL, FALSE, TRUE, 121, NOW(), NOW())
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
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
    op.execute(
        "DELETE FROM fan_token_rules "
        "WHERE code IN ('post-bookmark-received', 'membership-nft-mint')"
    )
