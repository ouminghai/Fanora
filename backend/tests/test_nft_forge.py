from contextlib import asynccontextmanager

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, select

import app.models.database  # noqa: F401
from app.core.config import settings
from app.models.community import FanTokenLedger
from app.models.nft import FragmentLedger, NftAiAnalysis, NftForgeSession, UserFragmentBalance
from app.models.user import User, UserProfile
from app.schemas.nft_forge import NftForgeAnalyzeRequest, NftFragmentRedeemRequest
from app.services.nft_forge import ForgeAnalysisDraft, _forge_analysis_messages, nft_forge_service


def test_forge_analysis_accepts_nested_llm_scores() -> None:
    result = ForgeAnalysisDraft.model_validate(
        {
            "scores": {
                "originality": 81,
                "visual_quality": 76,
                "fan_emotion": 92,
                "scarcity": 64,
                "community_potential": 73,
            },
            "suggestions": ["强化核心象征物"],
        }
    )

    assert result.originality == 81
    assert result.visual_quality == 76
    assert result.fan_emotion == 92
    assert result.scarcity == 64
    assert result.community_potential == 73


def test_forge_analysis_sends_the_actual_nft_image_to_the_llm() -> None:
    payload = NftForgeAnalyzeRequest(
        title="花海回声",
        story_summary="双重人物侧影围绕中央花海形成对称构图，灰蓝云雾营造梦境与纪念感。",
        description="一张以花海和双重侧影表达记忆与梦想的演唱会纪念海报。",
        image_prompt="surreal concert keepsake with mirrored portraits and vivid flowers",
        image_url="https://img.example/upload.webp",
        supply=50,
        price_fan_tokens=20,
    )

    messages = _forge_analysis_messages(payload)

    assert messages[1].content[1] == {
        "type": "image_url",
        "image_url": {"url": "https://img.example/upload.webp"},
    }


@asynccontextmanager
async def forge_test_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


async def _seed_forge(session: AsyncSession) -> tuple[User, UserProfile, NftForgeSession, NftAiAnalysis]:
    user = User(display_name="Forge Tester")
    session.add(user)
    await session.flush()
    profile = UserProfile(user_id=user.id, fan_token_balance=100, fan_token_lifetime_earned=100)
    forge = NftForgeSession(
        user_id=user.id,
        title="散场回声",
        story_summary="那天散场以后，我把最后一段合唱和落下的彩带记了很久。",
        image_prompt="square premium fan collectible, falling confetti, warm backlight, layered paper and foil",
        supply=50,
        price_fan_tokens=20,
        forge_mode="FOCUSED",
        generated_versions=[
            {
                "id": "agent-draft-1",
                "url": "https://example.com/agent-draft.jpg",
                "label": "AGENT DRAFT",
                "name": "散场回声",
                "description": "把散场合唱与彩带留在一枚收藏品里。",
                "image_prompt": "square premium fan collectible",
                "attributes": [],
            }
        ],
        selected_version_id="agent-draft-1",
    )
    session.add_all([profile, forge])
    await session.flush()
    analysis = NftAiAnalysis(
        forge_session_id=forge.id,
        rare_score=80,
        rarity_level="Rare",
        originality=80,
        visual_quality=80,
        fan_emotion=80,
        scarcity=80,
        community_potential=80,
        recommend_supply_min=10,
        recommend_supply_max=100,
        recommend_supply_default=50,
        recommend_price_min=10,
        recommend_price_max=40,
        recommend_price_default=20,
        suggestions=["保留彩带作为第一视觉焦点"],
    )
    session.add(analysis)
    await session.commit()
    return user, profile, forge, analysis


async def test_probability_uses_documented_quality_and_mode_formula() -> None:
    async with forge_test_session() as session:
        _, _, forge, analysis = await _seed_forge(session)
        focused = await nft_forge_service.probability(session, forge, analysis)
        assert focused.quality_factor == 71.0
        assert focused.mode_modifier == 0
        assert focused.success_rate <= 95
        assert focused.perfect_rate == 0
        assert focused.possible_results == ["发行成功", "发行失败"]

        forge.forge_mode = "STABLE"
        stable = await nft_forge_service.probability(session, forge, analysis)
        assert stable.success_rate > focused.success_rate
        assert stable.fan_cost == 10

        forge.forge_mode = "LEGENDARY"
        legendary = await nft_forge_service.probability(session, forge, analysis)
        assert legendary.success_rate < focused.success_rate
        assert legendary.perfect_rate == 0
        assert legendary.fan_cost == 40


async def test_probability_drops_by_at_least_twenty_five_percent_when_market_exposure_grows_tenfold() -> None:
    async with forge_test_session() as session:
        _, _, forge, analysis = await _seed_forge(session)
        baseline = await nft_forge_service.probability(session, forge, analysis)

        forge.supply *= 10
        expanded = await nft_forge_service.probability(session, forge, analysis)

        assert expanded.success_rate <= round(baseline.success_rate * 0.75, 2)
        assert expanded.success_rate >= settings.nft_forge_success_rate_min


