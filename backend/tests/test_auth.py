import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from app.core.config import settings
from app.services import auth as auth_service_module
from app.services.auth import web3auth_service


def test_web3auth_register_login_profile_and_logout(client, monkeypatch):
    account = Account.create()

    async def verified_token(_: str, __: str, ___: str | None = None):
        return {
            "sub": "web3auth-test-user",
            "name": "Fanora Tester",
            "email": "fan@example.com",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr(web3auth_service, "verify_identity_token", verified_token)

    challenge_response = client.post("/api/v1/auth/challenge", json={"wallet_address": account.address})
    assert challenge_response.status_code == 200
    challenge = challenge_response.json()
    signature = Account.sign_message(
        encode_defunct(text=challenge["message"]), private_key=account.key
    ).signature.hex()

    login_payload = {
        "challenge_id": challenge["challenge_id"],
        "wallet_address": account.address,
        "signature": signature,
        "id_token": "test-web3auth-identity-token",
        "wallet_type": "embedded",
    }
    login_response = client.post("/api/v1/auth/web3auth", json=login_payload)
    assert login_response.status_code == 200
    login = login_response.json()
    assert login["is_new_user"] is True
    assert login["user"]["primary_wallet"]["address"] == Web3.to_checksum_address(account.address)
    assert login["user"]["roles"] == ["fan"]
    assert login["user"]["email"] == "fan@example.com"
    assert login["user"]["fan_token_balance"] == 0
    assert login["user"]["is_official_member"] is False
    assert login["user"]["level"] == "待入会"
    assert "points" not in login["user"]

    replay_response = client.post("/api/v1/auth/web3auth", json=login_payload)
    assert replay_response.status_code == 401

    headers = {"Authorization": f"Bearer {login['access_token']}"}
    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["display_name"] == "Fanora Tester"

    update_response = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "display_name": "Monad Fan",
            "username": "monad_fan",
            "avatar_url": "https://example.com/new-avatar.webp",
            "bio": "Building a verifiable fandom identity.",
            "locale": "zh-CN",
            "profile_visibility": "public",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["username"] == "monad_fan"
    assert update_response.json()["onboarding_completed"] is True

    public_response = client.get(f"/api/v1/users/{login['user']['id']}")
    assert public_response.status_code == 200
    assert public_response.json()["email"] is None

    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 204
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401


def test_wallet_signature_must_match_challenge(client, monkeypatch):
    account = Account.create()
    attacker = Account.create()

    async def verified_token(_: str, __: str, ___: str | None = None):
        return {"sub": "signature-mismatch-user"}

    monkeypatch.setattr(web3auth_service, "verify_identity_token", verified_token)
    challenge = client.post("/api/v1/auth/challenge", json={"wallet_address": account.address}).json()
    bad_signature = Account.sign_message(
        encode_defunct(text=challenge["message"]), private_key=attacker.key
    ).signature.hex()
    response = client.post(
        "/api/v1/auth/web3auth",
        json={
            "challenge_id": challenge["challenge_id"],
            "wallet_address": account.address,
            "signature": bad_signature,
            "id_token": "test-web3auth-identity-token",
            "wallet_type": "external",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_external_web3auth_token_uses_authjs_jwks(monkeypatch):
    account = Account.create()
    claims = {
        # Web3Auth's external-wallet flow sends the connector name as the issuer
        # and the current web origin's hostname as the audience.
        "iss": "metamask",
        "aud": "localhost",
        "wallets": [{"address": account.address}],
        "exp": 4_102_444_800,
        "iat": 1_770_000_000,
    }
    calls: list[str] = []

    class SigningKey:
        key = "fake-public-key"

    class JwksClient:
        def __init__(self, name: str) -> None:
            self.name = name

        def get_signing_key_from_jwt(self, _: str) -> SigningKey:
            calls.append(self.name)
            return SigningKey()

    def decode_token(*args, **kwargs):
        options = kwargs.get("options") or {}
        if options.get("verify_signature") is False:
            return claims
        assert args[1] == SigningKey.key
        return claims

    monkeypatch.setattr(web3auth_service, "jwks_client", JwksClient("embedded"))
    monkeypatch.setattr(web3auth_service, "external_jwks_client", JwksClient("external"))
    monkeypatch.setattr(auth_service_module.jwt, "decode", decode_token)

    verified_claims = await web3auth_service.verify_identity_token(
        "header.payload.signature", Web3.to_checksum_address(account.address)
    )

    assert verified_claims is claims
    assert calls == ["external"]


@pytest.mark.asyncio
async def test_embedded_web3auth_token_accepts_legacy_issuer_and_checks_public_key(monkeypatch):
    claims = {
        "iss": settings.web3auth_legacy_issuer,
        "aud": settings.web3auth_client_id,
        "sub": "embedded-user",
        "wallets": [{"public_key": "02" + "a" * 64}],
        "exp": 4_102_444_800,
        "iat": 1_770_000_000,
    }
    calls: list[str] = []

    class SigningKey:
        key = "fake-public-key"

    class JwksClient:
        def __init__(self, name: str) -> None:
            self.name = name

        def get_signing_key_from_jwt(self, _: str) -> SigningKey:
            calls.append(self.name)
            return SigningKey()

    def decode_token(*args, **kwargs):
        options = kwargs.get("options") or {}
        if options.get("verify_signature") is False:
            return claims
        assert args[1] == SigningKey.key
        return claims

    monkeypatch.setattr(web3auth_service, "jwks_client", JwksClient("embedded"))
    monkeypatch.setattr(web3auth_service, "legacy_jwks_client", JwksClient("legacy"))
    monkeypatch.setattr(web3auth_service, "external_jwks_client", JwksClient("external"))
    monkeypatch.setattr(auth_service_module.jwt, "decode", decode_token)

    verified_claims = await web3auth_service.verify_identity_token(
        "header.payload.signature", "0x0000000000000000000000000000000000000001", "02" + "a" * 64
    )

    assert verified_claims is claims
    assert calls == ["legacy"]
