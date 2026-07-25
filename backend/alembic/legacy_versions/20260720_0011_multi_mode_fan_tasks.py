"""Expand the official community task catalog with multiple interaction modes."""

from alembic import op


revision = "20260720_0011"
down_revision = "20260720_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        INSERT INTO fan_tasks
            (id, community_id, created_by_user_id, title, description, task_type, status,
             reward_fan_tokens, target_post_id, validation_rule, participation_limit,
             created_at, updated_at, published_at)
        VALUES
            (
                '00000000-0000-0000-0000-000000000021',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '每日 Fans Club 签到',
                '领取后完成今日签到，在保持连续活跃的同时获得任务积分。',
                'daily_check_in', 'published', 20, NULL,
                '{"presentation":{"catalog_key":"daily-check-in","image_url":"/img/fanora/activity-checkin.jpg","category":"daily","interaction_prompt":"每天回来签到，连续 7 天还有额外奖励","action_url":"/community#check-in","action_label":"去签到","badge_label":"每日互动"}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000020',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                'FEAR and DREAMS 纪念票任务',
                '进入演唱会纪念页完成打卡，领取 FAN；页面已为后续 NFT 纪念票铸造预留入口。',
                'page_action', 'published', 500, NULL,
                '{"presentation":{"catalog_key":"fear-and-dreams","image_url":"/img/fanora/activity-concert.jpg","category":"event","interaction_prompt":"留下你的现场记忆，激活纪念票收藏资格","action_url":"/community/tasks/fear-and-dreams","action_label":"进入纪念票页面","badge_label":"特别任务","special":true}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000022',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '新歌连续收听 7 天',
                '连续参与新歌共听与每日感受互动，完成七日陪伴记录。',
                'streak', 'paused', 120, NULL,
                '{"presentation":{"catalog_key":"new-song-listening","image_url":"/img/fanora/activity-music.jpg","category":"music","interaction_prompt":"连续记录收听感受，让歌单讨论持续发生","action_url":"/community/creations?category=music","action_label":"查看共听计划","badge_label":"连续任务"}}'::json,
                NULL, NOW(), NOW(), NULL
            ),
            (
                '00000000-0000-0000-0000-000000000005',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '分享你的入坑歌曲',
                '领取任务后，在指定帖子分享最初打动你的歌曲与故事，系统即时确认完成。',
                'post_reply', 'published', 80, '00000000-0000-0000-0000-000000000003',
                '{"minimum_reply_length":10,"presentation":{"catalog_key":"share-your-song","image_url":"/img/fanora/activity-community.jpg","category":"discussion","interaction_prompt":"用一首歌开启交流，认识拥有相似记忆的粉丝","action_url":"/community/posts/00000000-0000-0000-0000-000000000003","action_label":"去分享歌曲","badge_label":"社区互动"}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000023',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '粉丝故事图文征集',
                '发布一条故事或共创内容，分享长期陪伴中的真实片段。',
                'content_publish', 'published', 180, NULL,
                '{"content_categories":["story","creation"],"presentation":{"catalog_key":"fan-story","image_url":"/img/fanora/activity-community.jpg","category":"creation","interaction_prompt":"用图文沉淀粉丝记忆，也为社区贡献优质内容","action_url":"/community/creations?composer=1","action_label":"发布粉丝故事","badge_label":"内容共创"}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000024',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '周年祝福共创',
                '发布一条周年祝福或视觉灵感，与社区共同完成纪念作品。',
                'content_publish', 'published', 150, NULL,
                '{"content_categories":["creation","discussion"],"presentation":{"catalog_key":"anniversary-wishes","image_url":"/img/fanora/activity-badge.jpg","category":"creation","interaction_prompt":"共同创作周年内容，让每一份祝福被看见","action_url":"/community/creations?composer=1","action_label":"参与周年共创","badge_label":"限时共创"}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000006',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '经典歌词接龙',
                '在指定音乐帖子回复一句歌词或下一句联想，和其他粉丝完成接龙。',
                'post_reply', 'published', 60, '00000000-0000-0000-0000-000000000004',
                '{"minimum_reply_length":10,"presentation":{"catalog_key":"classic-lyrics-chain","image_url":"/img/fanora/activity-music.jpg","category":"music","interaction_prompt":"回复歌词并邀请下一位粉丝接龙","action_url":"/community/posts/00000000-0000-0000-0000-000000000004","action_label":"去歌词接龙","badge_label":"社区挑战"}}'::json,
                NULL, NOW(), NOW(), NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000026',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '核心粉丝身份画像',
                '完善粉丝资料并连接更多互动记录，后续将开放自动身份验证。',
                'future', 'paused', 300, NULL,
                '{"presentation":{"catalog_key":"core-fan-identity","image_url":"/img/fanora/activity-badge.jpg","category":"identity","interaction_prompt":"完善真实粉丝画像，为身份成长积累可验证记录","action_url":"/profile","action_label":"查看身份画像","badge_label":"身份成长"}}'::json,
                NULL, NOW(), NOW(), NULL
            ),
            (
                '00000000-0000-0000-0000-000000000027',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '城市粉丝见面打卡',
                '为线下活动预留定位与现场凭证验证，开放后可领取活动积分。',
                'event_check_in', 'paused', 300, NULL,
                '{"presentation":{"catalog_key":"city-checkin","image_url":"/img/fanora/activity-checkin.jpg","category":"event","interaction_prompt":"在线下相遇并留下城市粉丝活动记录","action_url":"/community/tasks","action_label":"等待活动开放","badge_label":"线下活动"}}'::json,
                NULL, NOW(), NOW(), NULL
            ),
            (
                '00000000-0000-0000-0000-000000000028',
                (SELECT id FROM communities WHERE slug = 'fanora-official'),
                '00000000-0000-0000-0000-000000000001',
                '周年限定 Badge 解锁',
                '为周年链上收藏预留资格任务，当前先展示活动规则与未来领取入口。',
                'future', 'paused', 100, NULL,
                '{"presentation":{"catalog_key":"anniversary-badge","image_url":"/img/fanora/activity-badge.jpg","category":"special","interaction_prompt":"持续参与社区，为未来周年纪念收藏积累资格","action_url":"/community/tasks","action_label":"查看开放进度","badge_label":"限量 10,000 枚","special":true}}'::json,
                10000, NOW(), NOW(), NULL
            )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            task_type = EXCLUDED.task_type,
            status = EXCLUDED.status,
            reward_fan_tokens = EXCLUDED.reward_fan_tokens,
            target_post_id = EXCLUDED.target_post_id,
            validation_rule = EXCLUDED.validation_rule,
            participation_limit = EXCLUDED.participation_limit,
            updated_at = NOW();
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM fan_tasks
        WHERE id IN (
            '00000000-0000-0000-0000-000000000020',
            '00000000-0000-0000-0000-000000000021',
            '00000000-0000-0000-0000-000000000022',
            '00000000-0000-0000-0000-000000000023',
            '00000000-0000-0000-0000-000000000024',
            '00000000-0000-0000-0000-000000000026',
            '00000000-0000-0000-0000-000000000027',
            '00000000-0000-0000-0000-000000000028'
        );

        UPDATE fan_tasks
        SET title = '写下你的入坑故事',
            description = '领取任务后，在指定帖子回复不少于 10 个字，系统会立即确认完成。',
            reward_fan_tokens = 60,
            validation_rule = '{"minimum_reply_length":10}'::json,
            updated_at = NOW()
        WHERE id = '00000000-0000-0000-0000-000000000005';

        UPDATE fan_tasks
        SET title = '安利一首循环单曲',
            description = '领取任务后，在每周歌单帖子回复歌名与推荐理由即可完成。',
            reward_fan_tokens = 40,
            validation_rule = '{"minimum_reply_length":10}'::json,
            updated_at = NOW()
        WHERE id = '00000000-0000-0000-0000-000000000006';
        """
    )
