import pytest
from pydantic import ValidationError

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


def test_nft_creation_reference_image_accepts_supported_data_urls() -> None:
    request = NftDraftRequest(
        theme="现场记忆",
        story="把现场的灯光和与粉丝一起合唱的时刻保存下来。",
        reference_image_data_url="data:image/png;base64,aGVsbG8=",
    )
    assert request.reference_image_data_url is not None


def test_nft_creation_reference_image_rejects_unsupported_formats() -> None:
    with pytest.raises(ValidationError):
        NftDraftRequest(
            theme="现场记忆",
            story="把现场的灯光和与粉丝一起合唱的时刻保存下来。",
            reference_image_data_url="data:image/gif;base64,aGVsbG8=",
        )
