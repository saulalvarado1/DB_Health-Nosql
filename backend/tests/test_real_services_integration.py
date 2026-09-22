"""Valida el ciclo HTTP completo contra Redis y MongoDB reales de prueba.

La prueba solo se habilita cuando las tres URI aisladas están definidas. Nunca
usa la base principal ni imprime credenciales de los servicios monitorizados.
"""

import json
import os
from collections.abc import Generator
from uuid import uuid4

import pytest
import redis
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from redis.exceptions import RedisError
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_session
from app.infrastructure.persistence.models import MonitoredDatabase, User
from app.main import app

TEST_DATABASE_NAME = "db_health_monitor_test"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_REDIS_URI = os.getenv("TEST_REDIS_URI")
TEST_MONGODB_URI = os.getenv("TEST_MONGODB_URI")
REAL_SERVICES_CONFIGURED = all((TEST_DATABASE_URL, TEST_REDIS_URI, TEST_MONGODB_URI))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_services,
    pytest.mark.skipif(
        not REAL_SERVICES_CONFIGURED,
        reason=(
            "Define TEST_DATABASE_URL, TEST_REDIS_URI y TEST_MONGODB_URI para "
            "probar servicios reales."
        ),
    ),
]


@pytest.fixture(scope="module")
def integration_engine() -> Generator[Engine, None, None]:
    assert TEST_DATABASE_URL is not None
    if make_url(TEST_DATABASE_URL).database != TEST_DATABASE_NAME:
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


