"""Development/test helpers for removing a user without violating foreign keys."""

from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

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


class UserCleanupError(RuntimeError):
    """Base error for test-user cleanup."""


class UserNotFoundError(UserCleanupError):
    """Raised when the requested user does not exist."""


class UserOwnsCommunitiesError(UserCleanupError):
    """Raised when deleting a user would also require deleting owned communities."""

    def __init__(self, community_ids: list[str]) -> None:
        self.community_ids = community_ids
        super().__init__(
            "User owns communities. Pass delete_owned_communities=True only when those test communities may be deleted: "
            + ", ".join(community_ids)
        )


@dataclass(slots=True)
class UserDeletionResult:
    user_id: str
    deleted_owned_community_ids: list[str] = field(default_factory=list)
    deleted_rows: dict[str, int] = field(default_factory=dict)


def _row_count(result) -> int:
    return max(int(result.rowcount or 0), 0)


async def delete_user_by_id(
    session: AsyncSession,
    user_id: str,
    *,
    delete_owned_communities: bool = False,
) -> UserDeletionResult:
    """Delete a test user and current-schema dependants in foreign-key-safe order.

    Owned communities are protected by default because deleting one also removes
    memberships belonging to other users. The operation is committed atomically;
    any failure rolls the transaction back.
    """

    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User not found: {user_id}")

    owned_community_ids = list(
        (
            await session.execute(
                select(Community.id).where(Community.owner_user_id == user_id).order_by(Community.id)
            )
        )
        .scalars()
        .all()
    )
    if owned_community_ids and not delete_owned_communities:
        raise UserOwnsCommunitiesError(owned_community_ids)

    wallet_addresses = list(
        (await session.execute(select(Wallet.address).where(Wallet.user_id == user_id))).scalars().all()
    )
    deleted_rows: dict[str, int] = {}

    try:
        if owned_community_ids:
            result = await session.execute(
                delete(CommunityMember).where(col(CommunityMember.community_id).in_(owned_community_ids))
            )
            deleted_rows["owned_community_members"] = _row_count(result)
            result = await session.execute(delete(Community).where(col(Community.id).in_(owned_community_ids)))
            deleted_rows["owned_communities"] = _row_count(result)

        result = await session.execute(delete(CommunityMember).where(col(CommunityMember.user_id) == user_id))
        deleted_rows["community_memberships"] = _row_count(result)

        if wallet_addresses:
            result = await session.execute(
                delete(LoginChallenge).where(col(LoginChallenge.wallet_address).in_(wallet_addresses))
            )
            deleted_rows["login_challenges"] = _row_count(result)

        for name, statement in (
            ("fan_profile_runs", delete(FanProfileRun).where(col(FanProfileRun.user_id) == user_id)),
            ("user_sessions", delete(UserSession).where(col(UserSession.user_id) == user_id)),
            ("user_roles", delete(UserRole).where(col(UserRole.user_id) == user_id)),
            ("user_profiles", delete(UserProfile).where(col(UserProfile.user_id) == user_id)),
            ("wallets", delete(Wallet).where(col(Wallet.user_id) == user_id)),
            ("auth_identities", delete(AuthIdentity).where(col(AuthIdentity.user_id) == user_id)),
        ):
            result = await session.execute(statement)
            deleted_rows[name] = _row_count(result)

        await session.delete(user)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    deleted_rows["users"] = 1
    return UserDeletionResult(
        user_id=user_id,
        deleted_owned_community_ids=owned_community_ids,
        deleted_rows=deleted_rows,
    )
