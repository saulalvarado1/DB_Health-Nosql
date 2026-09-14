"""Implementaciones de conectores para motores monitoreados."""

from app.infrastructure.connectors.mongodb import MongoDBConnector
from app.infrastructure.connectors.redis import RedisConnector
from app.infrastructure.connectors.registry import ConnectorRegistry


def build_connector_registry() -> ConnectorRegistry:
    return ConnectorRegistry([MongoDBConnector(), RedisConnector()])
