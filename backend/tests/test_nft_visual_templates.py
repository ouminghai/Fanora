import pytest

from app.core.database import database_service
from app.models.nft import NftVisualTemplate as NftVisualTemplateModel
from app.schemas.nft_agent import NftVisualTemplateUpdate
from app.services.product_seed import SYSTEM_USER_ID
from app.services.nft_visual_templates import nft_visual_template_service


@pytest.mark.asyncio
async def test_template_update_keeps_private_templates_editable_and_rehosts_images(client) -> None:
    async with database_service.session() as session:
        session.add(
            NftVisualTemplateModel(
                id="custom-template",
                owner_user_id=SYSTEM_USER_ID,
                source_post_id=None,
                name="旧模板",
                category="粉丝周边",
                description="旧说明",
                prompt="old prompt",
                preview_image_url="https://example.com/old.webp",
                reference_image_urls=["https://example.com/old.webp"],
                palette=["#111111"],
                elements=["旧元素"],
                forbidden=["旧限制"],
                is_system=False,
            )
        )
        await session.commit()

    payload = NftVisualTemplateUpdate(
        name="新模板",
        category="音乐",
        description="更新后的说明",
        prompt="updated prompt",
        reference_image_urls=["data:image/png;base64,aGVsbG8="],
        palette=["#8B5CF6", "#EC4899", "#111827"],
        elements=["新元素"],
        forbidden=["Logo"],
    )

    async with database_service.session() as session:
        updated = await nft_visual_template_service.update(session, SYSTEM_USER_ID, "custom-template", payload)

    assert updated is not None
    assert updated.name == "新模板"
    assert updated.preview_image_url.startswith("https://fanora-1251127085.cos.ap-guangzhou.myqcloud.com/")
    assert updated.reference_image_urls == [updated.preview_image_url]


@pytest.mark.asyncio
async def test_template_update_rejects_system_templates(client) -> None:
    async with database_service.session() as session:
        session.add(
            NftVisualTemplateModel(
                id="system-template",
                owner_user_id=None,
                source_post_id=None,
                name="官方模板",
                category="粉丝周边",
                description="官方说明",
                prompt="official prompt",
                preview_image_url="https://example.com/system.webp",
                reference_image_urls=["https://example.com/system.webp"],
                palette=["#111111"],
                elements=[],
                forbidden=[],
                is_system=True,
            )
        )
        await session.commit()

    payload = NftVisualTemplateUpdate(
        name="系统改名",
        category="粉丝周边",
        description="不应该修改",
        prompt="official prompt",
        reference_image_urls=["https://example.com/another.webp"],
        elements=[],
        forbidden=[],
    )

    async with database_service.session() as session:
        result = await nft_visual_template_service.update(session, SYSTEM_USER_ID, "system-template", payload)

    assert result is None
