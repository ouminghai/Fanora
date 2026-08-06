"""Tencent Cloud COS image hosting adapter."""

import asyncio
import base64
import binascii
import mimetypes
import posixpath
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError

from app.core.config import settings


class CosConfigurationError(RuntimeError):
    """Raised when COS credentials or bucket settings are missing."""


class CosUploadError(RuntimeError):
    """Raised when COS rejects an upload."""


@dataclass(frozen=True)
class CosUpload:
    url: str
    raw: dict


def parse_data_url(value: str) -> tuple[bytes, str]:
    if not value.startswith("data:image/") or ";base64," not in value[:100]:
        raise ValueError("Expected an image data URL")
    header, encoded = value.split(",", 1)
    mime_type = header[5:].split(";", 1)[0]
    try:
        return base64.b64decode(encoded, validate=True), mime_type
    except binascii.Error as error:
        raise ValueError("Invalid image data URL") from error


class CosAdapter:
    @property
    def configured(self) -> bool:
        return bool(
            settings.cos_secret_id
            and settings.cos_secret_key
            and settings.cos_region
            and settings.cos_bucket
        )

    def _client(self) -> CosS3Client:
        if not self.configured:
            raise CosConfigurationError("Tencent Cloud COS is not configured")
        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
            Token=settings.cos_session_token or None,
            Scheme=settings.cos_scheme,
        )
        return CosS3Client(config)

    @staticmethod
    def _safe_filename(filename: str, mime_type: str) -> str:
        suffix = mimetypes.guess_extension(mime_type) or ".bin"
        name = Path(filename).name.strip() or "fanora-image"
        if not Path(name).suffix:
            name = f"{name}{suffix}"
        stem = Path(name).stem.replace(" ", "-") or "fanora-image"
        suffix = Path(name).suffix
        return f"{stem}-{uuid.uuid4().hex[:12]}{suffix}"

    def _object_key(self, filename: str, mime_type: str) -> str:
        prefix = settings.cos_key_prefix.strip("/")
        key = self._safe_filename(filename, mime_type)
        return posixpath.join(prefix, key) if prefix else key

    @staticmethod
    def _quote_key(key: str) -> str:
        return "/".join(quote(part) for part in key.split("/"))

    def _public_url(self, key: str) -> str:
        if settings.cos_public_base_url:
            return f"{settings.cos_public_base_url.rstrip('/')}/{self._quote_key(key)}"
        return (
            f"{settings.cos_scheme}://{settings.cos_bucket}.cos."
            f"{settings.cos_region}.myqcloud.com/{self._quote_key(key)}"
        )

    def _upload_sync(self, *, content: bytes, mime_type: str, key: str) -> dict:
        return self._client().put_object(
            Bucket=settings.cos_bucket,
            Body=content,
            Key=key,
            ContentType=mime_type,
        )

    async def upload_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str = "fanora-image",
    ) -> CosUpload:
        if not content:
            raise ValueError("Image content is empty")
        key = self._object_key(filename, mime_type)
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(self._upload_sync, content=content, mime_type=mime_type, key=key),
                timeout=settings.cos_timeout_seconds,
            )
        except TimeoutError as error:
            raise CosUploadError("Tencent Cloud COS upload timed out") from error
        except (CosClientError, CosServiceError) as error:
            raise CosUploadError(str(error)) from error
        return CosUpload(url=self._public_url(key), raw=raw)

    async def upload_data_url(self, value: str, *, filename: str = "fanora-image") -> str:
        content, mime_type = parse_data_url(value)
        result = await self.upload_bytes(content=content, mime_type=mime_type, filename=filename)
        return result.url

    async def ensure_remote_url(self, value: str | None, *, filename: str = "fanora-image") -> str | None:
        if not value:
            return None
        if value.startswith("data:image/"):
            return await self.upload_data_url(value, filename=filename)
        if value.startswith("/"):
            public_file = Path(__file__).resolve().parents[2] / "public" / value.lstrip("/")
            if not public_file.is_file():
                raise ValueError(f"Local image does not exist: {value}")
            mime_type = mimetypes.guess_type(public_file.name)[0] or "application/octet-stream"
            uploaded = await self.upload_bytes(content=public_file.read_bytes(), mime_type=mime_type, filename=filename)
            return uploaded.url
        return value

    async def ensure_remote_urls(self, values: list[str], *, filename_prefix: str = "fanora-image") -> list[str]:
        remote_urls: list[str] = []
        for index, value in enumerate(values):
            remote = await self.ensure_remote_url(value, filename=f"{filename_prefix}-{index + 1}")
            if remote:
                remote_urls.append(remote)
        return remote_urls


cos_adapter = CosAdapter()
