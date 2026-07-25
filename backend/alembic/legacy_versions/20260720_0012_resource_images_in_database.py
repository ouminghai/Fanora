"""Set portable fallback images for task and post records.

The original version read ignored developer-local image assets. Production
migrations must be reproducible without those files, so Base64 image import now lives in
``scripts/seed_eason_fan_attraction_posts.py``.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260720_0012"
down_revision = "20260720_0011"
branch_labels = None
depends_on = None

POST_BODIES = {
    "00000000-0000-0000-0000-000000000003": """## 第一次被一首歌击中的时候

有些喜欢没有预告。可能是耳机里的一句旋律，也可能是舞台灯亮起时，突然觉得自己的情绪被准确说中了。

> 真正重要的不是入坑有多早，而是那份喜欢如何陪你走到今天。

### 可以从这些线索开始

- 当时你在哪里？
- 是哪首歌、哪次舞台或哪句表达打动了你？
- 后来它怎样进入了你的生活？

认真回复即可完成对应粉丝任务，无需等待人工审核。""",
    "00000000-0000-0000-0000-000000000004": """## 本周共听：舍不得切掉的一首歌

把最近反复播放的歌留在这里，也说说它为什么值得被更多人听见。

### 推荐格式

1. 写下歌名或现场版本。
2. 分享你最喜欢的情绪、编曲或舞台瞬间。
3. 邀请下一位粉丝继续推荐。

发布成功后，已领取的歌词接龙任务会由系统直接验证。""",
    "00000000-0000-0000-0000-000000000010": """## 灯光熄灭之后，合唱还留在耳边

散场并不等于结束。人群慢慢离开，手机里的片段、朋友的拥抱和最后一首歌仍会把我们带回现场。

> 你最舍不得的是灯光、歌声，还是身边一起唱歌的人？

写下一段你想长期保存的现场记忆，让相似的瞬间在社区里重新相遇。""",
    "00000000-0000-0000-0000-000000000011": """## 一张纪念卡可以装下什么？

如果要为自己的粉丝旅程设计一张纪念卡，你会如何选择颜色、日期与文字？

| 元素 | 灵感方向 |
| --- | --- |
| 主色 | 一次舞台的灯光 |
| 日期 | 第一次听见或第一次到场 |
| 文字 | 一句属于自己的陪伴宣言 |

把你的设计想法发布出来，优秀灵感可以继续进入周年共创。""",
    "00000000-0000-0000-0000-000000000012": """## 今晚耳机里的现场感

同一首歌到了现场，呼吸、停顿和全场回应都会让它拥有新的生命。

- 最近反复播放的是哪个 Live 版本？
- 哪个细节让你愿意一听再听？
- 如果推荐给第一次听的人，你会怎样介绍？

留下你的选择，也去看看其他粉丝正在循环什么。""",
    "00000000-0000-0000-0000-000000000013": """## 让每一份支持被看见

Fanora 共创海报希望收集粉丝对 **Proof of Fandom** 的不同理解：长期陪伴、现场参与、内容创作，以及一次次真实交流。

### 参与方式

1. 选择图片、配色或一句核心表达。
2. 发布你的共创说明。
3. 浏览并回应其他粉丝的作品。

优秀灵感会进入后续社区共创提案。""",
}

LEGACY_POST_IMAGES = {
    "00000000-0000-0000-0000-000000000003": "/img/fanora/activity-community.jpg",
    "00000000-0000-0000-0000-000000000004": "/img/fanora/activity-music.jpg",
    "00000000-0000-0000-0000-000000000010": "/img/fanora/activity-concert.jpg",
    "00000000-0000-0000-0000-000000000011": "/img/fanora/activity-badge.jpg",
    "00000000-0000-0000-0000-000000000012": "/img/fanora/eason-concert.webp",
    "00000000-0000-0000-0000-000000000013": "/img/fanora/activity-community.jpg",
}

LEGACY_POST_BODIES = {
    "00000000-0000-0000-0000-000000000003": "欢迎来到 Fanora。分享你第一次被一首歌、一次舞台或一句歌词打动的故事。认真回复即可完成对应粉丝任务，无需等待人工审核。",
    "00000000-0000-0000-0000-000000000004": "留下歌名和推荐理由，也可以说说它陪你走过了怎样的一段时间。回复发布成功后，已领取任务会由系统直接验证。",
    "00000000-0000-0000-0000-000000000010": "灯光熄灭、人群慢慢离场，但耳边的合唱好像还没有结束。分享一段你最想留住的现场记忆。",
    "00000000-0000-0000-0000-000000000011": "如果能为自己的粉丝旅程设计一张纪念卡，你会放入哪一句歌词、哪一种颜色和哪段日期？",
    "00000000-0000-0000-0000-000000000012": "有些现场版本会让熟悉的歌突然拥有新的呼吸。留下你最近反复播放的一段 Live。",
    "00000000-0000-0000-0000-000000000013": "用图片、文字或配色表达你理解的 Proof of Fandom。优秀灵感会进入后续社区共创提案。",
}

LEGACY_TASK_IMAGES = {
    "daily-check-in": "/img/fanora/activity-checkin.jpg",
    "fear-and-dreams": "/img/fanora/activity-concert.jpg",
    "new-song-listening": "/img/fanora/activity-music.jpg",
    "share-your-song": "/img/fanora/activity-community.jpg",
    "fan-story": "/img/fanora/activity-community.jpg",
    "anniversary-wishes": "/img/fanora/activity-badge.jpg",
    "classic-lyrics-chain": "/img/fanora/activity-music.jpg",
    "core-fan-identity": "/img/fanora/activity-badge.jpg",
    "city-checkin": "/img/fanora/activity-checkin.jpg",
    "anniversary-badge": "/img/fanora/activity-badge.jpg",
}


def set_task_image(catalog_key: str, image_url: str) -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE fan_tasks
            SET validation_rule = jsonb_set(
                validation_rule::jsonb,
                '{presentation,image_url}',
                to_jsonb(CAST(:image_url AS text)),
                true
            )::json,
            updated_at = NOW()
            WHERE validation_rule->'presentation'->>'catalog_key' = :catalog_key
            """
        ),
        {"catalog_key": catalog_key, "image_url": image_url},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for post_id, cover_url in LEGACY_POST_IMAGES.items():
        connection.execute(
            sa.text(
                """
                UPDATE community_posts
                SET cover_url = :cover_url, body = :body, updated_at = NOW()
                WHERE id = :post_id
                """
            ),
            {"post_id": post_id, "cover_url": cover_url, "body": POST_BODIES[post_id]},
        )
    for catalog_key, image_url in LEGACY_TASK_IMAGES.items():
        set_task_image(catalog_key, image_url)


def downgrade() -> None:
    connection = op.get_bind()
    for post_id, cover_url in LEGACY_POST_IMAGES.items():
        connection.execute(
            sa.text(
                """
                UPDATE community_posts
                SET cover_url = :cover_url, body = :body, updated_at = NOW()
                WHERE id = :post_id
                """
            ),
            {"post_id": post_id, "cover_url": cover_url, "body": LEGACY_POST_BODIES[post_id]},
        )
    for catalog_key, image_url in LEGACY_TASK_IMAGES.items():
        set_task_image(catalog_key, image_url)
