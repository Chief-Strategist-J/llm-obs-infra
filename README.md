# LLM Observability & Infrastructure Platform (`llm-obs-infra`)

Enterprise-grade, distributed observability and telemetry pipeline for Large Language Model (LLM) agents, multi-model workflows, vector search, and token spend analytics.

---

## Quick Start

```bash
# 1. Bootstrap platform certificates and configuration
./bin/llmobs setup

# 2. Launch full infrastructure stack
./bin/llmobs up full

# 3. Verify health across all 10 core services
./bin/llmobs health --deep

# 4. Access Grafana Observability Portal
open http://localhost:31415
```

---

## CLI Command Reference (`./bin/llmobs`)

The platform is managed by a single unified Go orchestrator binary (`./bin/llmobs`).

### 1. Platform Stack Operations

```bash
# Start stack (Interactive profile selector)
./bin/llmobs up

# Start full stack directly
./bin/llmobs up full

# Start specific profiles
./bin/llmobs up db streaming
./bin/llmobs up stateless
./bin/llmobs up stateful

# Display real-time container status
./bin/llmobs status

# Stream container logs
./bin/llmobs logs
./bin/llmobs logs 100

# Restart platform
./bin/llmobs restart full

# Stop all containers and clean orphan resources
./bin/llmobs down
```

---

### 2. Health & Deep Diagnostics (`llmobs health`)

```bash
# Run concurrent latency and connectivity probes
./bin/llmobs health

# Deep functional verification (Postgres, ClickHouse queries, Redis RESP, Grafana API)
./bin/llmobs health --deep

# Filter by services or profile groups
./bin/llmobs health --deep --services alloydb,clickhouse,redis,grafana
./bin/llmobs health --deep --profiles stateful
```

---

### 3. Dynamic External Services & Data Connections (`llmobs service`)

Connect, probe, and manage any external service, LLM provider, or database dynamically:

```bash
# Register an LLM Provider (OpenAI, Anthropic, Groq, Ollama)
./bin/llmobs service add OpenAI --type openai --url https://api.openai.com/v1 --category llm --auth-token $OPENAI_API_KEY

# Register an External SQL Database
./bin/llmobs service add Prod-Postgres --type postgres --host db.prod.internal --port 5432 --category database --database analytics --auth-user admin --auth-pass secret

# Register a Vector Database
./bin/llmobs service add Qdrant-Cluster --type qdrant --url https://qdrant.internal:6333 --category vector-db

# List all registered services
./bin/llmobs service list
./bin/llmobs service list --category database

# Get service definition JSON
./bin/llmobs service get OpenAI

# Run live health check probe (HTTP status or TCP socket probe)
./bin/llmobs service test Prod-Postgres

# Bridge the data connection directly into Grafana as a datasource
./bin/llmobs service sync-to-grafana Prod-Postgres

# Unregister a service
./bin/llmobs service delete OpenAI
```

---

### 4. Dynamic Grafana Datasources (`llmobs datasource`)

Manage Grafana datasources via CLI without manual YAML editing:

```bash
# List all configured datasources
./bin/llmobs datasource list

# Add a Prometheus datasource
./bin/llmobs datasource add Prometheus --type prometheus --url http://prometheus:9090

# Add an AlloyDB / PostgreSQL datasource
./bin/llmobs datasource add CustomPostgres --type postgres --url host.docker.internal:5432 --user admin --password secret --database analytics

# Test connection health of a datasource
./bin/llmobs datasource test AlloyDB

# Batch synchronize platform datasources from environment
./bin/llmobs datasource sync

# Delete a datasource
./bin/llmobs datasource delete CustomPostgres
```

---

### 5. Dynamic Grafana Dashboards (`llmobs dashboard`)

Import, export, search, and delete Grafana dashboards:

```bash
# List all configured dashboards
./bin/llmobs dashboard list

# Search dashboards by title
./bin/llmobs dashboard list --query "telemetry"

# Import dashboard from local JSON file
./bin/llmobs dashboard import ./dashboards/llm-telemetry.json --overwrite

# Import dashboard directly from Grafana.com URL
./bin/llmobs dashboard import https://grafana.com/api/dashboards/1860/revisions/latest/download

# Export dashboard JSON
./bin/llmobs dashboard export <uid> --output ./backup-dash.json

# Delete a dashboard
./bin/llmobs dashboard delete <uid>
```

---

### 6. Dynamic Grafana Unified Alerting (`llmobs alert`)

Manage alert rules and notification channels (Slack, Webhooks, Email, PagerDuty):

