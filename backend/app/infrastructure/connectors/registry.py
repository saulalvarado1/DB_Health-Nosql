from app.domain.errors import ConfigurationError
from app.domain.models import DatabaseEngine
from app.domain.ports import DatabaseConnector


class ConnectorRegistry:
    """Resuelve el adaptador correcto sin acoplar los servicios a sus clases."""

    def __init__(self, connectors: list[DatabaseConnector]) -> None:
        self._connectors = {connector.engine: connector for connector in connectors}

    def get(self, engine_id: str) -> DatabaseConnector:
        try:
            engine = DatabaseEngine(engine_id)
            return self._connectors[engine]
        except (ValueError, KeyError) as error:
            raise ConfigurationError("No existe un conector para el motor solicitado.") from error
