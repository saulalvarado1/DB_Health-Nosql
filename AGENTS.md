# DB Health Monitor

## Scope

DB Health Monitor is a multi-user platform that monitors MongoDB and Redis.
V1.0 uses FastAPI, React, PostgreSQL, pytest, and Docker. PostgreSQL stores the
platform's own users, configuration, metrics, health assessments, and alerts;
it is not monitored in V1.0.

## Architecture

Use a modular monolith. Keep routes, services, repositories, and connectors
separate. Database-specific code belongs in connectors; the health engine works
only with normalized metrics and configurable rules. Do not introduce
microservices without explicit approval.

## Security and behavior

- Encrypt monitored-database credentials and never expose them in logs or API responses.
- Hash user passwords and use JWT for API access.
- Enforce ownership: users access only their own monitored instances.
- Use read-only, minimum-privilege accounts for MongoDB and Redis.
- The monitor must not modify customer data.
- The default interval is 30 seconds and remains configurable.

## V1 exclusions

Do not add SQL monitoring, Cassandra, Neo4j, predictive AI, or automated
database changes.

## Quality

Make schema changes through Alembic migrations, add focused tests for meaningful
behavior, and run available tests before reporting completion. Never commit
`.env`, `.venv`, caches, credentials, or generated package metadata.
