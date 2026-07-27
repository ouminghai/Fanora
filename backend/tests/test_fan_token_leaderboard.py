from app.core.database import database_service
from app.models.user import User, UserProfile


async def seed_leaderboard_users() -> None:
    async with database_service.session() as session:
        for index in range(12):
            user = User(id=f"leaderboard-user-{index}", display_name=f"Fan {index}")
            profile = UserProfile(
                user_id=user.id,
                username=f"fan_{index}",
                level="重度神经",
                fan_token_balance=1200 - index * 10,
                fan_token_lifetime_earned=1300 - index * 10,
                profile_visibility="public",
            )
            session.add(user)
            session.add(profile)
        hidden = User(id="leaderboard-hidden-user", display_name="Hidden Fan")
        hidden_profile = UserProfile(
            user_id=hidden.id,
            username="hidden_fan",
            fan_token_balance=9999,
            fan_token_lifetime_earned=9999,
            profile_visibility="private",
        )
        session.add(hidden)
        session.add(hidden_profile)
        await session.commit()


def test_fan_token_leaderboard_returns_public_top_10(client) -> None:
    assert client.portal is not None
    client.portal.call(seed_leaderboard_users)

    response = client.get("/api/v1/fan-tokens/leaderboard")

    assert response.status_code == 200
    leaders = response.json()
    assert len(leaders) == 10
    assert [item["rank"] for item in leaders] == list(range(1, 11))
    assert leaders[0]["user_id"] == "leaderboard-user-0"
    assert leaders[0]["fan_token_balance"] == 1200
    assert all(item["user_id"] != "leaderboard-hidden-user" for item in leaders)
