# User Service

Local domain microservice for user identity, profiles, and access control within the LLM Observability Platform.

---

## Infrastructure Requirements

This service relies on the following centralized platform infrastructure components:
- **AlloyDB (PostgreSQL)**: User accounts, profile schema, and credentials (`PORT_ALLOYDB: 31420`).
- **Redis Ledger**: User sessions, rate limits, and token invalidation (`PORT_REDIS: 31413`).
- **Kafka Broker**: User lifecycle events (`user.created`, `user.updated`, `user.deleted`) (`PORT_KAFKA: 31414`).
- **OpenTelemetry Collector**: Distributed traces and telemetry telemetry ingestion (`PORT_OTEL_HTTP: 31417`).
- **Service Registry**: Automatic discovery and registration (`PORT_REGISTRY: 31426`).

---

## Managing Infrastructure via Platform Orchestrator

Instead of maintaining redundant per-service Docker Compose files or shell scripts, use the central `llmobs` orchestrator:

```bash
# 1. Start the required database and streaming infrastructure
./bin/llmobs up db streaming

# Or start the full 10-service platform stack:
./bin/llmobs up full

# 2. Check infrastructure health across all services
./bin/llmobs health

# 3. View live infrastructure status
./bin/llmobs status

# 4. Tune resource limits dynamically (e.g. Memory / CPU)
./bin/llmobs config --alloydb-memory 4096M --redis-memory 512M

# 5. Bootstrap credentials interactively if needed
./bin/llmobs setup -i

# 6. Stop all infrastructure when finished
./bin/llmobs down
```

---

## Local Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. The default variables are pre-configured to connect directly to the active `llmobs` platform ports on `localhost`.
