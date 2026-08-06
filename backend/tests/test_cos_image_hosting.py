import base64

from app.adapters.cos import CosUpload, cos_adapter
from scripts.seed_eason_fan_attraction_posts import CommunitySnapshot, SnapshotImageHoster


async def test_snapshot_image_hoster_replaces_and_deduplicates_base64_images(monkeypatch) -> None:
    data_url = f"data:image/png;base64,{base64.b64encode(b'fanora-image').decode('ascii')}"
    uploads: list[bytes] = []

    async def fake_upload_bytes(*, content: bytes, mime_type: str, filename: str) -> CosUpload:
        uploads.append(content)
        return CosUpload(url="https://cdn.example.test/v/image.png", raw={})

    monkeypatch.setattr(cos_adapter, "upload_bytes", fake_upload_bytes)
    snapshot = CommunitySnapshot(
        users=[],
        user_profiles=[{"avatar_url": data_url}],
        user_roles=[],
        user_sessions=[],
        wallets=[],
        auth_identities=[],
        community={"logo_url": data_url},
        posts=[{"cover_url": data_url, "body": f"![image]({data_url})", "image_urls": [data_url]}],
        tasks=[{"validation_rule": {"presentation": {"image_url": data_url}}}],
    )

    hoster = SnapshotImageHoster()
    hosted = await hoster.host_snapshot(snapshot)

    expected = "https://cdn.example.test/v/image.png"
    assert hosted.user_profiles[0]["avatar_url"] == expected
    assert hosted.community["logo_url"] == expected
    assert hosted.posts[0]["cover_url"] == expected
    assert hosted.posts[0]["image_urls"] == [expected]
    assert hosted.posts[0]["body"] == f"![image]({expected})"
    assert hosted.tasks[0]["validation_rule"]["presentation"]["image_url"] == expected
    assert uploads == [b"fanora-image"]
    assert hoster.upload_count == 1
