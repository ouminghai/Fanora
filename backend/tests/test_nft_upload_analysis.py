from app.agents.nft_upload_analysis import NftUploadAnalysisAgent
from app.schemas.nft_agent import NftUploadedImageNarrative, NftVisualTemplate


def _template() -> NftVisualTemplate:
    return NftVisualTemplate(
        id="concert",
        name="演唱会纪念",
        category="音乐",
        description="演唱会收藏品模板",
        prompt="premium concert keepsake with layered paper and cinematic light",
        palette=["#8B5CF6"],
        elements=["票根"],
        forbidden=["水印"],
        preview_image_url="https://img.example/template.webp",
        reference_image_urls=[],
        is_system=True,
    )


class UnavailableModelService:
    available = False


class CapturingModelService:
    available = True

    def __init__(self) -> None:
        self.messages = []

    async def call_structured(self, messages, response_model):
        self.messages = messages
        assert response_model is NftUploadedImageNarrative
        return response_model(
            name="花海回声",
            description="画面以盛放花朵和双重人物侧影构成梦境舞台，冷灰背景衬托鲜艳花色。它适合作为演唱会记忆主题的收藏海报。",
            story_summary="双重人物侧影围绕中央花海形成对称构图，灰蓝云雾与高饱和花朵营造梦境和纪念感。",
            image_prompt="surreal concert keepsake, mirrored portraits, vivid flowers, cinematic gray-blue clouds",
            suggested_attributes=[{"trait_type": "构图", "value": "镜像双生"}],
        )


async def test_uploaded_image_analysis_has_deterministic_fallback() -> None:
    result = await NftUploadAnalysisAgent(UnavailableModelService()).analyze(
        image_url="https://img.example/upload.webp",
        template=_template(),
        style_name="典藏票根",
        style_prompt="tactile ticket stub",
    )

    assert result.metadata_source == "rules"
    assert result.degraded is True
    assert result.name
    assert result.description
    assert result.suggested_attributes[0].value == "创作者上传"


async def test_uploaded_image_analysis_sends_actual_image_to_multimodal_llm() -> None:
    model = CapturingModelService()
    result = await NftUploadAnalysisAgent(model).analyze(
        image_url="https://img.example/upload.webp",
        template=_template(),
        style_name="典藏票根",
        style_prompt="tactile ticket stub",
    )

    assert result.metadata_source == "llm"
    assert result.name == "花海回声"
    human_content = model.messages[1].content
    assert human_content[1] == {
        "type": "image_url",
        "image_url": {"url": "https://img.example/upload.webp"},
    }
