"""Idempotent parent records for auto-created development and test databases."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Community, User

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"
OFFICIAL_COMMUNITY_ID = "00000000-0000-0000-0000-000000000002"
WELCOME_POST_ID = "00000000-0000-0000-0000-000000000003"
MUSIC_POST_ID = "00000000-0000-0000-0000-000000000004"
WELCOME_TASK_ID = "00000000-0000-0000-0000-000000000005"
MUSIC_TASK_ID = "00000000-0000-0000-0000-000000000006"
FEAR_TASK_ID = "00000000-0000-0000-0000-000000000020"
DAILY_TASK_ID = "00000000-0000-0000-0000-000000000021"
LISTENING_STREAK_TASK_ID = "00000000-0000-0000-0000-000000000022"
FAN_STORY_TASK_ID = "00000000-0000-0000-0000-000000000023"
ANNIVERSARY_WISH_TASK_ID = "00000000-0000-0000-0000-000000000024"
IDENTITY_TASK_ID = "00000000-0000-0000-0000-000000000026"
CITY_CHECKIN_TASK_ID = "00000000-0000-0000-0000-000000000027"
ANNIVERSARY_BADGE_TASK_ID = "00000000-0000-0000-0000-000000000028"

POST_MARKDOWN_BODIES = {
    WELCOME_POST_ID: """## 第一次被一首歌击中的时候

有些喜欢没有预告。可能是耳机里的一句旋律，也可能是舞台灯亮起时，突然觉得自己的情绪被准确说中了。

> 真正重要的不是入坑有多早，而是那份喜欢如何陪你走到今天。

### 可以从这些线索开始

- 当时你在哪里？
- 是哪首歌、哪次舞台或哪句表达打动了你？
- 后来它怎样进入了你的生活？

认真回复即可完成对应粉丝任务，无需等待人工审核。""",
    MUSIC_POST_ID: """## 本周共听：舍不得切掉的一首歌

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

CREATION_SEEDS = [
    (
        "00000000-0000-0000-0000-000000000010",
        "演唱会散场以后，你最舍不得的是哪一刻？",
        "灯光熄灭、人群慢慢离场，但耳边的合唱好像还没有结束。分享一段你最想留住的现场记忆。",
        "/img/fanora/activity-concert.jpg",
        "story",
    ),
    (
        "00000000-0000-0000-0000-000000000011",
        "把长期喜欢做成一张纪念卡",
        "如果能为自己的粉丝旅程设计一张纪念卡，你会放入哪一句歌词、哪一种颜色和哪段日期？",
        "/img/fanora/activity-badge.jpg",
        "creation",
    ),
    (
        "00000000-0000-0000-0000-000000000012",
        "今晚耳机里的现场感",
        "有些现场版本会让熟悉的歌突然拥有新的呼吸。留下你最近反复播放的一段 Live。",
        "/img/fanora/eason-concert.webp",
        "music",
    ),
    (
        "00000000-0000-0000-0000-000000000013",
        "Fanora 共创海报：让每一份支持被看见",
        "用图片、文字或配色表达你理解的 Proof of Fandom。优秀灵感会进入后续社区共创提案。",
        "/img/fanora/activity-community.jpg",
        "creation",
    ),
]


