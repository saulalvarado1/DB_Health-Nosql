from datetime import UTC, datetime
from types import SimpleNamespace
from typing import ClassVar, Self
from uuid import UUID, uuid4

import app.workers.monitoring as worker_module


class FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def rollback(self) -> None:
        self.rollback_calls += 1


class FakeScheduleRepository:
    schedule_id: UUID
    schedule: SimpleNamespace
    claimed_calls: ClassVar[list[dict[str, object]]] = []
    completions: ClassVar[list[dict[str, object]]] = []

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    @classmethod
    def reset(cls, schedule_id: UUID) -> None:
        cls.schedule_id = schedule_id
        cls.schedule = SimpleNamespace(
            monitored_database=object(), monitored_database_id=schedule_id
        )
        cls.claimed_calls = []
        cls.completions = []

    def claim_due(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
        batch_size: int,
    ) -> list[UUID]:
        self.claimed_calls.append(
            {
                "worker_id": worker_id,
                "now": now,
                "lease_seconds": lease_seconds,
                "batch_size": batch_size,
            }
        )
        return [self.schedule_id]

    def get_claimed(
        self, schedule_id: UUID, worker_id: str, now: datetime
    ) -> SimpleNamespace | None:
        assert schedule_id == self.schedule_id
        assert worker_id == "worker-test"
        return self.schedule

    def complete(
        self,
        schedule: SimpleNamespace,
        *,
        completed_at: datetime,
        error_message: str | None,
    ) -> None:
        self.completions.append(
            {
                "schedule": schedule,
                "completed_at": completed_at,
                "error_message": error_message,
            }
        )


def build_worker(monkeypatch: object, service: type[object]) -> tuple[worker_module.MonitoringWorker, list[FakeSession]]:
    schedule_id = uuid4()
    FakeScheduleRepository.reset(schedule_id)
    monkeypatch.setattr(worker_module, "MonitoringScheduleRepository", FakeScheduleRepository)
    monkeypatch.setattr(worker_module, "MonitoringService", service)
    monkeypatch.setattr(worker_module, "CredentialsCipher", lambda: object())
    monkeypatch.setattr(worker_module, "build_connector_registry", lambda: object())
    sessions = [FakeSession(), FakeSession()]
    fixed_now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    worker = worker_module.MonitoringWorker(
        session_factory=lambda: sessions.pop(0),
        worker_id="worker-test",
        lease_seconds=90,
        batch_size=10,
        now=lambda: fixed_now,
    )
    return worker, sessions


def test_worker_claims_and_completes_a_due_schedule(monkeypatch: object) -> None:
    collected: list[object] = []

    class SuccessfulMonitoringService:
        def __init__(self, **_: object) -> None:
            pass

        def collect_once(self, monitored_database: object) -> None:
            collected.append(monitored_database)

    worker, _ = build_worker(monkeypatch, SuccessfulMonitoringService)

    summary = worker.run_once()

    assert summary == worker_module.WorkerRunSummary(claimed=1, completed=1, failed=0)
    assert len(collected) == 1
    assert FakeScheduleRepository.claimed_calls == [
        {
            "worker_id": "worker-test",
            "now": datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
            "lease_seconds": 90,
            "batch_size": 10,
        }
    ]
    assert FakeScheduleRepository.completions[0]["error_message"] is None


def test_worker_releases_schedule_without_logging_connection_details(
    monkeypatch: object, caplog: object
) -> None:
    class FailingMonitoringService:
        def __init__(self, **_: object) -> None:
            pass

        def collect_once(self, monitored_database: object) -> None:
            raise RuntimeError("redis://secret-password@example.test:6379/0")

    worker, remaining_sessions = build_worker(monkeypatch, FailingMonitoringService)

    summary = worker.run_once()

    assert summary == worker_module.WorkerRunSummary(claimed=1, completed=0, failed=1)
    assert FakeScheduleRepository.completions[0]["error_message"] == (
        "No fue posible completar la recolección programada."
    )
    assert "secret-password" not in caplog.text
    assert remaining_sessions == []
