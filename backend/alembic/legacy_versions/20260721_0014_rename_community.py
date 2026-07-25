"""Rename the public community for the on-chain product experience."""

from alembic import op

revision = "20260721_0014"
down_revision = "20260720_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        UPDATE users
        SET display_name = 'Fanora Protocol', updated_at = NOW()
        WHERE id = '00000000-0000-0000-0000-000000000001';

        UPDATE communities
        SET name = 'Fanora 链上社区',
            description = '围绕音乐、现场与长期支持展开的链上共创空间。',
            updated_at = NOW()
        WHERE slug = 'fanora-official';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        UPDATE users
        SET display_name = 'Fanora 官方', updated_at = NOW()
        WHERE id = '00000000-0000-0000-0000-000000000001';

        UPDATE communities
        SET name = 'Fanora 官方社区',
            description = '围绕音乐、现场与长期支持展开的唯一官方粉丝社区。',
            updated_at = NOW()
        WHERE slug = 'fanora-official';
        """
    )
