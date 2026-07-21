"""Pinata IPFS Platform adapter with bounded retries and no credential leakage."""

import asyncio
import json
from dataclasses import dataclass

import httpx

from app.core.config import settings


class PinataConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PinnedFile:
    cid: str
    pin_id: str | None


class PinataAdapter:
    @property
    def configured(self) -> bool:
        return bool(settings.pinata_jwt)

    async def _upload(self, *, filename: str, content: bytes, mime_type: str) -> PinnedFile:
        if not self.configured:
            raise PinataConfigurationError("Pinata JWT is not configured")
        last_error: Exception | None = None
        for attempt in range(settings.pinata_max_retries):
            try:
                async with httpx.AsyncClient(timeout=settings.pinata_timeout_seconds) as client:
                    response = await client.post(
                        settings.pinata_api_url,
                        headers={"Authorization": f"Bearer {settings.pinata_jwt}"},
                        files={"file": (filename, content, mime_type)},
                        data={"network": "public", "name": filename},
                    )
                    response.raise_for_status()
                    payload = response.json().get("data", response.json())
                    cid = payload.get("cid") or payload.get("IpfsHash")
                    if not cid:
                        raise RuntimeError("Pinata response did not include a CID")
                    return PinnedFile(cid=cid, pin_id=payload.get("id"))
            except (httpx.HTTPError, RuntimeError) as error:
                last_error = error
                if attempt + 1 < settings.pinata_max_retries:
                    await asyncio.sleep(2**attempt)
        raise RuntimeError("Pinata upload failed after bounded retries") from last_error

    async def pin_image(self, filename: str, content: bytes, mime_type: str) -> PinnedFile:
        return await self._upload(filename=filename, content=content, mime_type=mime_type)

    async def pin_metadata(self, filename: str, payload: dict) -> PinnedFile:
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return await self._upload(filename=filename, content=content, mime_type="application/json")

    @staticmethod
    def ipfs_uri(cid: str) -> str:
        return f"ipfs://{cid}"

    @staticmethod
    def gateway_url(cid: str) -> str:
        return f"{settings.pinata_gateway_url.rstrip('/')}/{cid}"


pinata_adapter = PinataAdapter()