async def test_normal_failed_forge_spends_fan_and_awards_one_fragment(monkeypatch) -> None:
    async with forge_test_session() as session:
        user, profile, forge, _ = await _seed_forge(session)
        monkeypatch.setattr(nft_forge_service, "_roll", lambda _seed, _namespace: 99.0)

        result = await nft_forge_service.start(
            session,
            user.id,
            forge.id,
            "forge:test:failed:1",
            use_fragment_credit=False,
        )

        await session.refresh(profile)
        assert result.status == "FAILED"
        assert result.fragment_balance == 1
        assert profile.fan_token_balance == 80
        assert result.generated_versions[0]["url"] == "https://example.com/agent-draft.jpg"
        assert len(list((await session.execute(select(FragmentLedger))).scalars())) == 1
        spend = (await session.execute(select(FanTokenLedger))).scalar_one()
        assert spend.delta == -20
        assert spend.source_type == "nft-forge-spend"


async def test_fragment_redemption_is_idempotent() -> None:
    async with forge_test_session() as session:
        user, _, _, _ = await _seed_forge(session)
        balance = UserFragmentBalance(user_id=user.id, balance=10)
        session.add(balance)
        await session.commit()
        payload = NftFragmentRedeemRequest(forge_mode="FOCUSED", idempotency_key="fragment:redeem:test:1")

        first = await nft_forge_service.redeem(session, user.id, payload)
        second = await nft_forge_service.redeem(session, user.id, payload)

        assert first.balance == 0
        assert first.focused_credits == 1
        assert second.balance == 0
        assert second.focused_credits == 1


async def _activate_test_creator(user_id: str) -> None:
    from app.core.database import database_service

    async with database_service.session() as session:
        profile = await session.get(UserProfile, user_id)
        assert profile is not None
        profile.is_official_member = True
        profile.fan_token_balance = 100
        profile.fan_token_lifetime_earned = 100
        await session.commit()


def test_forge_api_analyze_strategy_and_failed_attempt(client, monkeypatch) -> None:
    account = Account.create()
    challenge = client.post("/api/v1/auth/challenge", json={"wallet_address": account.address}).json()
    signature = Account.sign_message(
        encode_defunct(text=challenge["message"]),
        private_key=account.key,
    ).signature.hex()
    login = client.post(
        "/api/v1/auth/wallet",
        json={
            "challenge_id": challenge["challenge_id"],
            "wallet_address": account.address,
            "signature": signature,
        },
    ).json()
    assert client.portal is not None
    client.portal.call(_activate_test_creator, login["user"]["id"])
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    analyzed = client.post(
        "/api/v1/nft/forge/analyze",
        headers=headers,
        json={
            "title": "散场回声",
            "story_summary": "那天散场以后，我把最后一段合唱和落下的彩带记了很久。",
            "description": "把散场后的合唱、彩带与归属感收进一枚可收藏的数字纪念品。",
            "image_prompt": "square premium fan collectible, falling confetti, warm backlight, layered paper and foil",
            "image_url": "https://example.com/agent-draft.jpg",
            "supply": 50,
            "price_fan_tokens": 20,
            "forge_mode": "FOCUSED",
            "copyright_confirmed": True,
        },
    )
    assert analyzed.status_code == 201
    forge = analyzed.json()
    assert forge["analysis"]["rare_score"] >= 0
    assert forge["status"] == "ANALYZED"
    assert forge["generated_versions"][0]["url"] == "https://example.com/agent-draft.jpg"
    assert forge["selected_version_id"] == forge["generated_versions"][0]["id"]
    assert forge["supply"] == forge["analysis"]["recommend_supply"]["default"]
    assert forge["price_fan_tokens"] == forge["analysis"]["recommend_price"]["default"]

    current = client.get(
        f"/api/v1/nft/forge/{forge['id']}",
        headers=headers,
    )
    assert current.status_code == 200
    assert current.json()["id"] == forge["id"]

    strategy = client.patch(
        f"/api/v1/nft/forge/{forge['id']}/strategy",
        headers=headers,
        json={"supply": 80, "price_fan_tokens": 25, "forge_mode": "STABLE"},
    )
    assert strategy.status_code == 200
    assert strategy.json()["probability"]["fan_cost"] == 10

    monkeypatch.setattr(nft_forge_service, "_roll", lambda _seed, _namespace: 99.0)
    failed = client.post(
        f"/api/v1/nft/forge/{forge['id']}/start",
        headers=headers,
        json={"idempotency_key": f"forge:api:{forge['id']}:1", "use_fragment_credit": False},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert failed.json()["fragment_balance"] == 1
    assert failed.json()["fan_token_balance"] == 90
