"""Structured LangGraph draft and image-generation schemas for fan NFTs."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.nft import PublicAttribute


class NftDraftRequest(BaseModel):
    theme: str = Field(min_length=2, max_length=120)
    story: str = Field(min_length=10, max_length=1500)
    visual_style: str = Field(default="premium music memorabilia", min_length=2, max_length=240)
    preferred_name: str | None = Field(default=None, max_length=100)
    reference_notes: str | None = Field(default=None, max_length=500)
    generate_image: bool = True


class NftMetadataNarrative(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=1000)
    image_prompt: str = Field(min_length=10, max_length=1500)
    suggested_attributes: list[PublicAttribute] = Field(default_factory=list, max_length=8)


class NftDraftResponse(BaseModel):
    name: str
    description: str
    theme: str
    image_prompt: str
    suggested_attributes: list[PublicAttribute]
    image_data_url: str | None
    metadata_source: Literal["rules", "llm"]
    image_source: Literal["openai", "not_requested", "unavailable"]
    degraded: bool
    image_error: str | None = None
    prompt_version: str = "fan-nft-draft-prompt-v1"
