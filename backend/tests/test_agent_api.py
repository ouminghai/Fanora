from fastapi.testclient import TestClient


def test_analyze_fan_profile_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/fan-profile/analyze",
        json={
            "wallet_address": "0x0000000000000000000000000000000000000003",
            "fan_token_balance": 600,
            "completed_tasks": 8,
            "active_days": 15,
            "referrals": 2,
            "onchain_actions": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_source"] == "rules"
    assert payload["badge_eligible"] is True
    assert payload["badge_draft"]["name"]
    assert payload["risk_level"] == "low"
    assert payload["rule_version"] == "fan-profile-v2"
