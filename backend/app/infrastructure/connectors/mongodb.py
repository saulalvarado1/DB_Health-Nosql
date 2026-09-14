from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.domain.errors import ConnectorUnavailableError
from app.domain.models import DatabaseEngine
from app.domain.ports import DatabaseConnector


def numeric_value(source: dict[str, Any], key: str) -> float:
    value = source.get(key, 0)
    return float(value) if isinstance(value, int | float) else 0.0


class MongoDBConnector(DatabaseConnector):
    engine = DatabaseEngine.MONGODB

    def collect_metrics(self, connection_uri: str) -> dict[str, float]:
        client: MongoClient[dict[str, Any]] | None = None
        try:
            client = MongoClient(
                connection_uri,
                serverSelectionTimeoutMS=5_000,
                connectTimeoutMS=5_000,
                socketTimeoutMS=5_000,
            )
            client.admin.command("ping")
            server_status = client.admin.command("serverStatus")
        except PyMongoError as error:
            raise ConnectorUnavailableError("No fue posible conectar con MongoDB.") from error
        finally:
            if client is not None:
                client.close()

        connections = server_status.get("connections", {})
        memory = server_status.get("mem", {})
        operations = server_status.get("opcounters", {})
        total_operations = sum(
            numeric_value(operations, operation)
            for operation in ("insert", "query", "update", "delete", "command")
        )
        return {
            "availability": 1.0,
            "connections_current": numeric_value(connections, "current"),
            "memory_resident_mb": numeric_value(memory, "resident"),
            "operations_total": total_operations,
        }
