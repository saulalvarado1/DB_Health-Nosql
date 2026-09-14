from app.api.schemas.monitored_databases import MonitoredDatabaseResponse
from app.infrastructure.persistence.models import MonitoredDatabase


def monitored_database_response(database: MonitoredDatabase) -> MonitoredDatabaseResponse:
    """Transforma una entidad en respuesta pública y excluye la URI cifrada."""
    if database.schedule is None:
        raise RuntimeError("La instancia monitoreada no tiene programación configurada.")
    return MonitoredDatabaseResponse(
        id=database.id,
        name=database.name,
        engine=database.engine_id,
        interval_seconds=database.schedule.interval_seconds,
        is_enabled=database.is_enabled,
        created_at=database.created_at,
    )