def _delete_real_service_users(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.execute(delete(User).where(User.email.like("integration-real-%@example.com")))
        session.commit()


@pytest.fixture(autouse=True)
def clean_real_service_users(
    integration_session_factory: sessionmaker[Session],
) -> Generator[None, None, None]:
    _delete_real_service_users(integration_session_factory)
    try:
        yield
    finally:
        _delete_real_service_users(integration_session_factory)


@pytest.fixture
def client(
    integration_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with integration_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _authorization_header(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"integration-real-{suffix}@example.com"
    password = f"Integration-{uuid4().hex}-A1!"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201, registration.text

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_database(
    client: TestClient,
    headers: dict[str, str],
    *,
    engine: str,
    connection_uri: str,
) -> str:
    response = client.post(
        "/api/v1/databases",
        headers=headers,
        json={
            "name": f"integration-real-{engine}-{uuid4().hex}",
            "engine": engine,
            "connection_uri": connection_uri,
            "interval_seconds": 30,
        },
    )
    assert response.status_code == 201, response.text
    assert connection_uri not in json.dumps(response.json())
    return response.json()["id"]


def _collect(client: TestClient, headers: dict[str, str], database_id: str) -> dict[str, object]:
    response = client.post(f"/api/v1/databases/{database_id}/collect", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["collection_succeeded"] is True
    return response.json()


def _assert_redis_user_is_read_only() -> None:
    assert TEST_REDIS_URI is not None
    redis_client = redis.Redis.from_url(TEST_REDIS_URI)
    try:
        assert redis_client.ping() is True
        with pytest.raises(RedisError):
            redis_client.set("db-health-monitor-write-probe", "forbidden")
    finally:
        redis_client.close()


def _assert_mongodb_user_is_read_only() -> None:
    assert TEST_MONGODB_URI is not None
    mongo_client: MongoClient[dict[str, object]] = MongoClient(TEST_MONGODB_URI)
    try:
        assert mongo_client.admin.command("ping")["ok"] == 1.0
        with pytest.raises(OperationFailure) as denied_write:
            mongo_client["db_health_monitor_probe"]["forbidden"].insert_one({"value": 1})
        assert denied_write.value.code == 13
    finally:
        mongo_client.close()


def test_real_redis_mongodb_collection_history_and_alert_lifecycle(
    client: TestClient,
    integration_session_factory: sessionmaker[Session],
) -> None:
    assert TEST_REDIS_URI is not None
    assert TEST_MONGODB_URI is not None
    _assert_redis_user_is_read_only()
    _assert_mongodb_user_is_read_only()
    headers = _authorization_header(client)

    redis_database_id = _create_database(
        client,
        headers,
        engine="redis",
        connection_uri=TEST_REDIS_URI,
    )
    first_redis_sample = _collect(client, headers, redis_database_id)
    assert first_redis_sample["metric_count"] == 6

    redis_history = client.get(f"/api/v1/databases/{redis_database_id}/history", headers=headers)
    assert redis_history.status_code == 200, redis_history.text
    assert {metric["code"] for metric in redis_history.json()[0]["metrics"]} == {
        "availability",
        "connected_clients",
        "memory_usage_percent",
        "operations_per_second",
        "rejected_connections",
        "used_memory_bytes",
    }

    force_alert = client.put(
        f"/api/v1/databases/{redis_database_id}/thresholds/memory_usage_percent",
        headers=headers,
        json={"warning_value": 0.0, "critical_value": 0.001},
    )
    assert force_alert.status_code == 200, force_alert.text
    critical_sample = _collect(client, headers, redis_database_id)
    assert critical_sample["health_status"] == "critical"

    open_alerts = client.get("/api/v1/alerts", headers=headers, params={"status": "open"})
    assert open_alerts.status_code == 200, open_alerts.text
    redis_alert = next(
        alert for alert in open_alerts.json() if alert["monitored_database_id"] == redis_database_id
    )
    assert redis_alert["severity"] == "critical"
    assert redis_alert["threshold_rule_id"] is not None

    acknowledged = client.post(f"/api/v1/alerts/{redis_alert['id']}/acknowledge", headers=headers)
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["status"] == "acknowledged"

    clear_alert = client.put(
        f"/api/v1/databases/{redis_database_id}/thresholds/memory_usage_percent",
        headers=headers,
        json={"warning_value": 99.0, "critical_value": 100.0},
    )
    assert clear_alert.status_code == 200, clear_alert.text
    recovered_sample = _collect(client, headers, redis_database_id)
    assert recovered_sample["health_status"] == "healthy"

    resolved_alerts = client.get("/api/v1/alerts", headers=headers, params={"status": "resolved"})
    assert resolved_alerts.status_code == 200, resolved_alerts.text
    resolved_redis_alert = next(
        alert for alert in resolved_alerts.json() if alert["id"] == redis_alert["id"]
    )
    assert resolved_redis_alert["resolved_at"] is not None

    complete_redis_history = client.get(
        f"/api/v1/databases/{redis_database_id}/history", headers=headers
    )
    assert complete_redis_history.status_code == 200, complete_redis_history.text
    redis_samples = complete_redis_history.json()
    assert len(redis_samples) == 3
    assert len({sample["sample_id"] for sample in redis_samples}) == 3

    mongodb_database_id = _create_database(
        client,
        headers,
        engine="mongodb",
        connection_uri=TEST_MONGODB_URI,
    )
    mongodb_sample = _collect(client, headers, mongodb_database_id)
    assert mongodb_sample["metric_count"] == 4
    assert mongodb_sample["health_status"] == "healthy"

    mongodb_history = client.get(
        f"/api/v1/databases/{mongodb_database_id}/history", headers=headers
    )
    assert mongodb_history.status_code == 200, mongodb_history.text
    assert {metric["code"] for metric in mongodb_history.json()[0]["metrics"]} == {
        "availability",
        "connections_current",
        "memory_resident_mb",
        "operations_total",
    }

    with integration_session_factory() as session:
        stored_databases = list(
            session.scalars(
                select(MonitoredDatabase).where(
                    MonitoredDatabase.id.in_((redis_database_id, mongodb_database_id))
                )
            )
        )
        assert len(stored_databases) == 2
        stored_secrets = [database.connection_uri_encrypted for database in stored_databases]
        assert all(secret not in (TEST_REDIS_URI, TEST_MONGODB_URI) for secret in stored_secrets)
        assert all(TEST_REDIS_URI not in secret for secret in stored_secrets)
        assert all(TEST_MONGODB_URI not in secret for secret in stored_secrets)
