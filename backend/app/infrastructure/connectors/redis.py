from typing import Any

import redis
from redis.exceptions import RedisError

from app.domain.errors import ConnectorUnavailableError
from app.domain.models import DatabaseEngine
from app.domain.ports import DatabaseConnector


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class RedisConnector(DatabaseConnector):
    engine = DatabaseEngine.REDIS

    def collect_metrics(self, connection_uri: str) -> dict[str, float]:
        client: redis.Redis | None = None
        try:
            client = redis.Redis.from_url(
                connection_uri,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            client.ping()
            info = client.info()
        except RedisError as error:
            raise ConnectorUnavailableError("No fue posible conectar con Redis.") from error
        finally:
            if client is not None:
                client.close()

        used_memory = as_float(info.get("used_memory"))
        max_memory = as_float(info.get("maxmemory"))
        memory_usage_percent = used_memory / max_memory * 100 if max_memory > 0 else 0.0
        return {
            "availability": 1.0,
            "used_memory_bytes": used_memory,
            "memory_usage_percent": memory_usage_percent,
            "connected_clients": as_float(info.get("connected_clients")),
            "operations_per_second": as_float(info.get("instantaneous_ops_per_sec")),
            "rejected_connections": as_float(info.get("rejected_connections")),
        }
