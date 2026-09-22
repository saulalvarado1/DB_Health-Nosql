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
        keyspace_hits = as_float(info.get("keyspace_hits"))
        keyspace_misses = as_float(info.get("keyspace_misses"))
        keyspace_lookups = keyspace_hits + keyspace_misses
        keyspace_hit_rate_percent = (
            keyspace_hits / keyspace_lookups * 100 if keyspace_lookups > 0 else 0.0
        )
        keyspace_databases = [
            value
            for key, value in info.items()
            if key.startswith("db") and key[2:].isdigit() and isinstance(value, dict)
        ]
        keys_total = sum(as_float(database.get("keys")) for database in keyspace_databases)
        expiring_keys_total = sum(
            as_float(database.get("expires")) for database in keyspace_databases
        )
        return {
            "availability": 1.0,
            "blocked_clients": as_float(info.get("blocked_clients")),
            "connected_clients": as_float(info.get("connected_clients")),
            "connected_replicas": as_float(info.get("connected_slaves")),
            "evicted_keys": as_float(info.get("evicted_keys")),
            "expired_keys": as_float(info.get("expired_keys")),
            "expiring_keys_total": expiring_keys_total,
            "instantaneous_input_kbps": as_float(info.get("instantaneous_input_kbps")),
            "instantaneous_output_kbps": as_float(info.get("instantaneous_output_kbps")),
            "keys_total": keys_total,
            "keyspace_hit_rate_percent": keyspace_hit_rate_percent,
            "keyspace_hits_total": keyspace_hits,
            "keyspace_misses_total": keyspace_misses,
            "latest_fork_microseconds": as_float(info.get("latest_fork_usec")),
            "loading": as_float(info.get("loading")),
            "memory_fragmentation_ratio": as_float(info.get("mem_fragmentation_ratio")),
            "memory_usage_percent": memory_usage_percent,
            "network_input_bytes_total": as_float(info.get("total_net_input_bytes")),
            "network_output_bytes_total": as_float(info.get("total_net_output_bytes")),
            "operations_per_second": as_float(info.get("instantaneous_ops_per_sec")),
            "persistence_last_save_success": (
                1.0 if info.get("rdb_last_bgsave_status") == "ok" else 0.0
            ),
            "pubsub_channels": as_float(info.get("pubsub_channels")),
            "rejected_connections": as_float(info.get("rejected_connections")),
            "total_commands_processed": as_float(info.get("total_commands_processed")),
            "total_connections_received": as_float(info.get("total_connections_received")),
            "uptime_seconds": as_float(info.get("uptime_in_seconds")),
            "used_memory_bytes": used_memory,
        }
