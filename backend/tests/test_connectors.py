from typing import Any

import pytest

from app.infrastructure.connectors import mongodb as mongodb_connector
from app.infrastructure.connectors import redis as redis_connector


class FakeMongoAdmin:
    def command(self, command: str) -> dict[str, Any]:
        if command == "ping":
            return {"ok": 1.0}
        return {
            "connections": {"current": 20, "available": 80, "active": 7},
            "globalLock": {
                "currentQueue": {"total": 2},
                "activeClients": {"total": 9},
            },
            "mem": {"resident": 256},
            "metrics": {
                "document": {"returned": 100, "inserted": 3, "updated": 4, "deleted": 5},
                "cursor": {"open": {"total": 6}},
                "queryExecutor": {"scanned": 70, "scannedObjects": 80},
            },
            "network": {"bytesIn": 1_024, "bytesOut": 2_048, "numRequests": 12},
            "opcounters": {
                "insert": 1,
                "query": 2,
                "update": 3,
                "delete": 4,
                "getmore": 5,
                "command": 6,
            },
            "uptime": 3_600,
            "wiredTiger": {
                "cache": {
                    "bytes currently in the cache": 750,
                    "maximum bytes configured": 1_000,
                    "tracked dirty bytes in the cache": 100,
                }
            },
        }


class FakeMongoClient:
    last_instance: "FakeMongoClient | None" = None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.admin = FakeMongoAdmin()
        self.closed = False
        FakeMongoClient.last_instance = self

    def close(self) -> None:
        self.closed = True


class FakeRedisClient:
    def __init__(self) -> None:
        self.closed = False

    def ping(self) -> bool:
        return True

    def info(self) -> dict[str, Any]:
        return {
            "used_memory": 25,
            "maxmemory": 100,
            "blocked_clients": 2,
            "connected_clients": 3,
            "connected_slaves": 1,
            "evicted_keys": 4,
            "expired_keys": 5,
            "instantaneous_input_kbps": 1.5,
            "instantaneous_output_kbps": 2.5,
            "keyspace_hits": 80,
            "keyspace_misses": 20,
            "latest_fork_usec": 250,
            "loading": 0,
            "mem_fragmentation_ratio": 1.25,
            "instantaneous_ops_per_sec": 6,
            "total_net_input_bytes": 1_024,
            "total_net_output_bytes": 2_048,
            "rdb_last_bgsave_status": "ok",
            "pubsub_channels": 2,
            "rejected_connections": 7,
            "total_commands_processed": 200,
            "total_connections_received": 50,
            "uptime_in_seconds": 3_600,
            "db0": {"keys": 8, "expires": 3},
            "db2": {"keys": 2, "expires": 1},
        }

    def close(self) -> None:
        self.closed = True


def test_mongodb_connector_collects_the_expanded_metric_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mongodb_connector, "MongoClient", FakeMongoClient)

    metrics = mongodb_connector.MongoDBConnector().collect_metrics("mongodb://example")

    assert metrics == {
        "availability": 1.0,
        "connections_active": 7.0,
        "connections_available": 80.0,
        "connections_current": 20.0,
        "connections_usage_percent": 20.0,
        "documents_read_total": 100.0,
        "documents_written_total": 12.0,
        "global_lock_active_clients": 9.0,
        "global_lock_queue_total": 2.0,
        "memory_resident_mb": 256.0,
        "network_bytes_in": 1_024.0,
        "network_bytes_out": 2_048.0,
        "network_requests_total": 12.0,
        "open_cursors": 6.0,
        "operations_total": 21.0,
        "query_scanned_documents_total": 80.0,
        "query_scanned_keys_total": 70.0,
        "uptime_seconds": 3_600.0,
        "wiredtiger_cache_dirty_percent": 10.0,
        "wiredtiger_cache_usage_percent": 75.0,
    }
    assert FakeMongoClient.last_instance is not None
    assert FakeMongoClient.last_instance.closed is True


def test_redis_connector_collects_the_expanded_metric_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeRedisClient()
    monkeypatch.setattr(redis_connector.redis.Redis, "from_url", lambda *_args, **_kwargs: client)

    metrics = redis_connector.RedisConnector().collect_metrics("redis://example")

    assert metrics == {
        "availability": 1.0,
        "blocked_clients": 2.0,
        "connected_clients": 3.0,
        "connected_replicas": 1.0,
        "evicted_keys": 4.0,
        "expired_keys": 5.0,
        "expiring_keys_total": 4.0,
        "instantaneous_input_kbps": 1.5,
        "instantaneous_output_kbps": 2.5,
        "keys_total": 10.0,
        "keyspace_hit_rate_percent": 80.0,
        "keyspace_hits_total": 80.0,
        "keyspace_misses_total": 20.0,
        "latest_fork_microseconds": 250.0,
        "loading": 0.0,
        "memory_fragmentation_ratio": 1.25,
        "memory_usage_percent": 25.0,
        "network_input_bytes_total": 1_024.0,
        "network_output_bytes_total": 2_048.0,
        "operations_per_second": 6.0,
        "persistence_last_save_success": 1.0,
        "pubsub_channels": 2.0,
        "rejected_connections": 7.0,
        "total_commands_processed": 200.0,
        "total_connections_received": 50.0,
        "uptime_seconds": 3_600.0,
        "used_memory_bytes": 25.0,
    }
    assert client.closed is True


def test_derived_percentages_are_safe_when_denominators_are_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeRedisClient()
    monkeypatch.setattr(
        client,
        "info",
        lambda: {
            "used_memory": 25,
            "maxmemory": 0,
            "keyspace_hits": 0,
            "keyspace_misses": 0,
        },
    )
    monkeypatch.setattr(redis_connector.redis.Redis, "from_url", lambda *_args, **_kwargs: client)

    metrics = redis_connector.RedisConnector().collect_metrics("redis://example")

    assert metrics["memory_usage_percent"] == 0.0
    assert metrics["keyspace_hit_rate_percent"] == 0.0
