from app.core.database import database_service
from app.models.membership import MembershipLevel


async def test_membership_levels_are_returned_from_database_in_rank_order(client):
    async with database_service.session() as session:
        session.add_all(
            [
                MembershipLevel(
                    code="api-level-two",
                    name="接口等级二",
                    description="第二个真实数据库等级",
                    rank=902,
                    min_token_balance=500,
                    max_token_balance=999,
                    badge_image_url="/img/badges/moderate.png",
                ),
                MembershipLevel(
                    code="api-level-one",
                    name="接口等级一",
                    description="第一个真实数据库等级",
                    rank=901,
                    min_token_balance=0,
                    max_token_balance=499,
                    badge_image_url="/img/badges/new.png",
                ),
                MembershipLevel(
                    code="api-level-hidden",
                    name="停用等级",
                    description="停用后不应返回",
                    rank=903,
                    min_token_balance=1000,
                    max_token_balance=1499,
                    badge_image_url="/img/badges/severe.png",
                    is_active=False,
                ),
            ]
        )
        await session.commit()

    response = client.get("/api/v1/membership-levels")

    assert response.status_code == 200
    levels = [level for level in response.json() if level["code"].startswith("api-level-")]
    assert [level["code"] for level in levels] == ["api-level-one", "api-level-two"]
    assert levels[0]["badge_image_url"] == "/img/badges/new.png"
    assert levels[0]["min_token_balance"] == 0
    assert levels[1]["max_token_balance"] == 999

