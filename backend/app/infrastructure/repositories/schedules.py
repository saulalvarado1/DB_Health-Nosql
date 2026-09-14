from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.persistence.models import MonitoredDatabase, MonitoringSchedule


class MonitoringScheduleRepository:
    """Coordina ejecuciones vencidas sin permitir que dos workers las recojan."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def claim_due(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
        batch_size: int,
    ) -> list[UUID]:
        statement = (
            select(MonitoringSchedule)
            .join(MonitoredDatabase)
            .where(
                MonitoringSchedule.is_enabled.is_(True),
                MonitoredDatabase.is_enabled.is_(True),
                MonitoringSchedule.next_run_at <= now,
                or_(
                    MonitoringSchedule.lease_expires_at.is_(None),
                    MonitoringSchedule.lease_expires_at <= now,
                ),
            )
            .order_by(MonitoringSchedule.next_run_at, MonitoringSchedule.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        schedules = list(self._session.scalars(statement))
        if not schedules:
            return []

        lease_expires_at = now + timedelta(seconds=lease_seconds)
        schedule_ids = [schedule.id for schedule in schedules]
        for schedule in schedules:
            schedule.lease_owner = worker_id
            schedule.lease_expires_at = lease_expires_at
        self._session.commit()
        return schedule_ids

    def get_claimed(self, schedule_id: UUID, worker_id: str, now: datetime) -> MonitoringSchedule | None:
        statement = (
            select(MonitoringSchedule)
            .options(joinedload(MonitoringSchedule.monitored_database))
            .where(
                MonitoringSchedule.id == schedule_id,
                MonitoringSchedule.lease_owner == worker_id,
                MonitoringSchedule.lease_expires_at > now,
            )
        )
        return self._session.scalar(statement)

    def complete(
        self,
        schedule: MonitoringSchedule,
        *,
        completed_at: datetime,
        error_message: str | None,
    ) -> None:
        schedule.last_run_at = completed_at
        schedule.next_run_at = completed_at + timedelta(seconds=schedule.interval_seconds)
        schedule.lease_owner = None
        schedule.lease_expires_at = None
        schedule.last_error = error_message
        self._session.commit()
