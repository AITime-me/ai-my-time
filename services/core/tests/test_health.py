from fastapi.testclient import TestClient

from app.main import create_app


def test_healthcheck_returns_non_sensitive_liveness_payload() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-my-time-core",
        "environment": "development",
        "version": "0.1.0",
    }
