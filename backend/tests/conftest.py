import os
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["CHECKPOINT_DATABASE_URL"] = ""
os.environ["CHAIN_WRITES_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_MODEL"] = ""

from app.core.database import database_service  # noqa: E402
from app.main import app  # noqa: E402
from app.models.community import CommunityPost, FanTask  # noqa: E402
from app.services.product_seed import (  # noqa: E402
    CREATION_SEEDS,
    MUSIC_POST_ID,
    OFFICIAL_COMMUNITY_ID,
    POST_MARKDOWN_BODIES,
    SYSTEM_USER_ID,
    TASK_SEEDS,
    WELCOME_POST_ID,
)


async def seed_test_community_content() -> None:
    """Provide explicit lightweight content for in-memory API tests."""

    async with database_service.session() as session:
        session.add_all(
            [
                CommunityPost(
                    id=WELCOME_POST_ID,
                    community_id=OFFICIAL_COMMUNITY_ID,
                    author_user_id=SYSTEM_USER_ID,
                    title="你与喜欢的音乐，第一次相遇在什么时候？",
                    body=POST_MARKDOWN_BODIES[WELCOME_POST_ID],
                    cover_url="/img/fanora/activity-community.jpg",
                    category="story",
                ),
                CommunityPost(
                    id=MUSIC_POST_ID,
                    community_id=OFFICIAL_COMMUNITY_ID,
                    author_user_id=SYSTEM_USER_ID,
                    title="本周循环：安利一首你舍不得切掉的歌",
                    body=POST_MARKDOWN_BODIES[MUSIC_POST_ID],
                    cover_url="/img/fanora/activity-music.jpg",
                    category="music",
                ),
            ]
        )
        for post_id, title, _body, cover_url, category in CREATION_SEEDS:
            session.add(
                CommunityPost(
                    id=post_id,
                    community_id=OFFICIAL_COMMUNITY_ID,
                    author_user_id=SYSTEM_USER_ID,
                    title=title,
                    body=POST_MARKDOWN_BODIES[post_id],
                    cover_url=cover_url,
                    category=category,
                )
            )
        await session.flush()
        for task_seed in TASK_SEEDS:
            session.add(
                FanTask(
                    community_id=OFFICIAL_COMMUNITY_ID,
                    created_by_user_id=SYSTEM_USER_ID,
                    **deepcopy(task_seed),
                )
            )
        await session.commit()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        assert test_client.portal is not None
        test_client.portal.call(seed_test_community_content)
        yield test_client
