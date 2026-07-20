import pytest
from eth_account import Account
from sqlmodel import select

from app.core.database import database_service
from app.models.fan_profile import FanProfileRun
from app.models.user import (
    AuthIdentity,
    Community,
    CommunityMember,
    LoginChallenge,
    User,
    UserProfile,
    UserRole,
    UserSession,
    Wallet,
)
from app.services.user_cleanup import UserOwnsCommunitiesError, delete_user_by_id


async def test_delete_user_cleans_current_foreign_key_dependants(client):
    wallet_address = Account.create().address
    async with database_service.session() as session:
        user = User(display_name="Delete Me")
        other_user = User(display_name="Keep Me")
        session.add_all([user, other_user])
        await session.flush()
        community = Community(
            owner_user_id=other_user.id,
            slug=f"keep-{user.id[:8]}",
            name="Community to keep",
            description="This community must survive user cleanup.",
            logo_url="https://example.com/community.png",
        )
        session.add(community)
        await session.flush()
        session.add_all(
            [
                AuthIdentity(user_id=user.id, provider="web3auth", subject=f"delete-{user.id}"),
                Wallet(user_id=user.id, address=wallet_address, wallet_type="embedded", is_primary=True),
                UserProfile(user_id=user.id),
                UserRole(user_id=user.id, role="fan"),
                UserSession(user_id=user.id, token_hash=user.id.replace("-", "").ljust(64, "0"), expires_at=user.created_at),
                LoginChallenge(wallet_address=wallet_address, message="test", expires_at=user.created_at),
                CommunityMember(community_id=community.id, user_id=user.id),
                FanProfileRun(
                    user_id=user.id,
                    wallet_address=wallet_address,
                    community_id=community.id,
                    input_payload={},
                    output_payload={},
                    analysis_source="rules",
                ),
            ]
        )
        await session.commit()
        user_id = user.id
        community_id = community.id

        result = await delete_user_by_id(session, user_id)
        assert result.deleted_rows["users"] == 1

    async with database_service.session() as session:
        assert await session.get(User, user_id) is None
        assert await session.get(Community, community_id) is not None
        assert (
            await session.execute(select(CommunityMember).where(CommunityMember.user_id == user_id))
        ).scalar_one_or_none() is None


async def test_delete_user_requires_explicit_owned_community_cascade(client):
    async with database_service.session() as session:
        owner = User(display_name="Community Owner")
        member = User(display_name="Community Member")
        session.add_all([owner, member])
        await session.flush()
        community = Community(
            owner_user_id=owner.id,
            slug=f"delete-{owner.id[:8]}",
            name="Disposable Community",
            description="This community belongs to a disposable test user.",
            logo_url="https://example.com/community.png",
        )
        session.add(community)
        await session.flush()
        session.add_all(
            [
                CommunityMember(community_id=community.id, user_id=owner.id, role="owner"),
                CommunityMember(community_id=community.id, user_id=member.id),
            ]
        )
        await session.commit()
        owner_id = owner.id
        member_id = member.id
        community_id = community.id

        with pytest.raises(UserOwnsCommunitiesError):
            await delete_user_by_id(session, owner_id)

        result = await delete_user_by_id(session, owner_id, delete_owned_communities=True)
        assert result.deleted_owned_community_ids == [community_id]

    async with database_service.session() as session:
        assert await session.get(User, owner_id) is None
        assert await session.get(User, member_id) is not None
        assert await session.get(Community, community_id) is None
