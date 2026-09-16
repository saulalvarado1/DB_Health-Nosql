"""Prueba las reservas concurrentes del worker contra PostgreSQL real."""

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.persistence.models import MonitoredDatabase, MonitoringSchedule, User
from app.infrastructure.repositories.schedules import MonitoringScheduleRepository

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


def _delete_worker_test_users(session_factory: sessionmaker[Session]) -> None:
    session = session_factory()
    try:
        session.execute(delete(User).where(User.email.like("integration-worker-%@example.com")))
        session.commit()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_worker_test_users(
    integration_session_factory: sessionmaker[Session],
) -> Generator[None, None, None]:
    _delete_worker_test_users(integration_session_factory)
    try:
        yield
    finally:
        _delete_worker_test_users(integration_session_factory)


def _create_due_schedules(session_factory: sessionmaker[Session], now: datetime) -> set[UUID]:
    session = session_factory()
    try:
        suffix = uuid4().hex
        owner = User(
            email=f"integration-worker-{suffix}@example.com",
            password_hash="not-used-by-worker-concurrency-test",
        )
        session.add(owner)
        session.flush()

        databases: list[MonitoredDatabase] = []
        for index in range(2):
            database = MonitoredDatabase(
                owner_id=owner.id,
                engine_id="redis",
                name=f"integration-worker-redis-{suffix}-{index}",
                connection_uri_encrypted=f"integration-ciphertext-{suffix}-{index}",
            )
            database.schedule = MonitoringSchedule(
                interval_seconds=30,
                next_run_at=now - timedelta(seconds=1),
            )
            databases.append(database)
        session.add_all(databases)
        session.flush()
        schedule_ids = {database.schedule.id for database in databases}
        session.commit()
        return schedule_ids
    finally:
        session.close()


def test_workers_skip_locked_schedules_and_reclaim_expired_leases(
    integration_session_factory: sessionmaker[Session],
) -> None:
    now = datetime.now(UTC)
    due_schedule_ids = _create_due_schedules(integration_session_factory, now)
    first_worker_has_lock = Event()
    allow_first_worker_commit = Event()
    first_worker_claims: list[UUID] = []
    first_worker_errors: list[Exception] = []

    def claim_with_first_worker() -> None:
        session = integration_session_factory()

        @event.listens_for(session, "before_commit")
        def pause_before_commit(_: Session) -> None:
            first_worker_has_lock.set()
            if not allow_first_worker_commit.wait(timeout=5):
                raise TimeoutError("El segundo worker no terminó dentro del plazo de la prueba.")

        try:
            first_worker_claims.extend(
                MonitoringScheduleRepository(session).claim_due(
                    worker_id="integration-worker-a",
                    now=now,
                    lease_seconds=60,
                    batch_size=1,
                )
            )
        except Exception as error:  # noqa: BLE001 - Propaga fallos ocurridos en el hilo.
            first_worker_errors.append(error)
        finally:
            session.close()

    first_worker_thread = Thread(target=claim_with_first_worker, daemon=True)
    first_worker_thread.start()
    assert first_worker_has_lock.wait(timeout=5), "El primer worker no adquirió el bloqueo."

    second_worker_claims: list[UUID] = []
    try:
        with integration_session_factory() as second_session:
            second_worker_claims = MonitoringScheduleRepository(second_session).claim_due(
                worker_id="integration-worker-b",
                now=now,
                lease_seconds=60,
                batch_size=1,
            )
    finally:
        allow_first_worker_commit.set()

    first_worker_thread.join(timeout=5)
    assert not first_worker_thread.is_alive(), "El primer worker no finalizó."
    assert first_worker_errors == []
    assert len(first_worker_claims) == 1
    assert len(second_worker_claims) == 1
    assert set(first_worker_claims).isdisjoint(second_worker_claims)
    assert set(first_worker_claims + second_worker_claims) == due_schedule_ids

    with integration_session_factory() as verification_session:
        schedules = list(
            verification_session.scalars(
                select(MonitoringSchedule).where(MonitoringSchedule.id.in_(due_schedule_ids))
            )
        )
        assert {schedule.lease_owner for schedule in schedules} == {
            "integration-worker-a",
            "integration-worker-b",
        }

    with integration_session_factory() as active_lease_session:
        active_lease_claims = MonitoringScheduleRepository(active_lease_session).claim_due(
            worker_id="integration-worker-c",
            now=now,
            lease_seconds=60,
            batch_size=2,
        )
    assert active_lease_claims == []

    with integration_session_factory() as expired_lease_session:
        expired_lease_claims = MonitoringScheduleRepository(expired_lease_session).claim_due(
            worker_id="integration-worker-c",
            now=now + timedelta(seconds=61),
            lease_seconds=60,
            batch_size=2,
        )
    assert set(expired_lease_claims) == due_schedule_ids
