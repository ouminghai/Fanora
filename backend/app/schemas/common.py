"""Shared HTTP response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str = "fanora-api"
    version: str
    environment: str
    components: dict[str, str] = Field(default_factory=dict)
