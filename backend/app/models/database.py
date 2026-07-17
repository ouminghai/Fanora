"""Import all SQLModel tables so metadata is complete."""

from app.models.fan_profile import FanProfileRun
from app.models.user import AuthIdentity, User, Wallet

__all__ = ["AuthIdentity", "FanProfileRun", "User", "Wallet"]
