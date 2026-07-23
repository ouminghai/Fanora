import pytest

from app.agents.nft_creation import nft_creation_agent
from app.schemas.nft_agent import NftDraftRequest


@pytest.mark.asyncio
async def test_nft_creation_agent_returns_editable_draft_without_auto_publish() -> None:
    result = await nft_creation_agent.create_draft(
        NftDraftRequest(
            theme="演唱会记忆",
            story="全场灯光亮起时，我想把那一刻保存成属于自己的粉丝纪念卡。",
            generate_image=False,
        )
    )

    assert result.name
    assert result.description
    assert result.suggested_attributes
    assert result.image_data_url is None
    assert result.image_source == "not_requested"
