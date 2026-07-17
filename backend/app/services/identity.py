"""Identity interface shared by embedded-wallet and external-wallet adapters."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class AuthenticatedIdentity:
    user_id: str
    primary_wallet: str
    wallet_type: Literal["embedded", "external"]
    provider: str


class IdentityProvider(Protocol):
    async def authenticate(self, credential: str) -> AuthenticatedIdentity: ...