TASK_SEEDS = [
    {
        "id": DAILY_TASK_ID,
        "title": "每日 Fans Club 签到",
        "description": "领取后完成今日签到，在保持连续活跃的同时获得任务积分。",
        "task_type": "daily_check_in",
        "status": "published",
        "reward_fan_tokens": 20,
        "target_post_id": None,
        "validation_rule": {
            "presentation": {
                "catalog_key": "daily-check-in",
                "image_url": "/img/fanora/activity-checkin.jpg",
                "category": "daily",
                "interaction_prompt": "每天回来签到，连续 7 天还有额外奖励",
                "action_url": "/community#check-in",
                "action_label": "去签到",
                "badge_label": "每日互动",
            }
        },
    },
    {
        "id": FEAR_TASK_ID,
        "title": "FEAR and DREAMS 纪念票任务",
        "description": "进入演唱会纪念页完成打卡，领取 FAN；页面已为后续 NFT 纪念票铸造预留入口。",
        "task_type": "page_action",
        "status": "published",
        "reward_fan_tokens": 500,
        "target_post_id": None,
        "validation_rule": {
            "presentation": {
                "catalog_key": "fear-and-dreams",
                "image_url": "/img/fanora/activity-concert.jpg",
                "category": "event",
                "interaction_prompt": "留下你的现场记忆，激活纪念票收藏资格",
                "action_url": "/community/tasks/fear-and-dreams",
                "action_label": "进入纪念票页面",
                "badge_label": "特别任务",
                "special": True,
            }
        },
    },
    {
        "id": LISTENING_STREAK_TASK_ID,
        "title": "新歌连续收听 7 天",
        "description": "连续参与新歌共听与每日感受互动，完成七日陪伴记录。",
        "task_type": "streak",
        "status": "paused",
        "reward_fan_tokens": 120,
        "target_post_id": None,
        "validation_rule": {
            "presentation": {
                "catalog_key": "new-song-listening",
                "image_url": "/img/fanora/activity-music.jpg",
                "category": "music",
                "interaction_prompt": "连续记录收听感受，让歌单讨论持续发生",
                "action_url": "/community/creations?category=music",
                "action_label": "查看共听计划",
                "badge_label": "连续任务",
            }
        },
    },
    {
        "id": WELCOME_TASK_ID,
        "title": "分享你的入坑歌曲",
        "description": "领取任务后，在指定帖子分享最初打动你的歌曲与故事，系统即时确认完成。",
        "task_type": "post_reply",
        "status": "published",
        "reward_fan_tokens": 80,
        "target_post_id": WELCOME_POST_ID,
        "validation_rule": {
            "minimum_reply_length": 10,
            "presentation": {
                "catalog_key": "share-your-song",
                "image_url": "/img/fanora/activity-community.jpg",
                "category": "discussion",
                "interaction_prompt": "用一首歌开启交流，认识拥有相似记忆的粉丝",
                "action_url": f"/community/posts/{WELCOME_POST_ID}",
                "action_label": "去分享歌曲",
                "badge_label": "社区互动",
            },
        },
    },
    {
        "id": FAN_STORY_TASK_ID,
        "title": "粉丝故事图文征集",
        "description": "发布一条故事或共创内容，分享长期陪伴中的真实片段。",
        "task_type": "content_publish",
        "status": "published",
        "reward_fan_tokens": 180,
        "target_post_id": None,
        "validation_rule": {
            "content_categories": ["story", "creation"],
            "presentation": {
                "catalog_key": "fan-story",
                "image_url": "/img/fanora/activity-community.jpg",
                "category": "creation",
                "interaction_prompt": "用图文沉淀粉丝记忆，也为社区贡献优质内容",
                "action_url": "/community/creations?composer=1",
                "action_label": "发布粉丝故事",
                "badge_label": "内容共创",
            },
        },
    },
    {
        "id": ANNIVERSARY_WISH_TASK_ID,
        "title": "周年祝福共创",
        "description": "发布一条周年祝福或视觉灵感，与社区共同完成纪念作品。",
        "task_type": "content_publish",
        "status": "published",
        "reward_fan_tokens": 150,
        "target_post_id": None,
        "validation_rule": {
            "content_categories": ["creation", "discussion"],
            "presentation": {
                "catalog_key": "anniversary-wishes",
                "image_url": "/img/fanora/activity-badge.jpg",
                "category": "creation",
                "interaction_prompt": "共同创作周年内容，让每一份祝福被看见",
                "action_url": "/community/creations?composer=1",
                "action_label": "参与周年共创",
                "badge_label": "限时共创",
            },
        },
    },
    {
        "id": MUSIC_TASK_ID,
        "title": "经典歌词接龙",
        "description": "在指定音乐帖子回复一句歌词或下一句联想，和其他粉丝完成接龙。",
        "task_type": "post_reply",
        "status": "published",
        "reward_fan_tokens": 60,
        "target_post_id": MUSIC_POST_ID,
        "validation_rule": {
            "minimum_reply_length": 10,
            "presentation": {
                "catalog_key": "classic-lyrics-chain",
                "image_url": "/img/fanora/activity-music.jpg",
                "category": "music",
                "interaction_prompt": "回复歌词并邀请下一位粉丝接龙",
                "action_url": f"/community/posts/{MUSIC_POST_ID}",
                "action_label": "去歌词接龙",
                "badge_label": "社区挑战",
            },
        },
    },
    {
        "id": IDENTITY_TASK_ID,
        "title": "核心粉丝身份画像",
        "description": "完善粉丝资料并连接更多互动记录，后续将开放自动身份验证。",
        "task_type": "future",
        "status": "paused",
        "reward_fan_tokens": 300,
        "target_post_id": None,
        "validation_rule": {
            "presentation": {
                "catalog_key": "core-fan-identity",
                "image_url": "/img/fanora/activity-badge.jpg",
                "category": "identity",
                "interaction_prompt": "完善真实粉丝画像，为身份成长积累可验证记录",
                "action_url": "/profile",
                "action_label": "查看身份画像",
                "badge_label": "身份成长",
            }
        },
    },
    {
        "id": CITY_CHECKIN_TASK_ID,
        "title": "城市粉丝见面打卡",
        "description": "为线下活动预留定位与现场凭证验证，开放后可领取活动积分。",
        "task_type": "event_check_in",
        "status": "paused",
        "reward_fan_tokens": 300,
        "target_post_id": None,
        "validation_rule": {
            "presentation": {
                "catalog_key": "city-checkin",
                "image_url": "/img/fanora/activity-checkin.jpg",
                "category": "event",
                "interaction_prompt": "在线下相遇并留下城市粉丝活动记录",
                "action_url": "/community/tasks",
                "action_label": "等待活动开放",
                "badge_label": "线下活动",
            }
        },
    },
    {
        "id": ANNIVERSARY_BADGE_TASK_ID,
        "title": "周年限定 Badge 解锁",
        "description": "为周年链上收藏预留资格任务，当前先展示活动规则与未来领取入口。",
        "task_type": "future",
        "status": "paused",
        "reward_fan_tokens": 100,
        "target_post_id": None,
        "participation_limit": 10_000,
        "validation_rule": {
            "presentation": {
                "catalog_key": "anniversary-badge",
                "image_url": "/img/fanora/activity-badge.jpg",
                "category": "special",
                "interaction_prompt": "持续参与社区，为未来周年纪念收藏积累资格",
                "action_url": "/community/tasks",
                "action_label": "查看开放进度",
                "badge_label": "限量 10,000 枚",
                "special": True,
            }
        },
    },
]


async def seed_product_defaults(session: AsyncSession) -> None:
    """Create only the parent records required by an auto-created database."""

    if await session.get(User, SYSTEM_USER_ID) is None:
        session.add(User(id=SYSTEM_USER_ID, display_name="Fanora Protocol", status="system"))
        await session.flush()
    if await session.get(Community, OFFICIAL_COMMUNITY_ID) is None:
        session.add(
            Community(
                id=OFFICIAL_COMMUNITY_ID,
                owner_user_id=SYSTEM_USER_ID,
                slug="fanora-official",
                name="Fanora 链上社区",
                description="围绕音乐、现场与长期支持展开的链上共创空间。",
                logo_url="/img/logo.png",
            )
        )
        await session.flush()
    await session.commit()
