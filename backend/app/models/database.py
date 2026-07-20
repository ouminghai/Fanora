"""Import all SQLModel tables so metadata is complete."""

from app.models.fan_profile import FanProfileRun
from app.models.membership import FanTokenConfig, FanTokenRule, MembershipLevel
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

__all__ = [
    "AuthIdentity",
    "Community",
    "CommunityMember",
    "FanProfileRun",
    "FanTokenConfig",
    "FanTokenRule",
    "LoginChallenge",
    "MembershipLevel",
    "User",
    "UserProfile",
    "UserRole",
    "UserSession",
    "Wallet",
]
