"""Media upload endpoints backed by COS."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.adapters.cos import CosConfigurationError, CosUploadError, cos_adapter
from app.core.security import get_current_identity
from app.schemas.auth import ALLOWED_AVATAR_TYPES
from app.schemas.media import ImageUploadResponse
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/media")

MAX_COMMUNITY_IMAGE_BYTES = 1024 * 1024


@router.post("/images", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image must be JPEG, PNG, WebP, or GIF",
        )
    content = await file.read(MAX_COMMUNITY_IMAGE_BYTES + 1)
    if len(content) > MAX_COMMUNITY_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is larger than 1 MB")
    try:
        uploaded = await cos_adapter.upload_bytes(
            content=content,
            mime_type=file.content_type or "application/octet-stream",
            filename=f"fanora-{identity.user_id}",
        )
    except CosConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except (CosUploadError, OSError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {error}") from error
    return ImageUploadResponse(url=uploaded.url)
