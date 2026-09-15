# ADR-0019: Service Sub-Stack Isolated Memory Sizing, Configuration Bounds & Compose Profile Architecture

| Field | Value |
|---|---|
| **Document ID** | ADR-0019 |
| **Status** | **Accepted (Implemented & Verified)** |
| **Author(s)** | Principal Infrastructure Architect |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-15 |
| **Version** | 1.0.0 |
| **Scope** | `services/{auth,audit,notifications,payment,storage,user}/docker-compose.yml`, `services/*/scripts/deploy.sh`, `config/alloydb/postgresql.conf` |
| **Validated Against** | Docker Engine 24.0+, Docker Compose v2.20+, AlloyDB Omni 15, OpenTelemetry Collector Contrib v0.160.0+ |

---

## 1. Executive Summary

This Architecture Decision Record (ADR) formalizes the memory budgeting, resource constraints, health check standards, and profile isolation topology across all microservice sub-stacks (`services/auth`, `services/audit`, `services/notifications`, `services/payment`, `services/storage`, and `services/user`).

Prior to this decision:
1. **Host-Derived Shared Buffers in AlloyDB Omni**: Without explicitly mounting `postgresql.conf` and passing `-c config_file=...`, AlloyDB Omni containers computed `shared_buffers` dynamically from the total host RAM (~15 GB) resulting in ~12 GB allocations inside constrained containers. This triggered internal watchdog backend terminations (`g_term_it`: *Memory critically low*) and crash loops.
2. **Unsupported Healthcheck Executables in Minimal Containers**: The OpenTelemetry Collector Contrib image is distroless and lacks `/bin/sh` and `curl`/`wget`. Docker's default `CMD-SHELL` healthchecks failed with OCI runtime errors, falsely flagging healthy collector instances as `unhealthy`.
3. **Missing Profile Declarations**: Service sub-stacks lacked Docker Compose `profiles:` metadata, impeding profile-targeted execution (`--profile <service>`).

---

## 2. Memory Consumption & Sizing Topology

Each service sub-stack is composed of 5 dedicated containers designed to provide complete domain-level data isolation, streaming, telemetry, and discovery.

### 2.1 Sub-Stack Container Memory Matrix

| Container Role | Image | Reservation (Min) | Limit (Max Ceiling) | Heap / Buffer Config | Primary Memory Consumer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Database** | `google/alloydbomni:15` | **1024 MB** | **3072 MB** | `shared_buffers = 512MB`<br>`effective_cache_size = 1200MB`<br>`columnar_mem = 256MB` | Shared buffers, columnar cache, per-connection `work_mem` |
| **Kafka Broker** | `apache/kafka:latest` | **512 MB** | **2048 MB** | `-Xms512m -Xmx1024m` | JVM Heap, OS Page Cache for partition segments |
| **OTel Collector** | `otel/opentelemetry-collector-contrib` | **256 MB** | **1024 MB** | `GOMEMLIMIT=858993459` (819 MB) | In-memory batch buffers, queue processors, serialization |
| **Redis Ledger** | `redis:7-alpine` | **32 MB** | **256 MB** | `maxmemory 128mb` | In-memory key-value dictionary, ephemeral session cache |
| **Service Registry** | `chiefj/llmobs-service-registry` | **32 MB** | **128 MB** | Native compiled Go | Catalog metadata table in memory, Traefik sync state |
| **Sub-Stack Total** | *All 5 Containers* | **~1.85 GB** | **~6.5 GB** | — | — |

---

## 3. Architecture Decisions

### 3.1 AlloyDB Omni Memory Bounding via `postgresql.conf`
* **Decision**: All sub-stack databases MUST mount `../../config/alloydb/postgresql.conf` and specify the startup command:
  ```yaml
  command:
    - "postgres"
    - "-c"
    - "config_file=/etc/postgresql/postgresql.conf"
  ```
* **Rationale**: Capping `shared_buffers = 512MB` and `google_columnar_engine.memory_size_in_mb = 256` prevents AlloyDB Omni from claiming host-level allocations and prevents `g_term_it` backend eviction failures.

### 3.2 Distroless Container Health Check Standardization
* **Decision**: Remove `CMD-SHELL` invocations that invoke `/bin/sh` or `wget` inside distroless containers (`otel/opentelemetry-collector-contrib`).
* **Rationale**: Distroless images do not ship with interactive shells. Health verification is validated externally via TCP readiness probes on ports `4317` (gRPC) and `4318` (HTTP).

### 3.3 Uniform Profile Tagging Topology
* **Decision**: Every service definition in `services/<service>/docker-compose.yml` is annotated with the profile taxonomy:
  ```yaml
  profiles: ["<service_name>", "full", "<tier>"]
  ```
* **Profile Mapping**:
  - `services/auth` -> `profiles: ["auth", "db", "streaming", "tracing", "network", "full"]`
  - `services/audit` -> `profiles: ["audit", "db", "streaming", "tracing", "network", "full"]`
  - `services/notifications` -> `profiles: ["notifications", "db", "streaming", "tracing", "network", "full"]`
  - `services/payment` -> `profiles: ["payment", "db", "streaming", "tracing", "network", "full"]`
  - `services/storage` -> `profiles: ["storage", "db", "streaming", "tracing", "network", "full"]`
  - `services/user` -> `profiles: ["user", "db", "streaming", "tracing", "network", "full"]`

---

## 4. Operational Commands & Verification

### Running Targeted Sub-Stacks
To launch a specific service sub-stack with its isolated profile:

```bash
# Auth Stack
docker compose -f services/auth/docker-compose.yml --profile auth up -d

# Audit Stack
docker compose -f services/audit/docker-compose.yml --profile audit up -d

# Notification Stack
docker compose -f services/notifications/docker-compose.yml --profile notifications up -d

# Payment Stack
docker compose -f services/payment/docker-compose.yml --profile payment up -d

# Storage Stack
docker compose -f services/storage/docker-compose.yml --profile storage up -d

# User Stack
docker compose -f services/user/docker-compose.yml --profile user up -d
```

### Deploy Script Integration
Each service directory's `scripts/deploy.sh` script passes `--profile <service>` directly:
```bash
bash services/auth/scripts/deploy.sh status
bash services/auth/scripts/deploy.sh health
```

---

## 5. Status & Validation

All 6 service sub-stack Compose files and deployment scripts have been updated and validated against Docker Compose profile commands and health diagnostics with 100% check pass rates.
