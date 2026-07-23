import pytest

from app.agents.content_review import content_review_agent
from app.schemas.content_review import ContentReviewRequest


@pytest.mark.asyncio
async def test_content_review_approves_relevant_fan_memory() -> None:
    result = await content_review_agent.review(
        ContentReviewRequest(
            task_id="fear-task",
            task_title="FEAR and DREAMS 纪念票任务",
            task_description="分享真实演唱会现场记忆",
            interaction_prompt="留下你的现场记忆",
            content_type="page_action",
            source_id="submission-1",
            body="最后一首歌结束时，全场一起亮起灯光的瞬间最难忘。",
        )
    )

    assert result.decision == "approved"
    assert result.relevant is True
    assert result.spam is False


@pytest.mark.asyncio
async def test_content_review_rejects_missing_tag_and_spam() -> None:
    result = await content_review_agent.review(
        ContentReviewRequest(
            task_id="story-task",
            task_title="粉丝故事图文征集",
            task_description="发布一段真实粉丝故事",
            content_type="post",
            source_id="post-1",
            title="测试",
            body="哈哈哈哈哈哈哈哈哈哈哈哈",
            required_tag="#粉丝故事图文征集",
        )
    )

    assert result.decision == "rejected"
    assert result.tag_present is False
    assert result.spam is True