```bash
# List all alert rules
./bin/llmobs alert list

# Add or update an alert rule from a JSON file
./bin/llmobs alert add ./alerts/high-latency-rule.json

# Delete an alert rule
./bin/llmobs alert delete <uid>

# List notification contact points
./bin/llmobs alert contact-point list

# Add a Slack notification contact point
./bin/llmobs alert contact-point add Slack-Alerts --type slack --webhook-url https://hooks.slack.com/services/...

# Add a Webhook notification contact point
./bin/llmobs alert contact-point add Ops-Webhook --type webhook --url https://webhook.internal/alerts

# Send a test alert notification
./bin/llmobs alert contact-point test Slack-Alerts

# Delete a contact point
./bin/llmobs alert contact-point delete Slack-Alerts
```

---

### 7. Resource Configuration (`llmobs config`)

```bash
# View active platform configuration and limits
./bin/llmobs config

# Interactive resource limits wizard
./bin/llmobs config -i

# Set container memory limits and restart
./bin/llmobs config --temporal-memory 4096M --clickhouse-memory 8192M --restart
```

---

### 8. Horizontal Scaling (`llmobs scale`)

```bash
# Interactive scaling menu
./bin/llmobs scale

# Scale stateless services to N replicas
./bin/llmobs scale service llmobs-temporal 3
./bin/llmobs scale service llmobs-traefik 2

# Scale simulated worker nodes
./bin/llmobs scale node 1 host.docker.internal
./bin/llmobs scale list
./bin/llmobs scale down-node 1
```

---

### 9. Disaster Recovery & GDPR Compliance (`backup-purge`, `gdpr-erasure`)

```bash
# Dump databases to backup archive
./bin/llmobs backup-purge --backup-only

# Backup and purge persistent Docker volumes
./bin/llmobs backup-purge

# Execute GDPR/CCPA Right-to-Erasure across databases
./bin/llmobs gdpr-erasure --user-id "usr_12345" --actor-id "admin_ops"
```

---

### 10. Security & Ingress (`certs`, `cloudflare`, `free-ports`)

```bash
# Generate pure-Go self-signed TLS certificates (server.pem, ca.pem)
./bin/llmobs certs

# Detect and resolve host port contention
./bin/llmobs free-ports

# Manage Cloudflare Zero-Trust Ingress Tunnels
./bin/llmobs cloudflare setup
./bin/llmobs cloudflare start
./bin/llmobs cloudflare status
./bin/llmobs cloudflare logs
./bin/llmobs cloudflare stop
```

---

### 11. REST API Daemon (`server`)

```bash
# Start API daemon on port 31427
./bin/llmobs server
```

REST API routes follow standard JSON envelope formatting (`meta`, `data`, `errors`):
- `/api/v1/stack/*` — Stack lifecycle operations
- `/api/v1/health` & `/api/v1/health/deep` — Diagnostic endpoints
- `/api/v1/services` — External service catalog & health probe
- `/api/v1/grafana/datasources` — Dynamic Grafana datasources
- `/api/v1/grafana/dashboards` — Dynamic Grafana dashboards
- `/api/v1/grafana/alerts` & `/api/v1/grafana/contact-points` — Unified alerting
- `/api/v1/config` — Resource limit management
- `/api/v1/gdpr/erasure` — GDPR data erasure

---

## Platform Service & Port Reference

| Service | Host Port | Protocol | Purpose |
|---|---|---|---|
| **Traefik Gateway** | `31410`, `31411`, `31419` | HTTP / HTTPS | Edge routing & reverse proxy |
| **Redis Ledger** | `31413` | TCP / RESP | Real-time token spend rate limiting |
| **Kafka Broker** | `31414` | TCP / Binary | Telemetry event streaming |
| **Grafana Dashboard** | `31415` | HTTP | Observability visualization portal |
| **Grafana Tempo** | `31416`, `31423` | HTTP / gRPC | Distributed trace ingestion & storage |
| **OTel Collector** | `31417`, `31418` | HTTP / gRPC | OpenTelemetry trace/metric processing |
| **AlloyDB (PostgreSQL)** | `31420` | PostgreSQL | Relational metadata & user store |
| **ClickHouse Analytics** | `31421`, `31422` | HTTP / Native | High-throughput telemetry analytics |
| **Temporal Engine** | `31424`, `31425` | gRPC / HTTP UI | Resilient workflow orchestration |
| **Service Registry** | `31426` | HTTP | Service discovery catalog |
| **Platform Orchestrator API** | `31427` | HTTP | Unified management REST API daemon |
