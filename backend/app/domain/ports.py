from abc import ABC, abstractmethod
from collections.abc import Mapping

from app.domain.models import DatabaseEngine


class DatabaseConnector(ABC):
    """Contrato que todo motor NoSQL debe implementar."""

    engine: DatabaseEngine

    @abstractmethod
    def test_connection(self, connection_uri: str) -> None:
        """Verifica que la URI sea válida y la instancia responda sin modificar datos."""

    @abstractmethod
    def collect_metrics(self, connection_uri: str) -> Mapping[str, float]:
        """Comprueba la conexión y devuelve métricas normalizadas."""
