from datetime import timedelta

from eth_account import Account
from sqlmodel import col, select

from app.core.database import database_service
from app.models.base import utc_now
from app.models.community import CommunityPost, FanTokenLedger, TaskParticipation
from app.models.user import User, UserProfile, UserSession, Wallet
from app.services.auth import hash_session_token
from app.services.product_seed import (
    DAILY_TASK_ID,
    FAN_STORY_TASK_ID,
    FEAR_TASK_ID,
    WELCOME_POST_ID,
    WELCOME_TASK_ID,
)


async def create_official_member(raw_token: str) -> str:
    account = Account.create()
    async with database_service.session() as session:
        user = User(display_name="Community Flow Tester")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id, is_official_member=True, official_member_since=utc_now()),
                Wallet(
                    user_id=user.id,
                    address=account.address,
                    wallet_type="embedded",
                    provider="wallet",
                    is_primary=True,
                ),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()
        return user.id


async def test_join_check_in_reply_task_and_ledger_are_idempotent(client):
    raw_token = "community-task-flow-session-token"
    user_id = await create_official_member(raw_token)
    headers = {"Authorization": f"Bearer {raw_token}"}

    community_response = client.get("/api/v1/community", headers=headers)
    assert community_response.status_code == 200
    assert community_response.json()["slug"] == "fanora-official"
    assert community_response.json()["joined"] is False

    first_join = client.post("/api/v1/community/join", headers=headers)
    second_join = client.post("/api/v1/community/join", headers=headers)
    assert first_join.status_code == 200
    assert second_join.status_code == 200
    assert first_join.json()["joined"] is True

    first_check_in = client.post("/api/v1/check-ins", headers=headers)
    second_check_in = client.post("/api/v1/check-ins", headers=headers)
    assert first_check_in.status_code == 200
    assert first_check_in.json()["already_checked_in"] is False
    assert first_check_in.json()["reward_fan_tokens"] == 20
    assert first_check_in.json()["monthly_reward_fan_tokens"] == 20
    assert first_check_in.json()["monthly_records"] == [
        {
            "check_in_date": first_check_in.json()["check_in_date"],
            "reward_fan_tokens": 20,
        }
    ]
    assert second_check_in.status_code == 200
    assert second_check_in.json()["already_checked_in"] is True

    claim_response = client.post(f"/api/v1/tasks/{WELCOME_TASK_ID}/claim", headers=headers)
    repeated_claim = client.post(f"/api/v1/tasks/{WELCOME_TASK_ID}/claim", headers=headers)
    assert claim_response.status_code == 200
    assert repeated_claim.status_code == 200
    assert claim_response.json()["participation_status"] == "claimed"

    reply_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
        headers=headers,
        json={"body": "第一次听到现场版时，我立刻被那段旋律击中了。"},
    )
    assert reply_response.status_code == 201

    tasks_response = client.get("/api/v1/tasks", headers=headers)
    task = next(item for item in tasks_response.json() if item["id"] == WELCOME_TASK_ID)
    assert task["participation_status"] == "rewarded"
    assert task["unavailable_reason"] == "任务已完成"

    second_reply_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
        headers=headers,
        json={"body": "后来每次再听到这首歌，我都会想起第一次入坑的晚上。"},
    )
    assert second_reply_response.status_code == 201

    ledger_response = client.get("/api/v1/fan-tokens/me/ledger", headers=headers)
    assert ledger_response.status_code == 200
    entries = ledger_response.json()
    task_entries = [entry for entry in entries if entry["source_type"] == "task"]
    assert len(task_entries) == 1
    assert task_entries[0]["delta"] == 80

    async with database_service.session() as session:
        participation = (
            await session.execute(
                select(TaskParticipation).where(
                    TaskParticipation.task_id == WELCOME_TASK_ID,
                    TaskParticipation.user_id == user_id,
                )
            )
        ).scalar_one()
        task_rewards = list(
            (
                await session.execute(
                    select(FanTokenLedger).where(
                        FanTokenLedger.task_id == WELCOME_TASK_ID,
                        FanTokenLedger.user_id == user_id,
                    )
                )
            ).scalars().all()
        )
        assert participation.status == "rewarded"
        assert len(task_rewards) == 1


