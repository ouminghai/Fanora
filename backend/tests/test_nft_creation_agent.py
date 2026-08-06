import pytest
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import ValidationError

import app.agents.nft_studio as nft_studio_module
from app.agents.nft_creation import (
    _image_log_value,
    _prepare_multimodal_references,
    _prioritized_image_prompt,
    _reference_images,
    _reference_locked_image_prompt,
    _siliconflow_generation_payload,
    _siliconflow_reference_payload,
    nft_creation_agent,
)
from app.agents.nft_studio import NftStudioAgent, _wants_generate_image
from app.core.database import database_service
from app.models.nft import NftVisualTemplate as NftVisualTemplateModel
from app.schemas.nft_agent import NftAgentChatRequest, NftDraftRequest, NftDraftResponse, NftVisualTemplate
from app.services.llm import LLMService
from app.services.product_seed import SYSTEM_USER_ID


def _test_visual_template(template_id: str = "concert", name: str = "演唱会纪念") -> NftVisualTemplate:
    return NftVisualTemplate(
        id=template_id,
        name=name,
        category="测试模板",
        description="仅用于验证数据库模板传入 Agent 的测试数据。",
        prompt="premium square fan collectible with tactile materials and emotional storytelling",
        palette=["#8B5CF6", "#EC4899", "#172554"],
        elements=["收藏品", "情绪光线", "层次构图"],
        forbidden=["Logo", "水印", "可读文字"],
        preview_image_url="https://img.example/template.webp",
        reference_image_urls=["https://img.example/template.webp"],
        is_system=True,
    )


async def _seed_test_visual_templates(templates: list[NftVisualTemplate]) -> None:
    async with database_service.session() as session:
        for template in templates:
            if await session.get(NftVisualTemplateModel, template.id) is None:
                session.add(NftVisualTemplateModel(**template.model_dump()))
        await session.commit()


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


@pytest.mark.parametrize(
    "message",
    ["生成图片", "立即生成", "先出图", "帮我出一张图", "做一张预览", "现在就生图", "重新画一版"],
)
def test_explicit_image_commands_have_priority_over_story_completeness(message: str) -> None:
    assert _wants_generate_image(message) is True


def test_image_edit_payload_sends_three_multimodal_references() -> None:
    references = _reference_images(
        {
            "iteration_image_url": "https://img.example/current.webp",
            "reference_image_urls": [
                "https://img.example/template.webp",
                "https://img.example/user.webp",
                "https://img.example/extra.webp",
            ],
        }
    )

    assert references == [
        "https://img.example/template.webp",
        "https://img.example/user.webp",
        "https://img.example/extra.webp",
    ]
    assert _siliconflow_reference_payload(references) == {
        "image": "https://img.example/template.webp",
        "image2": "https://img.example/user.webp",
        "image3": "https://img.example/extra.webp",
    }
    payload = _siliconflow_generation_payload(
        model="Qwen/Qwen-Image-Edit-2509",
        prompt="Preserve the reference visual language.",
        image_size="1024x1024",
        negative_prompt="logo, watermark",
        references=references,
    )
    assert payload["image"] == references[0]
    assert payload["image2"] == references[1]
    assert payload["image3"] == references[2]
    assert payload["num_inference_steps"] == 20
    assert payload["guidance_scale"] == 4
    assert "image_size" not in payload
    assert "batch_size" not in payload


def test_image_request_logs_redact_base64_reference_pixels() -> None:
    value = "data:image/jpeg;base64," + ("a" * 256)

    logged = _image_log_value({"image": value, "prompt": "keep the visual identity"})

    assert logged["image"] == "<data:image/jpeg;base64; payload_chars=256>"
    assert logged["prompt"] == "keep the visual identity"


