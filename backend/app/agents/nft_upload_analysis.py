"""Multimodal metadata analysis for creator-uploaded NFT artwork."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import logger
from app.schemas.nft_agent import (
    NftUploadedImageAnalysisResponse,
    NftUploadedImageNarrative,
    NftVisualTemplate,
)
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable

UPLOAD_ANALYSIS_SYSTEM_PROMPT = """
你是 Fanora 的 NFT 视觉策展人与粉丝文化编辑。分析用户实际上传的图片，只返回符合 schema 的 JSON 对象。

必须返回：name、description、story_summary、image_prompt、suggested_attributes。
- name：简洁、适合收藏柜展示的中文 NFT 名称，避免通用的“无题”或文件名。
- description：两到三句中文作品描述，忠于画面，不虚构真实演唱会、人物关系或独家经历。
- story_summary：总结画面的主体、构图、颜色、材质和情绪，供后续五维分析使用。
- image_prompt：完整描述当前图片的视觉内容，并包含给定视觉模板和视觉风格，方便后续继续迭代。
- suggested_attributes：最多 8 个公开属性，每项只含 trait_type 和 value。

不得声称已经发行、上链、固定到 IPFS 或具有投资价值。不得仅根据文件名猜测内容。
""".strip()


class NftUploadAnalysisAgent:
    def __init__(self, model_service: LLMService = llm_service) -> None:
        self._model_service = model_service

    @staticmethod
    def _fallback(
        template: NftVisualTemplate,
        style_prompt: str,
    ) -> NftUploadedImageAnalysisResponse:
        return NftUploadedImageAnalysisResponse(
            name=f"{template.name}藏品"[:100],
            description="这件作品来自创作者上传的原创画面，保留当前构图、色彩与视觉主体，并作为可继续编辑的粉丝收藏品进入版本柜。",
            story_summary="创作者上传了一张待策展的 NFT 画面，当前版本将结合所选视觉模板与视觉风格继续完成收藏品分析。",
            image_prompt=(
                f"Use the uploaded artwork as the visual source of truth. Preserve its subject, composition, palette, "
                f"materials and emotional atmosphere. Visual template: {template.prompt}. Selected visual style: {style_prompt}."
            )[:1500],
            suggested_attributes=[
                {"trait_type": "来源", "value": "创作者上传"},
                {"trait_type": "视觉模板", "value": template.name[:120]},
            ],
            theme=template.name,
            metadata_source="rules",
            degraded=True,
        )

    async def analyze(
        self,
        *,
        image_url: str,
        template: NftVisualTemplate,
        style_name: str,
        style_prompt: str,
    ) -> NftUploadedImageAnalysisResponse:
        fallback = self._fallback(template, style_prompt)
        if not self._model_service.available:
            return fallback
        instruction = (
            f"视觉模板：{template.name}\n"
            f"模板提示词：{template.prompt}\n"
            f"用户选择的视觉风格：{style_name}\n"
            f"视觉风格提示词：{style_prompt}\n"
            "请直接观察图片后生成 NFT 名称、描述、故事摘要、可迭代图片提示词和公开属性。"
        )
        try:
            result = await self._model_service.call_structured(
                [
                    SystemMessage(content=UPLOAD_ANALYSIS_SYSTEM_PROMPT),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": instruction},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ]
                    ),
                ],
                NftUploadedImageNarrative,
            )
            return NftUploadedImageAnalysisResponse(
                **result.model_dump(),
                theme=template.name,
                metadata_source="llm",
                degraded=False,
            )
        except (LLMUnavailable, ValueError, TypeError):
            logger.exception("nft_uploaded_image_analysis_fallback")
            return fallback


nft_upload_analysis_agent = NftUploadAnalysisAgent()
