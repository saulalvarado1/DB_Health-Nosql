from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_session
from app.main import app


class AvailableSession:
    def execute(self, statement: object) -> None:
        assert str(statement) == "SELECT 1"


class UnavailableSession:
    def execute(self, statement: object) -> None:
        raise SQLAlchemyError("PostgreSQL no responde")


def test_liveness_does_not_require_postgresql() -> None:
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "db-health-monitor"}


def test_readiness_reports_ready_when_postgresql_responds() -> None:
    app.dependency_overrides[get_session] = lambda: AvailableSession()
    try:
        response = TestClient(app).get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "db-health-monitor"}


def test_readiness_reports_unavailable_when_postgresql_fails() -> None:
    app.dependency_overrides[get_session] = lambda: UnavailableSession()
    try:
        response = TestClient(app).get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "El almacenamiento interno no está disponible."}
