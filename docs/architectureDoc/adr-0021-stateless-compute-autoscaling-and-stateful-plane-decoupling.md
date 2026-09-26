# ADR-0021: Stateless Compute Autoscaling, Split-Brain Elimination & Stateful Plane Decoupling

| Field | Value |
|---|---|
| **Document ID** | ADR-0021 |
| **Status** | **Accepted (Implemented & Verified)** |
| **Author(s)** | Principal Infrastructure Architect & SRE Lead |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-26 |
| **Version** | 1.0.0 |
| **Scope** | `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.stateless.yml`, `docker-compose.cloudflare.yml`, `service-discovery/`, `scripts/manage.sh`, `scripts/orchestrator/profile-resolver.sh`, `scripts/orchestrator/stack-orchestration.sh` |
| **Validated Against** | Docker Engine 24.0+, Docker Compose v2.20+, Cloudflare Tunnel (cloudflared), PostgreSQL 15 / AlloyDB Omni, Apache Kafka 3.7+ (KRaft), Redis 7 Alpine |

---

## 1. Executive Summary

This Architecture Decision Record (ADR) formalizes the decoupling of the platform into two strictly separated operating planes:
1. **The Stateful Data & Messaging Plane**: The authoritative persistence and stream-processing tier (AlloyDB Omni, Kafka, Redis, ClickHouse, Tempo), running strictly on dedicated, single-source-of-truth clustered infrastructure backed by persistent disk mounts.
2. **The Stateless Compute & Ingress Edge Plane**: The horizontally scalable compute and routing tier (Traefik gateway, Cloudflare tunnel connectors, Service Registry agents, OpenTelemetry collector daemons, Temporal workers), which can scale across $N$ instances without data divergence or split-brain corruption.

Prior to this decision, deploying the platform stack across autoscaled compute nodes caused each new VM to boot its own un-replicated local PostgreSQL, Redis, and Kafka containers, corrupting transactional state and partition ordering across compute replicas (P0 Defect #2 in `TODO.md`).

---

## 2. Problem Statement & Root Cause

When Managed Instance Groups (MIGs) or autoscalers scaled the stack from 1 to 2 or more nodes, each VM instantiated the complete Compose definition:
- Node 1 ran its own local PostgreSQL on `:5432` and local Kafka broker on `:9092`.
- Node 2 ran its own local PostgreSQL on `:5432` and local Kafka broker on `:9092`.
- Ingress traffic distributed across nodes wrote to divergent local databases.
- Kafka events emitted on Node 1 were invisible to consumer workers on Node 2.
- Local Service Discovery instances only maintained visibility over local container namespaces.

---

## 3. Architecture Decisions

### 3.1 Strict Plane Separation via Compose Profiles

Every container workload in `docker-compose.yml` and `docker-compose.cloudflare.yml` is categorized under explicit profile tags:

| Plane | Workload Services | Profile Tags | Host Requirements |
|---|---|---|---|
| **Stateful Data Plane** | `llmobs-alloydb`, `llmobs-kafka`, `llmobs-redis`, `llmobs-clickhouse`, `llmobs-tempo` | `["stateful", "data"]` | Static dedicated stateful VM; persistent regional disk at `/mnt/disks/llmobs-data`. |
| **Stateless Compute Plane** | `llmobs-traefik`, `llmobs-cloudflare-tunnel`, `llmobs-otel-collector`, `llmobs-service-registry`, `llmobs-grafana`, `llmobs-temporal` | `["stateless", "compute", "edge"]` | Autoscaled ephemeral VMs ($1 \dots N$ replicas); zero local database mounts. |
| **Unified Local Dev** | All 10 services | `["full"]` | Single-box developer machine. |

### 3.2 Dynamic Configuration Injection (`docker-compose.stateless.yml`)

Autoscaling compute nodes boot with `docker-compose.stateless.yml`, which overrides connection endpoints to target the centralized authoritative host:
- `LLMOBS_PRIMARY_DATA_HOST`: Injected dynamically from private VPC DNS / internal IP.
- Stateless compute containers mount no local database volumes, ensuring zero host disk exhaustion.
- Cross-service dependencies (e.g. `llmobs-temporal` depending on `llmobs-alloydb`) are configured with `required: false` so stateless services launch independently on compute nodes.

### 3.3 Dynamic Service Discovery Host Expansion

The Service Registry engine (`service-discovery/di/providers.go`) expands environment variables with defaults during seed catalog parsing (`expandEnvWithDefaults`). In `config/service-registry/services.json`, all stateful services dynamically resolve to:
```json
"host": "${LLMOBS_PRIMARY_DATA_HOST:-localhost}"
```
This guarantees that Traefik gateways and health checkers running on autoscaled nodes route directly to the authoritative stateful plane.

### 3.4 Multi-Connector Cloudflare Ingress

Cloudflare Tunnel (`docker-compose.cloudflare.yml`) is tagged with `profiles: ["stateless", "edge"]`. In autoscaled environments, all compute nodes run `cloudflared` using the shared `TUNNEL_TOKEN`. Cloudflare's Anycast edge balances ingress across all active connectors, and each connector routes internally to its local Traefik proxy.

### 3.5 Orchestration CLI Integration (`manage.sh`)

`scripts/manage.sh` and `scripts/orchestrator/profile-resolver.sh` natively support plane-targeted deployments:
```bash
./scripts/manage.sh up stateful   # Boots authoritative datastores on primary host
./scripts/manage.sh up stateless  # Boots stateless edge/compute on autoscaled VM
./scripts/manage.sh up full       # Unified single-machine development stack
```
When `stateless` is selected, `ensure_data_storage` skips local database directory creation on compute nodes.

---

## 4. Verification & Validation

1. **Profile Syntax Validation**: Verified all 9 profiles resolve without errors:
   `db`, `analytics`, `streaming`, `workflows`, `tracing`, `network`, `stateful`, `stateless`, `full`.
2. **Stateless Isolation Assertion**: Validated that `docker compose --profile stateless config --services` outputs only the 5 stateless services and zero database/kafka containers.
3. **CI Matrix Enforcement**: Added `stateful` and `stateless` profiles to `.github/workflows/compose-profile-validation.yml`.
