"""Prueba de aislamiento entre usuarios contra PostgreSQL real de pruebas.

No se ejecuta sin TEST_DATABASE_URL y rechaza cualquier base que no se llame
db_health_monitor_test. Las URI usadas son ficticias y nunca se recolectan.
"""

import os
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_session
from app.infrastructure.persistence.models import Alert, MetricSample, MonitoredDatabase, User
from app.main import app

TEST_DATABASE_NAME = "db_health_monitor_test"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="Define TEST_DATABASE_URL para ejecutar pruebas de integración.",
    ),
]


@pytest.fixture(scope="module")
def integration_engine() -> Generator[Engine, None, None]:
    assert TEST_DATABASE_URL is not None
    database_name = make_url(TEST_DATABASE_URL).database
    if database_name != TEST_DATABASE_NAME:
        pytest.fail("Por seguridad, TEST_DATABASE_URL debe apuntar a db_health_monitor_test.")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(select(User.id).limit(1))
    except SQLAlchemyError:
        engine.dispose()
        pytest.fail(
            "No fue posible usar la base de integración. Ejecuta alembic upgrade head "
            "contra db_health_monitor_test."
        )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def integration_session_factory(integration_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=integration_engine, autocommit=False, autoflush=False)


def _delete_integration_users(session_factory: sessionmaker[Session]) -> None:
    session = session_factory()
    try:
        session.execute(delete(User).where(User.email.like("integration-%@example.com")))
        session.commit()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_integration_users(
    integration_session_factory: sessionmaker[Session],
) -> Generator[None, None, None]:
    """Limpia solo usuarios con el prefijo creado por esta prueba."""
    _delete_integration_users(integration_session_factory)
    try:
        yield
    finally:
        _delete_integration_users(integration_session_factory)


@pytest.fixture
def client(
    integration_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = integration_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _authorization_header(client: TestClient, email: str) -> dict[str, str]:
    password = "IntegrationTestPassword2026!"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201, registration.text

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_alert_for_database(session_factory: sessionmaker[Session], database_id: str) -> str:
    session = session_factory()
    try:
        sample = MetricSample(
            monitored_database_id=database_id,
            collected_at=datetime.now(UTC),
            collection_succeeded=False,
            error_message="Muestra creada para verificar aislamiento de alertas.",
        )
        session.add(sample)
        session.flush()
        alert = Alert(
            monitored_database_id=database_id,
            sample_id=sample.id,
            deduplication_key=f"integration-{uuid4()}",
            severity="critical",
            status="open",
            message="Alerta creada para verificar aislamiento entre usuarios.",
        )
        session.add(alert)
        session.commit()
        return str(alert.id)
    finally:
        session.close()


def test_second_user_cannot_access_another_users_data(
    client: TestClient,
    integration_session_factory: sessionmaker[Session],
) -> None:
    suffix = uuid4().hex
    owner_headers = _authorization_header(client, f"integration-owner-{suffix}@example.com")
    other_user_headers = _authorization_header(client, f"integration-other-{suffix}@example.com")
    connection_uri = f"redis://monitor:integration-only-{suffix}@example.test:6379/0"

    created = client.post(
        "/api/v1/databases",
        headers=owner_headers,
        json={
            "name": f"integration-redis-{suffix}",
            "engine": "redis",
            "connection_uri": connection_uri,
            "interval_seconds": 30,
        },
    )
    assert created.status_code == 201, created.text
    database_id = created.json()["id"]
    alert_id = _create_alert_for_database(integration_session_factory, database_id)

    assert client.get("/api/v1/databases", headers=other_user_headers).json() == []

    protected_requests = [
        client.get(f"/api/v1/databases/{database_id}", headers=other_user_headers),
        client.patch(
            f"/api/v1/databases/{database_id}",
            headers=other_user_headers,
            json={"name": "intrusion-attempt"},
        ),
        client.delete(f"/api/v1/databases/{database_id}", headers=other_user_headers),
        client.get(f"/api/v1/databases/{database_id}/history", headers=other_user_headers),
        client.post(f"/api/v1/databases/{database_id}/collect", headers=other_user_headers),
        client.get(f"/api/v1/databases/{database_id}/thresholds", headers=other_user_headers),
        client.put(
            f"/api/v1/databases/{database_id}/thresholds/memory_usage_percent",
            headers=other_user_headers,
            json={"warning_value": 75, "critical_value": 85},
        ),
        client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=other_user_headers),
    ]
    assert all(response.status_code == 404 for response in protected_requests)
    assert client.get("/api/v1/alerts", headers=other_user_headers).json() == []

    owner_response = client.get(f"/api/v1/databases/{database_id}", headers=owner_headers)
    assert owner_response.status_code == 200
    assert owner_response.json()["name"] == f"integration-redis-{suffix}"

    session = integration_session_factory()
    try:
        stored_database = session.scalar(
            select(MonitoredDatabase).where(MonitoredDatabase.id == database_id)
        )
        assert stored_database is not None
        assert stored_database.connection_uri_encrypted != connection_uri
        assert connection_uri not in stored_database.connection_uri_encrypted
    finally:
        session.close()

    deleted = client.delete(f"/api/v1/databases/{database_id}", headers=owner_headers)
    assert deleted.status_code == 204, deleted.text

    session = integration_session_factory()
    try:
        assert session.get(MonitoredDatabase, UUID(database_id)) is None
        assert session.get(Alert, UUID(alert_id)) is None
    finally:
        session.close()
