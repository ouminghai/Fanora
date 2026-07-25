"""Seed enough official creations to demonstrate the masonry community wall."""

from alembic import op


revision = "20260720_0010"
down_revision = "20260720_0009"
branch_labels = None
depends_on = None


POST_IDS = [
    "00000000-0000-0000-0000-000000000010",
    "00000000-0000-0000-0000-000000000011",
    "00000000-0000-0000-0000-000000000012",
    "00000000-0000-0000-0000-000000000013",
]


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO community_posts
            (id, community_id, author_user_id, title, body, cover_url, category, status, reply_count, created_at, updated_at)
        VALUES
            ('00000000-0000-0000-0000-000000000010',
             (SELECT id FROM communities WHERE slug = 'fanora-official'),
             '00000000-0000-0000-0000-000000000001',
             '演唱会散场以后，你最舍不得的是哪一刻？',
             '灯光熄灭、人群慢慢离场，但耳边的合唱好像还没有结束。分享一段你最想留住的现场记忆。',
             '/img/fanora/activity-concert.jpg', 'story', 'published', 0, NOW(), NOW()),
            ('00000000-0000-0000-0000-000000000011',
             (SELECT id FROM communities WHERE slug = 'fanora-official'),
             '00000000-0000-0000-0000-000000000001',
             '把长期喜欢做成一张纪念卡',
             '如果能为自己的粉丝旅程设计一张纪念卡，你会放入哪一句歌词、哪一种颜色和哪段日期？',
             '/img/fanora/activity-badge.jpg', 'creation', 'published', 0, NOW(), NOW()),
            ('00000000-0000-0000-0000-000000000012',
             (SELECT id FROM communities WHERE slug = 'fanora-official'),
             '00000000-0000-0000-0000-000000000001',
             '今晚耳机里的现场感',
             '有些现场版本会让熟悉的歌突然拥有新的呼吸。留下你最近反复播放的一段 Live。',
             '/img/fanora/eason-concert.webp', 'music', 'published', 0, NOW(), NOW()),
            ('00000000-0000-0000-0000-000000000013',
             (SELECT id FROM communities WHERE slug = 'fanora-official'),
             '00000000-0000-0000-0000-000000000001',
             'Fanora 共创海报：让每一份支持被看见',
             '用图片、文字或配色表达你理解的 Proof of Fandom。优秀灵感会进入后续社区共创提案。',
             '/img/fanora/activity-community.jpg', 'creation', 'published', 0, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    ids = ", ".join(f"'{post_id}'" for post_id in POST_IDS)
    op.execute(f"DELETE FROM community_posts WHERE id IN ({ids})")
