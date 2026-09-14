from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import MetricDefinition


class MetricCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enabled_for_engine(self, engine_id: str) -> dict[str, MetricDefinition]:
        statement = select(MetricDefinition).where(
            MetricDefinition.engine_id == engine_id,
            MetricDefinition.is_enabled.is_(True),
        )
        definitions = self._session.scalars(statement)
        return {definition.code: definition for definition in definitions}
