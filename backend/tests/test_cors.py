from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_application


def test_cors_is_disabled_when_no_origin_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", [])
    app = create_application()

    response = TestClient(app).get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_configured_frontend_origin_receives_cors_headers(monkeypatch) -> None:
    frontend_origin = "http://localhost:5173"
    monkeypatch.setattr(settings, "cors_allowed_origins", [frontend_origin])
    app = create_application()

    response = TestClient(app).options(
        "/api/v1/health",
        headers={
            "Origin": frontend_origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == frontend_origin
    assert response.headers["access-control-allow-credentials"] == "true"
