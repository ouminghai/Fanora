"""Seed Echo/Quests local images and 50 Eason fan-attraction posts."""

import argparse
import asyncio
import base64
import mimetypes
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlmodel import select

from app.core.database import database_service
from app.models.base import utc_now
from app.models.community import CommunityPost, FanTask
from app.models.user import Community, User
from app.services.product_seed import (
    OFFICIAL_COMMUNITY_ID,
    RESOURCE_POST_IMAGES,
    RESOURCE_TASK_IMAGES,
    SYSTEM_USER_ID,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_ROOT = PROJECT_ROOT / "resources"
POST_ID_TEMPLATE = "20000000-0000-0000-0000-{index:012d}"
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
EMOTION_WORDS = {
    "震撼",
    "热血",
    "感动",
    "惊喜",
    "治愈",
    "心酸",
    "浪漫",
    "疯狂",
    "温柔",
    "难忘",
    "燃",
    "戳心",
    "佩服",
    "激动",
    "舍不得",
    "惊艳",
    "泪目",
    "真诚",
    "沉醉",
    "释怀",
    "心动",
    "酣畅",
    "共鸣",
    "安心",
    "上头",
}


@dataclass(frozen=True, slots=True)
class PostSeed:
    title: str
    category: str
    observation: str
    question: str


POST_SEEDS = [
    PostSeed("1首歌就能让万人安静，太震撼了", "music", "前奏刚响，全场从聊天声切换成专注，这种默契像大家同时想起了同一段人生。", "你见过哪首歌一开场就让现场完全安静？"),
    PostSeed("2分钟全场大合唱，真的热血", "music", "他把麦克风轻轻递向观众，几万人立刻接住旋律，舞台和看台像变成了同一支乐队。", "如果只能选一次万人合唱，你最想听哪首？"),
    PostSeed("3个转音把情绪唱满，太感动", "music", "不是炫技，而是每个细小变化都在推动故事，听着听着就会想到自己没说出口的话。", "哪次现场演唱让你突然理解了一首老歌？"),
    PostSeed("4次临场变化都有惊喜，这就是现场", "music", "同一首歌到了不同城市会有不同呼吸和停顿，让熟悉的作品始终保有新鲜感。", "你最喜欢录音室版本，还是更不可预测的 Live？"),
    PostSeed("5万人一起被治愈，原来歌声真有力量", "story", "大家带着不同烦恼进场，却会在某个副歌里同时松一口气，这种共同体验特别珍贵。", "哪首歌曾经陪你走过一段低潮？"),
    PostSeed("6秒停顿唱出心酸，后劲太大", "music", "他很懂得给情绪留白，不急着把每句话唱满，反而让观众把自己的故事放进去。", "你最难忘他的哪个停顿或呼吸？"),
    PostSeed("7种舞台颜色都很浪漫，像一场电影", "creation", "灯光、影像和服装不只是装饰，而是在帮每首歌建立属于自己的空间。", "如果由你设计一首歌的舞台，会选什么颜色？"),
    PostSeed("8万人同时挥手，现场真的疯狂", "story", "从第一排到最高看台都在回应，一个人的动作能传遍整座场馆，这就是号召力最直观的样子。", "你在哪个现场瞬间感受过全场同频？"),
    PostSeed("9首慢歌连着听，竟然这么温柔", "music", "他能把宏大的场馆唱得像朋友坐在旁边聊天，距离一下子就消失了。", "哪首慢歌最像他在对你单独说话？"),
    PostSeed("10年后再听还是难忘，作品真的会长大", "story", "年轻时听爱情，后来听告别和选择，同一首歌会随着年龄不断出现新的答案。", "哪首歌陪你跨过了最长的一段时间？"),
    PostSeed("11次掌声都很燃，他一开口就稳了", "discussion", "不需要复杂口号，观众会自然地用掌声回应他的状态和表达。", "你觉得真正有号召力的歌手最重要的能力是什么？"),
    PostSeed("12句生活感太戳心，像在唱普通人的故事", "story", "他的作品常把小人物的犹豫、体面和遗憾唱得很具体，所以大家很容易认出自己。", "哪一首歌最像你的生活片段？"),
    PostSeed("13座城市都能唱成主场，真的佩服", "discussion", "语言和地域不同，但那些关于成长、关系和孤独的情绪没有边界。", "你觉得哪种情绪最能跨越城市和语言？"),
    PostSeed("14秒欢呼就让人激动，出场气场太强", "story", "灯还没完全亮，名字还没喊出口，观众已经知道今晚会留下值得记住的瞬间。", "你第一次等他出场时是什么感觉？"),
    PostSeed("15分钟安可还是舍不得，谁懂散场后的空落", "story", "最后一首结束后大家仍不愿离开，因为告别的不只是演出，也是那晚共同拥有的情绪。", "散场后你通常会循环哪首歌？"),
    PostSeed("16段现场改编太惊艳，老歌又活了一次", "music", "新的编曲没有抹掉原作的记忆，反而像给熟悉的朋友换了一个更成熟的表达。", "你最希望哪首经典作品重新编曲？"),
    PostSeed("17个瞬间让人泪目，情绪不是演出来的", "story", "真正打动人的往往不是高音，而是眼神、呼吸和一句唱得稍微不同的话。", "哪一个现场细节曾让你突然红了眼眶？"),
    PostSeed("18年还保留真诚，难怪大家一直在", "discussion", "长期吸引粉丝的不只是作品数量，还有他面对舞台和观众时始终认真。", "你因为什么从听众变成了长期支持者？"),
    PostSeed("19首歌连听也不累，完全沉醉", "music", "快歌、慢歌、叙事歌和实验表达彼此交替，让整场演出像一本有起伏的小说。", "你心中的完美歌单第一首和最后一首是什么？"),
    PostSeed("20岁听不懂的歌，如今终于释怀", "story", "有些作品要等经历到了才会打开，陈奕迅的歌常常在多年后突然和生活对上。", "你最近重新听懂了哪首歌？"),
    PostSeed("21次回看依然心动，这个舞台太有生命力", "creation", "镜头之外还有观众的呼吸、乐队的互动和临场变化，所以回看仍能发现新细节。", "你收藏最多的是哪一段现场视频？"),
    PostSeed("22首金曲唱得酣畅，情绪切换太顺", "music", "他能从轻松幽默走到深沉克制，却不会让人觉得割裂，整晚像一次完整旅程。", "你喜欢他更疯一点，还是更安静一点？"),
    PostSeed("23个故事产生共鸣，谁都能找到自己的那一首", "story", "有人听见爱情，有人听见友情，也有人听见与自己的和解，这种开放性让作品拥有很长的生命。", "你会把哪首歌送给现在的自己？"),
    PostSeed("24小时循环也很安心，声音像老朋友", "music", "熟悉的音色不会催你振作，只是陪你把复杂情绪慢慢放好。", "你需要陪伴时最先点开的歌是哪首？"),
    PostSeed("25秒前奏就上头，经典辨识度太高", "music", "很多作品不用等到人声出现，编曲一响，现场已经开始欢呼。", "哪段前奏能让你立刻认出歌名？"),
    PostSeed("26场演出依然震撼，每晚都不是复制粘贴", "discussion", "稳定完成只是基础，真正难得的是他会根据当晚状态和观众回应调整表达。", "你更看重演出的稳定，还是临场火花？"),
    PostSeed("27次全场回应太热血，号召力看得见", "story", "他不用反复带动气氛，观众自然知道何时合唱、何时安静、何时把掌声送出去。", "你最想站在哪个区域感受全场声浪？"),
    PostSeed("28句普通话也唱得感动，情绪从不打折", "music", "不同语言版本会有不同质感，但他总能抓住作品最核心的人物和情绪。", "你偏爱粤语作品还是国语作品？为什么？"),
    PostSeed("29次互动都有惊喜，幽默感也是魅力", "discussion", "认真唱歌之外，他会用轻松的表达拉近距离，让大型演出也有朋友聚会的松弛感。", "你记得他哪次让全场笑出来的互动？"),
    PostSeed("30天低潮被一首歌治愈，真的谢谢陪伴", "story", "作品没有替人解决问题，却能让人知道自己的感受并不孤单。", "哪首歌曾在你最需要时刚好出现？"),
    PostSeed("31岁再听还是心酸，成长原来有声音", "story", "年轻时觉得是情歌，后来才发现里面还有责任、遗憾和成年人保留的体面。", "哪首歌随着年龄变化最大？"),
    PostSeed("32束灯光照出浪漫，舞美懂得克制", "creation", "不是每一刻都追求耀眼，有时一束光和一个背影就足够把情绪推到最高。", "你最喜欢热闹舞台还是极简舞台？"),
    PostSeed("33次跳脱反差太疯狂，舞台人格真丰富", "discussion", "他可以上一秒认真叙事，下一秒彻底放开，这种反差让演出一直保持活力。", "你最喜欢他舞台上哪一种状态？"),
    PostSeed("34首歌里的温柔，不用大声也能抵达", "music", "他擅长把关心藏在细节里，不灌输答案，只让听众自己靠近情绪。", "哪首歌的温柔最不动声色？"),
    PostSeed("35公里散场路仍难忘，大家都在哼同一首", "story", "走出场馆后，陌生人因为同一场演出有了短暂默契，连回家的路都像演出的延长。", "你散场路上遇到过什么有趣的粉丝瞬间？"),
    PostSeed("36次鼓点把气氛点燃，乐队配合太燃", "music", "强大的现场不只属于主唱，乐队、和声和舞台团队共同托住了每次情绪爆发。", "你会特别留意现场里的哪件乐器？"),
    PostSeed("37个小表情太戳心，镜头根本藏不住", "story", "作品进入情绪后，他脸上的细微变化会让人物突然真实起来。", "哪段近景让你觉得他完全进入了歌曲？"),
    PostSeed("38场状态管理让人佩服，专业不是口号", "discussion", "巡演对体力和注意力都是长期考验，而他仍努力让每座城市得到完整体验。", "你最敬佩现场歌手的哪种职业能力？"),
    PostSeed("39秒万人欢呼太激动，这就是共同记忆", "story", "单独看只是一段视频，身处其中却会感到整座场馆的情绪从脚下升起来。", "你最想把哪个欢呼瞬间永久保存？"),
    PostSeed("40首还没听够就舍不得，歌单真的太强", "music", "经典作品太多，任何取舍都会让人遗憾，也说明他的音乐陪伴了太多人生阶段。", "如果能追加一首安可，你会投给谁？"),
    PostSeed("41种情绪都唱得惊艳，角色感太强", "music", "他不是用一种唱法处理所有作品，而是会先找到歌曲里的人，再决定声音应该站在哪里。", "你觉得他塑造得最完整的是哪首歌中的人物？"),
    PostSeed("42次回忆突然泪目，音乐真的会保存时间", "story", "一首歌能把人带回具体的街道、天气和陪伴过自己的人，这是作品最温柔的时间能力。", "哪首歌一响，你会立刻回到某一年？"),
    PostSeed("43句话都很真诚，聊天感让距离消失", "discussion", "他和观众交流时没有标准答案，更像分享当晚真实的想法。", "你喜欢演唱会里多一点聊天，还是多唱几首歌？"),
    PostSeed("44分钟慢歌段落让人沉醉，叙事感拉满", "music", "连续的情绪铺陈让人暂时忘记时间，像跟着一个角色走完了一段关系。", "你会怎样安排一组慢歌的顺序？"),
    PostSeed("45次听见终于释怀，原来遗憾也能被接住", "story", "好的作品不一定让人忘记遗憾，却能帮人用新的角度看待它。", "哪首歌让你和过去的自己和解了一点？"),
    PostSeed("46个舞台瞬间都心动，魅力来自不设限", "creation", "他愿意尝试不同造型、叙事和表演方式，让观众很难用单一标签定义他。", "你最想看到他下一次尝试什么舞台概念？"),
    PostSeed("47首串烧听得酣畅，经典密度太高", "music", "熟悉旋律一个接一个出现，观众的记忆也被连续打开，几乎没有冷场。", "你会把哪三首歌放进自己的限定串烧？"),
    PostSeed("48座城市都有共鸣，好音乐真的没有边界", "discussion", "无论观众来自哪里，大家都会在爱、失去、成长和自我怀疑里找到相似经验。", "你在哪座城市看过最难忘的一场？"),
    PostSeed("49次陪伴让人安心，喜欢从来不是一阵风", "story", "真正长久的吸引力，是作品在人生不同阶段都还能提供新的理解和陪伴。", "陈奕迅的音乐陪你走过了哪些阶段？"),
    PostSeed("50遍循环依然上头，这就是艺术感染力", "music", "旋律、文字、声音和舞台表达彼此支撑，让作品既容易靠近，又值得反复理解。", "最近哪首歌让你重新进入循环播放？"),
]

BODY_TEMPLATES = [
    """## {title}\n\n朋友，我最近回看现场时又被这个细节抓住了：{observation}\n\n陈奕迅的号召力不只是让人跟着唱，更厉害的是，他能让不同经历的人在同一刻找到自己的情绪。那种艺术感染力不是把答案塞给你，而是给你一个可以放下故事的位置。\n\n**聊聊看：** {question}\n\n#陈奕迅 #Eason #现场感染力""",
    """## {title}\n\n说真的，{observation}\n\n我觉得这就是陈奕迅很特别的地方：大场馆里有万人回应，但你还是会觉得这首歌像在和自己聊天。他把技巧藏在故事后面，也把舞台交给每一个愿意投入的人，这份号召力一点都不靠喊口号。\n\n{question} 我先等你们来分享。\n\n#陈奕迅 #粉丝共鸣 #演唱会""",
    """## {title}\n\n刚和朋友聊到这一幕：{observation}\n\n很多歌手能把现场唱热，陈奕迅却还能把热闹唱出层次，把安静唱出重量。观众愿意一起合唱，也愿意在需要的时候屏住呼吸，这份默契就是很真实的号召力。\n\n**想问问大家：** {question}\n\n#陈奕迅 #艺术感染力 #Live""",
    """## {title}\n\n不知道你们有没有同感，{observation}\n\n喜欢他的现场，很大一部分原因是每首歌都不只是完成任务。声音、表情、编曲和灯光会共同讲故事，让熟悉的作品在当晚重新发生一次，这种完整表达就是很难替代的艺术感染力。\n\n{question} 欢迎把你的版本留在评论里。\n\n#陈奕迅 #现场记忆 #粉丝故事""",
    """## {title}\n\n今天想和大家认真安利这个观察：{observation}\n\n陈奕迅真正有艺术感染力的地方，是他能把个人表达变成集体记忆。一个人开口，几万人回应，但每个人带走的又是属于自己的那部分。\n\n来交换答案吧：{question}\n\n#陈奕迅 #EasonChan #音乐共鸣""",
]


def validate_post_seeds() -> None:
    if len(POST_SEEDS) != 50:
        raise ValueError(f"Expected 50 post seeds, found {len(POST_SEEDS)}")
    for index, seed in enumerate(POST_SEEDS, start=1):
        if re.search(r"\d", seed.title) is None:
            raise ValueError(f"Post {index} title does not contain a number: {seed.title}")
        if not any(word in seed.title for word in EMOTION_WORDS):
            raise ValueError(f"Post {index} title does not contain an emotion word: {seed.title}")
        if len(seed.title) > 120:
            raise ValueError(f"Post {index} title is too long")


def validate_resource_files(resource_root: Path) -> None:
    required_paths = {
        *(resource_root / relative_path for relative_path in RESOURCE_POST_IMAGES.values()),
        *(resource_root / relative_path for relative_path in RESOURCE_TASK_IMAGES.values()),
    }
    missing_paths = sorted(path for path in required_paths if not path.is_file())
    if missing_paths:
        formatted = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(
            f"Missing {len(missing_paths)} required Echo/Quests image file(s) under {resource_root}:\n{formatted}\n"
            "Run this script from a checkout that contains the local resources directory, or pass --resources-dir."
        )


def select_resource_images(resource_root: Path, limit: int) -> list[Path]:
    images = sorted(
        (
            path
            for path in resource_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ),
        key=lambda path: (path.stat().st_size, path.as_posix()),
    )
    if len(images) < limit:
        raise FileNotFoundError(f"Expected at least {limit} resource images, found {len(images)}")
    return images[:limit]


def image_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_body(seed: PostSeed, index: int) -> str:
    template = BODY_TEMPLATES[(index - 1) % len(BODY_TEMPLATES)]
    return template.format(
        title=seed.title,
        observation=seed.observation,
        question=seed.question,
    )


async def seed_posts(*, dry_run: bool, resource_root: Path) -> None:
    validate_post_seeds()
    validate_resource_files(resource_root)
    images = select_resource_images(resource_root, len(POST_SEEDS))
    if dry_run:
        print("Echo post images:")
        for post_id, relative_path in RESOURCE_POST_IMAGES.items():
            print(f"- {post_id} <- {resource_root / relative_path}")
        print("Quest images:")
        for catalog_key, relative_path in RESOURCE_TASK_IMAGES.items():
            print(f"- {catalog_key} <- {resource_root / relative_path}")
        print("Eason fan attraction posts:")
        for index, (seed, image) in enumerate(zip(POST_SEEDS, images, strict=True), start=1):
            print(f"{index:02d}. {seed.title} <- {image}")
        return

    async with database_service.session() as session:
        if await session.get(User, SYSTEM_USER_ID) is None:
            raise RuntimeError("Fanora system user is missing; initialize the application database first")
        if await session.get(Community, OFFICIAL_COMMUNITY_ID) is None:
            raise RuntimeError("Fanora official community is missing; initialize the application database first")

        base_posts: dict[str, CommunityPost] = {}
        for post_id in RESOURCE_POST_IMAGES:
            post = await session.get(CommunityPost, post_id)
            if post is None:
                raise RuntimeError(f"Echo base post is missing: {post_id}; run database migrations first")
            base_posts[post_id] = post

        tasks = (await session.execute(select(FanTask))).scalars().all()
        tasks_by_catalog_key = {
            presentation["catalog_key"]: task
            for task in tasks
            if isinstance(task.validation_rule, dict)
            and isinstance((presentation := task.validation_rule.get("presentation")), dict)
            and isinstance(presentation.get("catalog_key"), str)
        }
        missing_task_keys = sorted(set(RESOURCE_TASK_IMAGES) - tasks_by_catalog_key.keys())
        if missing_task_keys:
            raise RuntimeError(
                f"Quest records are missing for catalog keys: {', '.join(missing_task_keys)}; run database migrations first"
            )

        for post_id, relative_path in RESOURCE_POST_IMAGES.items():
            base_posts[post_id].cover_url = image_data_url(resource_root / relative_path)
            base_posts[post_id].updated_at = utc_now()

        for catalog_key, relative_path in RESOURCE_TASK_IMAGES.items():
            task = tasks_by_catalog_key[catalog_key]
            validation_rule = deepcopy(task.validation_rule)
            validation_rule["presentation"]["image_url"] = image_data_url(resource_root / relative_path)
            task.validation_rule = validation_rule
            task.updated_at = utc_now()

        now = utc_now()
        created = 0
        updated = 0
        for index, (seed, image) in enumerate(zip(POST_SEEDS, images, strict=True), start=1):
            post_id = POST_ID_TEMPLATE.format(index=index)
            post = await session.get(CommunityPost, post_id)
            cover_url = image_data_url(image)
            created_at = now - timedelta(hours=(len(POST_SEEDS) - index) * 6)
            if post is None:
                post = CommunityPost(
                    id=post_id,
                    community_id=OFFICIAL_COMMUNITY_ID,
                    author_user_id=SYSTEM_USER_ID,
                    title=seed.title,
                    body=render_body(seed, index),
                    cover_url=cover_url,
                    image_urls=[],
                    category=seed.category,
                    status="published",
                    created_at=created_at,
                    updated_at=created_at,
                )
                session.add(post)
                created += 1
            else:
                post.title = seed.title
                post.body = render_body(seed, index)
                post.cover_url = cover_url
                post.image_urls = []
                post.category = seed.category
                post.status = "published"
                post.created_at = created_at
                post.updated_at = created_at
                updated += 1

        await session.commit()
        print(
            "Seed completed: "
            f"echo_posts_updated={len(base_posts)}, quests_updated={len(RESOURCE_TASK_IMAGES)}, "
            f"eason_posts_created={created}, eason_posts_updated={updated}, eason_posts_total={len(POST_SEEDS)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print content without writing to the database")
    parser.add_argument(
        "--resources-dir",
        type=Path,
        default=RESOURCE_ROOT,
        help=f"Local image directory (default: {RESOURCE_ROOT})",
    )
    return parser.parse_args()


async def main(*, dry_run: bool, resource_root: Path) -> None:
    try:
        await seed_posts(dry_run=dry_run, resource_root=resource_root.expanduser().resolve())
    finally:
        await database_service.close()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(main(dry_run=arguments.dry_run, resource_root=arguments.resources_dir))
