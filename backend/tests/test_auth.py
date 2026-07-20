from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from app.services.auth import web3auth_service


def test_web3auth_register_login_profile_and_logout(client, monkeypatch):
    account = Account.create()

    async def verified_token(_: str, __: str):
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

    async def verified_token(_: str, __: str):
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
