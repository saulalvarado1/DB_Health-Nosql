from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.domain.errors import ConnectorUnavailableError
from app.domain.models import DatabaseEngine
from app.domain.ports import DatabaseConnector


def numeric_value(source: dict[str, Any], key: str) -> float:
    value = source.get(key, 0)
    return float(value) if isinstance(value, int | float) else 0.0


def object_value(source: dict[str, Any], key: str) -> dict[str, Any]:
    value = source.get(key, {})
    return value if isinstance(value, dict) else {}


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

        connections = object_value(server_status, "connections")
        memory = object_value(server_status, "mem")
        network = object_value(server_status, "network")
        operations = object_value(server_status, "opcounters")
        global_lock = object_value(server_status, "globalLock")
        current_queue = object_value(global_lock, "currentQueue")
        active_clients = object_value(global_lock, "activeClients")
        metrics = object_value(server_status, "metrics")
        document_metrics = object_value(metrics, "document")
        cursor_metrics = object_value(object_value(metrics, "cursor"), "open")
        query_executor = object_value(metrics, "queryExecutor")
        wired_tiger_cache = object_value(object_value(server_status, "wiredTiger"), "cache")

        current_connections = numeric_value(connections, "current")
        available_connections = numeric_value(connections, "available")
        connection_capacity = current_connections + available_connections
        connections_usage_percent = (
            current_connections / connection_capacity * 100 if connection_capacity > 0 else 0.0
        )

        cache_bytes = numeric_value(wired_tiger_cache, "bytes currently in the cache")
        cache_maximum_bytes = numeric_value(wired_tiger_cache, "maximum bytes configured")
        wiredtiger_cache_usage_percent = (
            cache_bytes / cache_maximum_bytes * 100 if cache_maximum_bytes > 0 else 0.0
        )
        dirty_cache_bytes = numeric_value(wired_tiger_cache, "tracked dirty bytes in the cache")
        wiredtiger_cache_dirty_percent = (
            dirty_cache_bytes / cache_maximum_bytes * 100 if cache_maximum_bytes > 0 else 0.0
        )

        total_operations = sum(
            numeric_value(operations, operation)
            for operation in ("insert", "query", "update", "delete", "getmore", "command")
        )
        return {
            "availability": 1.0,
            "connections_active": numeric_value(connections, "active"),
            "connections_available": available_connections,
            "connections_current": current_connections,
            "connections_usage_percent": connections_usage_percent,
            "documents_read_total": numeric_value(document_metrics, "returned"),
            "documents_written_total": sum(
                numeric_value(document_metrics, operation)
                for operation in ("inserted", "updated", "deleted")
            ),
            "global_lock_active_clients": numeric_value(active_clients, "total"),
            "global_lock_queue_total": numeric_value(current_queue, "total"),
            "memory_resident_mb": numeric_value(memory, "resident"),
            "network_bytes_in": numeric_value(network, "bytesIn"),
            "network_bytes_out": numeric_value(network, "bytesOut"),
            "network_requests_total": numeric_value(network, "numRequests"),
            "open_cursors": numeric_value(cursor_metrics, "total"),
            "operations_total": total_operations,
            "query_scanned_documents_total": numeric_value(query_executor, "scannedObjects"),
            "query_scanned_keys_total": numeric_value(query_executor, "scanned"),
            "uptime_seconds": numeric_value(server_status, "uptime"),
            "wiredtiger_cache_dirty_percent": wiredtiger_cache_dirty_percent,
            "wiredtiger_cache_usage_percent": wiredtiger_cache_usage_percent,
        }
