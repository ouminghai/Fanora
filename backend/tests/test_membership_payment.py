from datetime import timedelta

from eth_account import Account

from app.adapters.monad import monad_contract_adapter
from app.core.config import settings
from app.core.database import database_service
from app.models.base import utc_now
from app.models.user import User, UserProfile, UserSession, Wallet
from app.services.auth import hash_session_token
from app.services.membership_payment import ConfirmedChainPayment, official_membership_payment_service


async def test_verified_one_mon_payment_activates_official_membership(client, monkeypatch):
    account = Account.create()
    treasury = Account.create().address
    raw_token = "membership-test-session-token"
    transaction_hash = "0x" + "ab" * 32

    async with database_service.session() as session:
        user = User(display_name="Pending Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id),
                Wallet(
                    user_id=user.id,
                    address=account.address,
                    wallet_type="embedded",
                    provider="web3auth",
                    is_primary=True,
                ),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()
        user_id = user.id

    gateway = Account.create().address
    monkeypatch.setattr(settings, "membership_payment_contract_address", gateway)

    async def current_fee() -> int:
        return settings.membership_fee_wei

    monkeypatch.setattr(monad_contract_adapter, "membership_fee", current_fee)

    async def confirmed_payment(_: str) -> ConfirmedChainPayment:
        return ConfirmedChainPayment(
            transaction_hash=transaction_hash,
            from_address=account.address,
            to_address=gateway,
            treasury_address=treasury,
            payment_id=official_membership_payment_service.payment_id_for_user(user_id),
            value_wei=settings.membership_fee_wei,
            chain_id=settings.monad_chain_id,
            block_number=123,
            confirmations=1,
        )

    monkeypatch.setattr(official_membership_payment_service, "_load_chain_payment", confirmed_payment)
    headers = {"Authorization": f"Bearer {raw_token}"}

    pending_response = client.get("/api/v1/membership/me", headers=headers)
    assert pending_response.status_code == 200
    assert pending_response.json()["status"] == "pending_payment"
    assert pending_response.json()["is_official_member"] is False
    assert pending_response.json()["fee_mon"] == "1"

    verify_response = client.post(
        "/api/v1/membership/verify",
        headers=headers,
        json={"transaction_hash": transaction_hash},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "active"
    assert verify_response.json()["transaction_hash"] == transaction_hash

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["is_official_member"] is True
    assert me_response.json()["level"] == "新生儿"


async def test_membership_status_does_not_offer_payment_without_gateway(client):
    account = Account.create()
    raw_token = "membership-unconfigured-session-token"

    async with database_service.session() as session:
        user = User(display_name="Unconfigured Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id),
                Wallet(user_id=user.id, address=account.address, wallet_type="external", is_primary=True),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()

    response = client.get(
        "/api/v1/membership/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 200
    assert response.json()["payment_contract_address"] is None
