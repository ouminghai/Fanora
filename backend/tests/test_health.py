from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "fanora-api"
    assert payload["components"]["database"] == "healthy"
    assert payload["components"]["fan_profile_agent"] == "ready"
