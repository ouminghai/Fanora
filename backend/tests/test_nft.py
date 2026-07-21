import base64
import io

import pytest
from PIL import Image

from app.adapters.pinata import PinnedFile, pinata_adapter
from app.models.membership import MembershipLevel
from app.services.nft import NftService, NftValidationError


def image_data_url(width: int = 256, height: int = 256) -> str:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), "purple").save(stream, format="PNG")
    encoded = base64.b64encode(stream.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


def test_custom_badge_image_validation_accepts_safe_png() -> None:
    content, mime_type, width, height = NftService._parse_image(image_data_url())
    assert content
    assert mime_type == "image/png"
    assert (width, height) == (256, 256)


def test_custom_badge_image_validation_rejects_small_images() -> None:
    with pytest.raises(NftValidationError, match="dimensions"):
        NftService._parse_image(image_data_url(64, 64))


@pytest.mark.asyncio
async def test_membership_levels_pin_their_own_badge_images(monkeypatch) -> None:
    pinned_names: list[str] = []

    async def pin_image(filename: str, content: bytes, mime_type: str) -> PinnedFile:
        assert content
        assert mime_type == "image/png"
        pinned_names.append(filename)
        return PinnedFile(cid=f"cid-{filename}", pin_id=f"pin-{filename}")

    monkeypatch.setattr(pinata_adapter, "pin_image", pin_image)
    service = NftService()
    newborn = MembershipLevel(
        code="newborn", name="新生儿", description="新会员", rank=1,
        min_token_balance=0, max_token_balance=99, badge_image_url="/img/badges/new.png",
    )
    mild = MembershipLevel(
        code="mild-neuro", name="轻度神经", description="活跃会员", rank=2,
        min_token_balance=100, max_token_balance=499, badge_image_url="/img/badges/mild.png",
    )

    newborn_cid = await service._pin_membership_level_image(newborn)
    mild_cid = await service._pin_membership_level_image(mild)

    assert newborn_cid != mild_cid
    assert newborn.badge_image_cid == "cid-membership-level-newborn"
    assert mild.badge_image_cid == "cid-membership-level-mild-neuro"
    assert pinned_names == ["membership-level-newborn", "membership-level-mild-neuro"]