@pytest.mark.asyncio
async def test_remote_references_are_sent_as_actual_multimodal_image_data() -> None:
    import httpx

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://img.example/reference.jpg"
        return httpx.Response(200, content=b"reference-pixels", headers={"content-type": "image/jpeg"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        prepared = await _prepare_multimodal_references(["https://img.example/reference.jpg"], http)

    assert prepared == ["data:image/jpeg;base64,cmVmZXJlbmNlLXBpeGVscw=="]


@pytest.mark.asyncio
async def test_reference_download_failure_retains_remote_url() -> None:
    import httpx

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("reference timed out", request=request)

    reference = "https://img.example/reference.jpg"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        prepared = await _prepare_multimodal_references([reference], http)

    assert prepared == [reference]


def test_reference_prompt_prevents_unrelated_subject_replacement() -> None:
    prompt = _reference_locked_image_prompt("Transform this into a premium photocard.", ["data:image/jpeg;base64,x"])

    assert "primary visual source of truth" in prompt
    assert "composition density" in prompt
    assert "unrelated single emblem" in prompt


def test_image_prompt_merges_database_template_and_selected_style_into_priority_one() -> None:
    prompt = _prioritized_image_prompt(
        {
            "template_prompt": "horizontal collectible ticket with a perforated stub",
            "selected_style_prompt": "gentle hand-drawn illustration with paper grain",
            "image_prompt": "warm memory expressed through amber light",
        }
    )

    assert "PRIORITY 1 is the mandatory combined visual constraint" in prompt
    assert "template defines the artwork form and composition" in prompt
    assert "selected visual style defines how the entire artwork is rendered" in prompt
    assert "PRIORITY 1 - VISUAL TEMPLATE + USER-SELECTED VISUAL STYLE" in prompt
    assert "PRIORITY 2 - USER-SELECTED VISUAL STYLE" not in prompt
    assert prompt.index("PRIORITY 1 - VISUAL TEMPLATE + USER-SELECTED VISUAL STYLE") < prompt.index("PRIORITY 2 - CURRENT NFT DETAILS")
    assert "horizontal collectible ticket" in prompt
    assert "gentle hand-drawn illustration" in prompt


def test_generated_preview_keeps_temporary_data_url_until_publish() -> None:
    generated = NftDraftResponse(
        name="大头仔",
        description="一件具有温暖陪伴感和收藏质感的原创粉丝 NFT。",
        theme="bigguy视觉模板",
        image_prompt="A tactile rounded collectible figure with cinematic lighting.",
        suggested_attributes=[],
        image_data_url="data:image/png;base64,aGVsbG8=",
        image_source_url="https://provider.example/generated.png",
        metadata_source="llm",
        image_source="siliconflow",
        degraded=False,
    )

    assert generated.image_data_url == "data:image/png;base64,aGVsbG8="
    assert generated.image_source_url == "https://provider.example/generated.png"


@pytest.mark.asyncio
async def test_image_tool_exception_is_reported_instead_of_evaluate_event(monkeypatch) -> None:
    @tool("generate_nft_image")
    async def failing_image_tool(runtime: ToolRuntime) -> str:
        """Simulate an image tool failure after image generation."""

        del runtime
        raise RuntimeError("图片生成服务暂时不可用")

    monkeypatch.setattr(nft_studio_module, "NFT_IMAGE_TOOLS", (failing_image_tool,))
    agent = NftStudioAgent(model_service=LLMService())
    template = _test_visual_template()

    result = await agent.chat(
        "creator-cos-error",
        NftAgentChatRequest(message="生成图片", template_id="concert"),
        template,
    )

    image_event = next(event for event in result.tool_events if event.tool == "generate_nft_image")
    assert image_event.status == "degraded"
    assert "图片生成服务暂时不可用" in image_event.summary
    assert all(event.tool != "evaluate_image_generation" for event in result.tool_events)


@pytest.mark.asyncio
async def test_explicit_image_request_invokes_image_tool_with_incomplete_story() -> None:
    agent = NftStudioAgent(model_service=LLMService())
    template = _test_visual_template()
    result = await agent.chat(
        "creator-explicit-preview",
        NftAgentChatRequest(message="生成图片", template_id="concert"),
        template,
    )

    assert result.ready_for_generation is False
    assert any(event.tool == "generate_nft_image" for event in result.tool_events)

    repeated = await agent.chat(
        "creator-explicit-preview",
        NftAgentChatRequest(
            conversation_id=result.conversation_id,
            message="立即生成",
            template_id="concert",
        ),
        template,
    )
    assert repeated.story_summary
    assert any(event.tool == "generate_nft_image" for event in repeated.tool_events)


@pytest.mark.asyncio
async def test_second_turn_invokes_preview_even_when_story_is_incomplete() -> None:
    agent = NftStudioAgent(model_service=LLMService())
    template = _test_visual_template("badge", "粉丝徽章")
    first = await agent.chat(
        "creator-second-turn-preview",
        NftAgentChatRequest(message="我喜欢轻松开心的感觉。", template_id="badge"),
        template,
    )
    second = await agent.chat(
        "creator-second-turn-preview",
        NftAgentChatRequest(
            conversation_id=first.conversation_id,
            message="颜色鲜艳一点。",
            template_id="badge",
        ),
        template,
    )

    assert second.turn_count == 2
    assert second.ready_for_generation is False
    assert any(event.tool == "generate_nft_image" for event in second.tool_events)


@pytest.mark.asyncio
async def test_nft_studio_agent_accumulates_history_and_builds_brief() -> None:
    agent = NftStudioAgent(model_service=LLMService())
    template = _test_visual_template()
    first = await agent.chat(
        "creator-1",
        NftAgentChatRequest(message="我想记录演唱会散场时，全场一起合唱的那个瞬间。", template_id="concert"),
        template,
    )
    assert first.ready_for_generation is False
    assert first.conversation_id
    assert first.tool_events[0].tool == "load_visual_template"
    assert first.draft is not None
    assert first.image_generated is False
    assert first.draft.image_data_url is None

    second = await agent.chat(
        "creator-1",
        NftAgentChatRequest(
            conversation_id=first.conversation_id,
            message="画面中心是落下的彩带和举起的灯牌，情绪是温暖、舍不得结束，但也很有归属感。",
            template_id="concert",
        ),
        template,
    )
    assert second.turn_count == 2
    assert second.ready_for_generation is True
    assert second.draft is not None
    assert second.draft.name
    assert "彩带" in second.story_summary
    assert second.image_generated is False
    assert second.image_generation_recommended is True
    assert any(event.tool == "generate_nft_image" for event in second.tool_events)


@pytest.mark.asyncio
async def test_nft_studio_template_tools_select_and_save_to_database(client) -> None:
    agent = NftStudioAgent(model_service=LLMService())
    concert = _test_visual_template("concert", "演唱会纪念")
    letter = _test_visual_template("letter", "粉丝来信")
    client.portal.call(_seed_test_visual_templates, [concert, letter])
    first = await agent.chat(
        SYSTEM_USER_ID,
        NftAgentChatRequest(message="我想记录一封陪伴了很多年的粉丝来信。", template_id=concert.id),
        concert,
        [concert, letter],
    )

    selected = await agent.chat(
        SYSTEM_USER_ID,
        NftAgentChatRequest(
            conversation_id=first.conversation_id,
            message="请帮我推荐粉丝来信模板，并继续优化这一版。",
            template_id=concert.id,
        ),
        concert,
        [concert, letter],
    )
    assert selected.template.id == "letter"
    assert any(event.tool == "select_visual_template" for event in selected.tool_events)

    saved = await agent.chat(
        SYSTEM_USER_ID,
        NftAgentChatRequest(
            conversation_id=first.conversation_id,
            message="把当前作品方向另存为模板。",
            template_id=letter.id,
        ),
        letter,
        [concert, letter],
    )
    assert saved.saved_template is not None
    assert saved.saved_template.owner_user_id == SYSTEM_USER_ID
    assert saved.saved_template.is_system is False
    assert any(event.tool == "save_visual_template" for event in saved.tool_events)
    assert saved.image_generated is False
    assert "另存为模板" not in saved.story_summary


@pytest.mark.asyncio
async def test_nft_studio_accepts_saved_template_prompts_longer_than_240_characters() -> None:
    agent = NftStudioAgent(model_service=LLMService())
    template = _test_visual_template().model_copy(
        update={
            "id": "bigguy-template",
            "name": "bigguy视觉模板",
            "prompt": (
                "Create a new original fan-merch NFT that preserves the visual language, "
                "collectible craftsmanship and emotional atmosphere of this NFT reference: bigguy. "
                "Use a bold rounded symbolic subject, tactile printed texture, playful color blocking, "
                "premium collectible finishing, balanced negative space and an original composition "
                "without copying protected characters, logos, watermarks or readable text."
            ),
        }
    )

    result = await agent.chat(
        "creator-long-template",
        NftAgentChatRequest(
            message="使用这个模板创作一件新的粉丝周边 NFT。",
            template_id=template.id,
            visual_style="photocard",
        ),
        template,
        [template],
    )

    assert result.draft is not None
    assert result.draft.image_data_url is None
    assert result.image_generated is False
