"""Import all SQLModel tables so metadata is complete."""

from app.models.community import (
    CommunityPost,
    CommunityPostReaction,
    CommunityReply,
    CommunityReplyLike,
    DailyCheckIn,
    FanTask,
    FanTokenLedger,
    TaskAuditLog,
    TaskParticipation,
)
from app.models.fan_profile import FanProfileRun
from app.models.membership import FanTokenConfig, FanTokenRule, MembershipLevel
from app.models.user import (
    AuthIdentity,
    AuthSecurityEvent,
    Community,
    CommunityMember,
    LoginChallenge,
    OfficialMembershipPayment,
    User,
    UserProfile,
    UserRole,
    UserSession,
    Wallet,
)

__all__ = [
    "AuthIdentity",
    "AuthSecurityEvent",
    "Community",
    "CommunityMember",
    "CommunityPost",
    "CommunityPostReaction",
    "CommunityReply",
    "CommunityReplyLike",
    "DailyCheckIn",
    "FanProfileRun",
    "FanTokenConfig",
    "FanTokenLedger",
    "FanTokenRule",
    "FanTask",
    "LoginChallenge",
    "MembershipLevel",
    "OfficialMembershipPayment",
    "User",
    "UserProfile",
    "UserRole",
    "UserSession",
    "Wallet",
    "TaskAuditLog",
    "TaskParticipation",
]