async def test_pending_member_cannot_check_in_or_claim_task(client):
    account = Account.create()
    raw_token = "pending-community-member-session"
    async with database_service.session() as session:
        user = User(display_name="Pending Community Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id),
                Wallet(user_id=user.id, address=account.address, wallet_type="external", is_primary=True),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()
    headers = {"Authorization": f"Bearer {raw_token}"}
    assert client.post("/api/v1/community/join", headers=headers).status_code == 200
    assert client.post("/api/v1/check-ins", headers=headers).status_code == 403
    assert client.post(f"/api/v1/tasks/{WELCOME_TASK_ID}/claim", headers=headers).status_code == 403


async def test_auto_created_tasks_and_posts_use_portable_fallback_images(client):
    tasks = client.get("/api/v1/tasks").json()
    posts = client.get("/api/v1/community/posts").json()

    assert len(tasks) >= 10
    assert len(posts) >= 6
    assert all(task["presentation"]["image_url"].startswith("/img/") for task in tasks)
    assert all(post["cover_url"].startswith("/img/") for post in posts if post["cover_url"])


async def test_daily_creation_and_special_page_tasks_complete_without_manual_review(client):
    raw_token = "multi-mode-community-task-session"
    user_id = await create_official_member(raw_token)
    headers = {"Authorization": f"Bearer {raw_token}"}
    assert client.post("/api/v1/community/join", headers=headers).status_code == 200

    daily_claim = client.post(f"/api/v1/tasks/{DAILY_TASK_ID}/claim", headers=headers)
    assert daily_claim.status_code == 200
    assert daily_claim.json()["task_type"] == "daily_check_in"
    assert client.post("/api/v1/check-ins", headers=headers).status_code == 200

    story_claim = client.post(f"/api/v1/tasks/{FAN_STORY_TASK_ID}/claim", headers=headers)
    assert story_claim.status_code == 200
    assert story_claim.json()["required_tag"] == "#粉丝故事图文征集"
    story_post = client.post(
        "/api/v1/community/posts",
        headers=headers,
        json={
            "title": "一次值得长期保存的现场记忆",
            "body": "#粉丝故事图文征集\n\n## 最难忘的瞬间\n\n我最想留下的是 **全场合唱** 结束后，大家仍然不愿离开的那几分钟。",
            "category": "story",
            "cover_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII=",
            "image_urls": [
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII=",
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII=",
            ],
        },
    )
    assert story_post.status_code == 201
    assert story_post.json()["body"].startswith("#粉丝故事图文征集")
    assert story_post.json()["cover_url"].startswith("data:image/png;base64,")
    assert len(story_post.json()["image_urls"]) == 2
    async with database_service.session() as session:
        post_publish_entries = list(
            (
                await session.execute(
                    select(FanTokenLedger).where(
                        FanTokenLedger.user_id == user_id,
                        FanTokenLedger.source_type == "rule:post-publish",
                    )
                )
            ).scalars().all()
        )
        assert len(post_publish_entries) == 1
        assert post_publish_entries[0].delta == 5
    post_list = client.get("/api/v1/community/posts", headers=headers).json()
    story_summary = next(item for item in post_list if item["id"] == story_post.json()["id"])
    assert "##" not in story_summary["body_preview"]
    assert "**" not in story_summary["body_preview"]

    fear_claim = client.post(f"/api/v1/tasks/{FEAR_TASK_ID}/claim", headers=headers)
    assert fear_claim.status_code == 200
    short_note = client.post(
        f"/api/v1/tasks/{FEAR_TASK_ID}/complete",
        headers=headers,
        json={"interaction_note": "太难忘了"},
    )
    assert short_note.status_code == 422
    fear_complete = client.post(
        f"/api/v1/tasks/{FEAR_TASK_ID}/complete",
        headers=headers,
        json={
            "interaction_note": "最后一首歌结束时，全场一起亮起灯光的瞬间最难忘。",
            "image_urls": ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII="],
        },
    )
    assert fear_complete.status_code == 200
    assert fear_complete.json()["participation_status"] == "rewarded"
    assert fear_complete.json()["presentation"]["special"] is True

    async with database_service.session() as session:
        fear_participation = (
            await session.execute(
                select(TaskParticipation).where(
                    TaskParticipation.task_id == FEAR_TASK_ID,
                    TaskParticipation.user_id == user_id,
                )
            )
        ).scalar_one()
        assert fear_participation.submission["body"].startswith("最后一首歌")
        assert len(fear_participation.submission["image_urls"]) == 1

    tasks = client.get("/api/v1/tasks", headers=headers).json()
    statuses = {task["id"]: task["participation_status"] for task in tasks}
    assert statuses[DAILY_TASK_ID] == "rewarded"
    assert statuses[FAN_STORY_TASK_ID] == "rewarded"
    assert statuses[FEAR_TASK_ID] == "rewarded"

    ledger = client.get("/api/v1/fan-tokens/me/ledger", headers=headers).json()
    rewards = {entry["task_id"]: entry["delta"] for entry in ledger if entry["source_type"] == "task"}
    assert DAILY_TASK_ID not in rewards
    assert rewards[FAN_STORY_TASK_ID] == 180
    assert rewards[FEAR_TASK_ID] == 500
    assert any(entry["source_type"] == "rule:daily-check-in" and entry["delta"] == 20 for entry in ledger)

    async with database_service.session() as session:
        participations = list(
            (
                await session.execute(
                    select(TaskParticipation).where(TaskParticipation.user_id == user_id)
                )
            ).scalars().all()
        )
        assert {item.task_id for item in participations if item.status == "rewarded"}.issuperset(
            {DAILY_TASK_ID, FAN_STORY_TASK_ID, FEAR_TASK_ID}
        )


async def test_post_reactions_and_two_level_comments(client):
    raw_token = "community-social-interaction-session"
    user_id = await create_official_member(raw_token)
    headers = {"Authorization": f"Bearer {raw_token}"}
    assert client.post("/api/v1/community/join", headers=headers).status_code == 200

    like_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/like",
        headers=headers,
    )
    bookmark_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/bookmark",
        headers=headers,
    )
    assert like_response.status_code == 200
    assert like_response.json()["liked"] is True
    assert bookmark_response.status_code == 200
    assert bookmark_response.json()["bookmarked"] is True

    bookmark_off_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/bookmark",
        headers=headers,
    )
    bookmark_again_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/bookmark",
        headers=headers,
    )
    assert bookmark_off_response.status_code == 200
    assert bookmark_off_response.json()["bookmarked"] is False
    assert bookmark_again_response.status_code == 200
    assert bookmark_again_response.json()["bookmarked"] is True

    root_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
        headers=headers,
        json={"body": "这是第一层评论，用来讨论第一次听到这首歌的感受。"},
    )
    assert root_response.status_code == 201
    root_id = root_response.json()["id"]
    child_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
        headers=headers,
        json={
            "body": "这是第二层评论，继续回复上一条讨论内容。",
            "parent_reply_id": root_id,
        },
    )
    assert child_response.status_code == 201

    third_level_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
        headers=headers,
        json={
            "body": "系统不应该允许第三层评论继续嵌套。",
            "parent_reply_id": child_response.json()["id"],
        },
    )
    assert third_level_response.status_code == 409

    reply_like_response = client.post(
        f"/api/v1/community/replies/{root_id}/like",
        headers=headers,
    )
    assert reply_like_response.status_code == 200
    assert reply_like_response.json()["liked"] is True

    unlike_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/like",
        headers=headers,
    )
    repeated_like_response = client.post(
        f"/api/v1/community/posts/{WELCOME_POST_ID}/like",
        headers=headers,
    )
    assert unlike_response.status_code == 200
    assert unlike_response.json()["liked"] is False
    assert repeated_like_response.status_code == 200
    assert repeated_like_response.json()["liked"] is True

    detail_response = client.get(f"/api/v1/community/posts/{WELCOME_POST_ID}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["liked"] is True
    assert detail["bookmarked"] is True
    root = next(reply for reply in detail["replies"] if reply["id"] == root_id)
    assert root["like_count"] == 1
    assert root["liked"] is True
    assert len(root["children"]) == 1

    async with database_service.session() as session:
        interaction_entries = list(
            (
                await session.execute(
                    select(FanTokenLedger).where(
                        FanTokenLedger.user_id == user_id,
                        col(FanTokenLedger.source_type).in_(["rule:post-like", "rule:post-reply"]),
                    )
                )
            ).scalars().all()
        )
        post_like_entries = [entry for entry in interaction_entries if entry.source_type == "rule:post-like"]
        post_reply_entries = [entry for entry in interaction_entries if entry.source_type == "rule:post-reply"]
        assert len(post_like_entries) == 1
        assert post_like_entries[0].delta == 1
        assert len(post_reply_entries) == 2
        assert all(entry.delta == 1 for entry in post_reply_entries)

        welcome_post = await session.get(CommunityPost, WELCOME_POST_ID)
        assert welcome_post is not None
        bookmark_entries = list(
            (
                await session.execute(
                    select(FanTokenLedger).where(
                        FanTokenLedger.user_id == welcome_post.author_user_id,
                        FanTokenLedger.source_type == "rule:post-bookmark-received",
                        FanTokenLedger.source_id == WELCOME_POST_ID,
                    )
                )
            ).scalars().all()
        )
        assert len(bookmark_entries) == 1
        assert bookmark_entries[0].delta == 1


async def test_post_comments_are_paginated_by_root_comment(client):
    raw_token = "community-comment-pagination-session"
    await create_official_member(raw_token)
    headers = {"Authorization": f"Bearer {raw_token}"}
    assert client.post("/api/v1/community/join", headers=headers).status_code == 200

    for index in range(11):
        response = client.post(
            f"/api/v1/community/posts/{WELCOME_POST_ID}/replies",
            headers=headers,
            json={"body": f"第 {index + 1} 条顶级评论，用于验证社区评论的分页加载能力。"},
        )
        assert response.status_code == 201

    first_page = client.get(f"/api/v1/community/posts/{WELCOME_POST_ID}?reply_limit=10&reply_offset=0", headers=headers)
    assert first_page.status_code == 200
    assert len(first_page.json()["replies"]) == 10
    assert first_page.json()["has_more_replies"] is True
    assert first_page.json()["next_replies_offset"] == 10

    second_page = client.get(f"/api/v1/community/posts/{WELCOME_POST_ID}?reply_limit=10&reply_offset=10", headers=headers)
    assert second_page.status_code == 200
    assert 1 <= len(second_page.json()["replies"]) <= 10
    assert second_page.json()["has_more_replies"] is False
    assert second_page.json()["next_replies_offset"] is None


async def test_community_posts_support_stable_offset_pagination(client):
    first_page = client.get("/api/v1/community/posts?limit=2&offset=0")
    second_page = client.get("/api/v1/community/posts?limit=2&offset=2")

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    assert {post["id"] for post in first_page.json()}.isdisjoint(
        {post["id"] for post in second_page.json()}
    )
