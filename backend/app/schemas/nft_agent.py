"""Structured LangGraph draft and image-generation schemas for fan NFTs."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.auth import validate_image_url
from app.schemas.nft import PublicAttribute


class NftDraftRequest(BaseModel):
    theme: str = Field(min_length=2, max_length=120)
    story: str = Field(min_length=10, max_length=1500)
    # Visual templates can contribute up to 2,000 characters of art direction,
    # followed by the selected style preset. Keep this aligned with
    # NftVisualTemplateCreate.prompt instead of rejecting valid saved templates.
    visual_style: str = Field(default="premium music memorabilia", min_length=2, max_length=2500)
    template_prompt: str | None = Field(default=None, max_length=2000)
    selected_style_prompt: str | None = Field(default=None, max_length=2000)
    preferred_name: str | None = Field(default=None, max_length=100)
    reference_notes: str | None = Field(default=None, max_length=500)
    reference_image_data_url: str | None = Field(default=None, max_length=7_000_000)
    iteration_image_data_url: str | None = Field(default=None, max_length=7_000_000)
    reference_image_urls: list[str] = Field(default_factory=list, max_length=6)
    iteration_image_url: str | None = Field(default=None, max_length=2048)
    generate_image: bool = True

    @field_validator("reference_image_data_url", "iteration_image_data_url")
    @classmethod
    def validate_reference_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        allowed_prefixes = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
        if not value.startswith(allowed_prefixes):
            raise ValueError("reference image must be a PNG, JPEG, or WebP base64 data URL")
        return value

    @field_validator("reference_image_urls")
    @classmethod
    def validate_reference_urls(cls, value: list[str]) -> list[str]:
        return [item if item.startswith("/img/") else (validate_image_url(item, label="Reference image") or "") for item in value]

    @field_validator("iteration_image_url")
    @classmethod
    def validate_iteration_url(cls, value: str | None) -> str | None:
        return validate_image_url(value, label="Iteration image")


class NftMetadataNarrative(BaseModel):
    name: str = Field(min_length=2, max_length=100, validation_alias=AliasChoices("name", "名称"))
    description: str = Field(min_length=10, max_length=1000, validation_alias=AliasChoices("description", "描述"))
    image_prompt: str = Field(min_length=10, max_length=1500, validation_alias=AliasChoices("image_prompt", "图片提示词"))
    suggested_attributes: list[PublicAttribute] = Field(
        default_factory=list,
        max_length=8,
        validation_alias=AliasChoices("suggested_attributes", "公开属性", "建议属性"),
    )

    @field_validator("suggested_attributes", mode="before")
    @classmethod
    def normalize_string_attributes(cls, value: object) -> object:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return [{"trait_type": "Attribute", "value": item[:120]} for item in value]
        return value


class NftDraftResponse(BaseModel):
    name: str
    description: str
    theme: str
    image_prompt: str
    suggested_attributes: list[PublicAttribute]
    image_data_url: str | None
    image_source_url: str | None = None
    metadata_source: Literal["rules", "llm"]
    image_source: Literal["openai", "siliconflow", "not_requested", "unavailable"]
    degraded: bool
    image_error: str | None = None
    prompt_version: str = "fan-nft-draft-prompt-v1"


class NftVisualTemplate(BaseModel):
    id: str
    name: str
    category: str
    description: str
    prompt: str
    palette: list[str]
    elements: list[str]
    forbidden: list[str]
    preview_image_url: str
    reference_image_urls: list[str] = Field(default_factory=list)
    owner_user_id: str | None = None
    source_post_id: str | None = None
    is_system: bool = False


class NftVisualTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    description: str = Field(min_length=4, max_length=500)
    prompt: str = Field(min_length=10, max_length=2000)
    reference_image_urls: list[str] = Field(default_factory=list, max_length=6)
    source_post_id: str | None = None
    palette: list[str] = Field(default_factory=lambda: ["#8B5CF6", "#EC4899", "#111827"], max_length=6)
    elements: list[str] = Field(default_factory=list, max_length=12)
    forbidden: list[str] = Field(default_factory=lambda: ["Logo", "水印", "可读文字"], max_length=12)

    @field_validator("reference_image_urls")
    @classmethod
    def validate_images(cls, value: list[str]) -> list[str]:
        return [item if item.startswith("/img/") else (validate_image_url(item, label="Template reference") or "") for item in value]


class NftVisualStyle(BaseModel):
    id: str
    name: str
    description: str
    prompt: str


class NftUploadedImageAnalyzeRequest(BaseModel):
    image_url: str = Field(min_length=12, max_length=2048)
    template_id: str = Field(min_length=2, max_length=64)
    visual_style: str = Field(min_length=2, max_length=40)

    @field_validator("image_url")
    @classmethod
    def validate_uploaded_image(cls, value: str) -> str:
        return validate_image_url(value, label="Uploaded NFT image") or ""


class NftUploadedImageNarrative(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=1000)
    story_summary: str = Field(min_length=10, max_length=1500)
    image_prompt: str = Field(min_length=10, max_length=1500)
    suggested_attributes: list[PublicAttribute] = Field(default_factory=list, max_length=8)


class NftUploadedImageAnalysisResponse(NftUploadedImageNarrative):
    theme: str
    metadata_source: Literal["rules", "llm"]
    degraded: bool = False
    prompt_version: str = "fan-nft-upload-analysis-v1"


class NftAgentChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=1200)
    template_id: str = Field(default="concert", min_length=2, max_length=40)
    visual_style: str = Field(default="cinematic", min_length=2, max_length=40)
    reference_image_urls: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("reference_image_urls")
    @classmethod
    def validate_chat_images(cls, value: list[str]) -> list[str]:
        return [item if item.startswith("/img/") else (validate_image_url(item, label="Reference image") or "") for item in value]


class NftAgentToolEvent(BaseModel):
    tool: str
    status: Literal["completed", "degraded"] = "completed"
    summary: str


class NftAgentChatResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    story_summary: str
    missing_fields: list[str]
    ready_for_generation: bool
    turn_count: int
    template: NftVisualTemplate
    draft: NftDraftResponse | None = None
    saved_template: NftVisualTemplate | None = None
    image_generation_recommended: bool = False
    image_generation_reason: str = ""
    image_generated: bool = False
    tool_events: list[NftAgentToolEvent] = Field(default_factory=list)
