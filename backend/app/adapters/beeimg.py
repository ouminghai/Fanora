"""BeeImg image hosting adapter."""

import base64
import binascii
import mimetypes
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import settings


class BeeImgConfigurationError(RuntimeError):
    """Raised when BeeImg credentials are missing."""


class BeeImgUploadError(RuntimeError):
    """Raised when BeeImg rejects an upload."""


@dataclass(frozen=True)
class BeeImgUpload:
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


class BeeImgAdapter:
    def __init__(self) -> None:
        self._cached_token: str | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.beeimg_token or (settings.beeimg_username and settings.beeimg_password))

    def _base_url(self) -> str:
        return settings.beeimg_base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self._base_url()}/{path.strip('/')}"

    async def _login(self, client: httpx.AsyncClient) -> str:
        if settings.beeimg_token:
            return settings.beeimg_token
        if self._cached_token:
            return self._cached_token
        if not settings.beeimg_username or not settings.beeimg_password:
            raise BeeImgConfigurationError("BeeImg username/password or token is required")
        payload = {
            "login_type": "username",
            "username": settings.beeimg_username,
            "password": settings.beeimg_password,
            "remember": "1",
        }
        response = await client.post(self._url(settings.beeimg_login_path), json=payload)
        if response.status_code >= 400 and response.status_code != 422:
            response = await client.post(self._url(settings.beeimg_login_path), data=payload)
        response.raise_for_status()
        body = response.json()
        token = self._extract_first(body, ("token", "access_token", "auth_token"))
        if not token and isinstance(body.get("data"), dict):
            token = self._extract_first(body["data"], ("token", "access_token", "auth_token"))
        if not token:
            raise BeeImgUploadError("BeeImg login did not return a token")
        self._cached_token = token
        return token

    @staticmethod
    def _extract_first(source: dict, keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _extract_url(body: dict) -> str | None:
        candidates: list[object] = [body.get("url")]
        data = body.get("data")
        if isinstance(data, dict):
            candidates.extend(
                [
                    data.get("public_url"),
                    data.get("url"),
                    data.get("src"),
                    data.get("path"),
                    data.get("image_url"),
                ]
            )
            links = data.get("links")
            if isinstance(links, dict):
                candidates.extend([links.get("url"), links.get("html"), links.get("markdown")])
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                return candidate
        return None

    async def upload_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str = "fanora-image",
    ) -> BeeImgUpload:
        if not self.configured:
            raise BeeImgConfigurationError("BeeImg is not configured")
        suffix = mimetypes.guess_extension(mime_type) or ".bin"
        if not Path(filename).suffix:
            filename = f"{filename}{suffix}"
        async with httpx.AsyncClient(timeout=settings.beeimg_timeout_seconds) as client:
            token = await self._login(client)
            storage_id = settings.beeimg_strategy_id or settings.beeimg_storage_id
            form: dict[str, str | int] = {
                "storage_id": storage_id,
                "album_id": settings.beeimg_album_id,
                "expired_at": "",
                "is_public": str(settings.beeimg_permission),
                "is_remove_exif": "",
                "intro": "",
            }
            if settings.beeimg_album_id:
                form["album_id"] = settings.beeimg_album_id
            response = await client.post(
                self._url(settings.beeimg_upload_path),
                data=form,
                files={"file": (filename, content, mime_type)},
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            body = response.json()
            if body.get("status") == "error":
                raise BeeImgUploadError(str(body.get("message") or "BeeImg upload failed"))
            url = self._extract_url(body)
            if not url:
                raise BeeImgUploadError("BeeImg upload did not return an image URL")
            return BeeImgUpload(url=url, raw=body)

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


beeimg_adapter = BeeImgAdapter()
