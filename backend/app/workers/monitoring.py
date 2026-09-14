import logging
import os
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.secrets import CredentialsCipher
from app.infrastructure.connectors import build_connector_registry
from app.infrastructure.repositories.schedules import MonitoringScheduleRepository
from app.services.monitoring import MonitoringService

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


@dataclass(frozen=True, slots=True)
class WorkerRunSummary:
    claimed: int
    completed: int
    failed: int


class MonitoringWorker:
    """Ejecuta recolecciones vencidas mediante reservas temporales en PostgreSQL."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        worker_id: str,
        lease_seconds: int,
        batch_size: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._batch_size = batch_size
        self._now = now

    def run_once(self) -> WorkerRunSummary:
        claimed_ids = self._claim_due_schedules()
        completed = 0
        failed = 0
        for schedule_id in claimed_ids:
            try:
                succeeded = self._run_claimed_schedule(schedule_id)
            except Exception:  # noqa: BLE001 - A task cannot stop the rest of its batch.
                logger.warning(
                    "No fue posible procesar una tarea programada; se reintentará al vencer la reserva."
                )
                failed += 1
                continue

            if succeeded:
                completed += 1
            else:
                failed += 1
        return WorkerRunSummary(claimed=len(claimed_ids), completed=completed, failed=failed)

    def _claim_due_schedules(self) -> list[UUID]:
        with self._session_factory() as session:
            return MonitoringScheduleRepository(session).claim_due(
                worker_id=self._worker_id,
                now=self._now(),
                lease_seconds=self._lease_seconds,
                batch_size=self._batch_size,
            )

    def _run_claimed_schedule(self, schedule_id: UUID) -> bool:
        with self._session_factory() as session:
            schedules = MonitoringScheduleRepository(session)
            schedule = schedules.get_claimed(schedule_id, self._worker_id, self._now())
            if schedule is None:
                return False

            error_message: str | None = None
            try:
                MonitoringService(
                    session=session,
                    cipher=CredentialsCipher(),
                    connectors=build_connector_registry(),
                ).collect_once(schedule.monitored_database)
            except Exception:  # noqa: BLE001 - A worker must release its claimed schedule.
                session.rollback()
                error_message = "No fue posible completar la recolección programada."
                logger.warning(
                    "Falló una recolección programada para la programación %s.",
                    schedule_id,
                )
            finally:
                try:
                    schedules.complete(
                        schedule,
                        completed_at=self._now(),
                        error_message=error_message,
                    )
                except Exception:  # noqa: BLE001 - A failed close must preserve the retry lease.
                    session.rollback()
                    logger.warning(
                        "No fue posible registrar el cierre de una tarea programada; "
                        "se reintentará al vencer la reserva."
                    )
                    return False
            return error_message is None


def build_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:12]}"


def run_forever() -> None:
    worker = MonitoringWorker(
        session_factory=SessionLocal,
        worker_id=build_worker_id(),
        lease_seconds=settings.monitoring_lease_seconds,
        batch_size=settings.monitoring_worker_batch_size,
    )
    logger.info("Worker de monitoreo iniciado.")
    while True:
        try:
            summary = worker.run_once()
            if summary.claimed:
                logger.info(
                    "Worker procesó %s tareas: %s correctas, %s fallidas.",
                    summary.claimed,
                    summary.completed,
                    summary.failed,
                )
        except Exception:  # noqa: BLE001 - Transient infrastructure errors must be retried.
            logger.warning("El ciclo de monitoreo no pudo ejecutarse; se reintentará.")
        time.sleep(settings.monitoring_worker_poll_seconds)


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Worker de monitoreo detenido.")


if __name__ == "__main__":
    main()
