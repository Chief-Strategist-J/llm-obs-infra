# ADR-0015: Profile-Driven Modular Infrastructure Execution and Targeted Health Verification

| Field | Value |
|---|---|
| **Document ID** | ADR-0015 |
| **Status** | **Accepted (Implemented)** |
| **Author(s)** | Principal Infrastructure Architect |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-10 |
| **Version** | 1.0.0 |
| **Scope** | Docker Compose Profiles (`docker-compose.yml`), Profile Resolver (`profile-resolver.sh`), Targeted Health checks (`targeted-health.sh`), Endpoint Reporter (`endpoint-reporter.sh`), Management CLI (`manage.sh`) |
| **Validated against** | Docker Engine 24.0+, Docker Compose v2.20+, OpenTelemetry v0.100.0+ |

---

## 1. Executive Summary

This Architecture Decision Record (ADR) formalizes the design, profile topology, dependency resolution algorithms, and targeted verification routines implemented for selective infrastructure execution in `llm-obs-infra`:

1. **Profile Taxonomy (`db`, `analytics`, `streaming`, `workflows`, `tracing`, `network`, `full`)**: Deconstructs the 10-container platform into 6 independent operational profiles, enabling developers to run sub-stacks without spinning up unneeded containers.
2. **Optional Telemetry Bindings (`required: false`)**: Annotates cross-profile OpenTelemetry `depends_on` bindings with `required: false` so standalone profiles (e.g. `workflows` or `network`) operate without forcing telemetry stack containers (`llmobs-otel-collector`, `llmobs-tempo`) to start.
3. **Single Responsibility Principle (SRP) Modular Script Architecture**: Decouples orchestration logic into single-purpose shell modules: `profile-resolver.sh` (dependency resolution & menu prompt), `targeted-health.sh` (selective container readiness), and `endpoint-reporter.sh` (terminal configuration reporting).
4. **Automatic Inter-Profile Dependency Resolution**: Guarantees that high-level workflows (such as `llmobs-temporal`) automatically pull in base data dependencies (`llmobs-alloydb`) to prevent container execution failures.
5. **Interactive Stack Selection Menu**: Provides an interactive terminal prompt when `./scripts/manage.sh up` is launched in a TTY environment without CLI parameters, while preserving 100% backward compatibility for full stack execution in non-interactive/CI environments.
6. **Targeted Dynamic Health Verification**: Replaces monolithic health assertion loops with targeted verification running strictly against active services in the selected profile set, marking unselected services as `[SKIP]`.

---

## 2. Context and Problem Statement

The `llm-obs-infra` platform consists of 10 microservice containers: `llmobs-alloydb`, `llmobs-redis`, `llmobs-clickhouse`, `llmobs-kafka`, `llmobs-tempo`, `llmobs-otel-collector`, `llmobs-grafana`, `llmobs-traefik`, `llmobs-temporal`, and `llmobs-service-registry`.

Prior to this architecture decision:
1. **High Memory Overhead**: Running `./scripts/manage.sh up` spawned all 10 containers simultaneously, consuming ~6–8 GB of RAM and 4 CPU cores even when a developer only required PostgreSQL (`AlloyDB`) or Kafka for feature development.
2. **Brittle Cross-Service Dependencies**: High-level engines like `Temporal` or `Service Registry` hard-blocked on `llmobs-otel-collector` being present, causing standalone execution attempts to fail.
3. **Monolithic Health Assertions**: Diagnostic scripts (`test-health.sh`) asserted readiness across all 10 containers. Starting a subset of services produced false-positive `[FAIL]` reports for stopped containers.
4. **Configuration Obscurity**: Developers lacked immediate visibility into active connection strings, ports, and Web UI URLs matching the specific containers launched.

---

## 3. Architecture Decisions

### 3.1 Service Profile Taxonomy & Docker Compose Tags

Every service definition in `docker-compose.yml` is annotated with Docker Compose `profiles:` arrays. Every container retains `"full"` to preserve unified full-stack execution:

| Profile Name | Target Services | RAM Allocation Range | Operational Scope |
|---|---|---|---|
| **`db`** | `llmobs-alloydb`, `llmobs-redis` | ~600 MB – 2.0 GB | Relational data persistence & micro-USD spend ledger |
| **`analytics`** | `llmobs-clickhouse` | ~500 MB – 2.0 GB | Columnar telemetry span queries & OLAP aggregations |
| **`streaming`** | `llmobs-kafka` | ~500 MB – 1.0 GB | Real-time event bus & topic partitioning |
| **`workflows`** | `llmobs-temporal`, `llmobs-alloydb` | ~800 MB – 2.5 GB | Durable workflow saga orchestration (+ auto-included `AlloyDB`) |
| **`tracing`** | `llmobs-tempo`, `llmobs-otel-collector`, `llmobs-grafana` | ~400 MB – 800 MB | OpenTelemetry collection, Tempo waterfalls, Grafana UI |
| **`network`** | `llmobs-traefik`, `llmobs-service-registry` | ~100 MB – 200 MB | Traefik SSL reverse proxy & dynamic service discovery |
| **`full`** | All 10 platform services | ~6.0 GB – 8.0 GB | Unified platform production & end-to-end integration |

### 3.2 Optional Telemetry Dependency Declaration (`required: false`)

To allow services with OpenTelemetry exporters (`llmobs-temporal`, `llmobs-service-registry`) to run standalone without forcing the telemetry stack to spin up, `depends_on` bindings for `llmobs-otel-collector` are declared with `required: false`:

```yaml
  llmobs-temporal:
    image: temporalio/auto-setup:1.24.2
    profiles: ["workflows", "full"]
    depends_on:
      llmobs-alloydb:
        condition: service_started
      llmobs-otel-collector:
        condition: service_started
        required: false
```

### 3.3 Dynamic Profile Resolver (`scripts/orchestrator/profile-resolver.sh`)

The `profile-resolver.sh` module parses user CLI inputs and interactive menu selections into explicit Compose `--profile` arguments and target container names:

1. **Interactive Prompt**: In TTY mode without flags, displays an interactive 8-option menu (`[1] Full`, `[2] Database`, `[3] Analytics`, `[4] Streaming`, `[5] Workflows`, `[6] Tracing`, `[7] Gateway`, `[8] Custom`).
2. **Logical Dependency Auto-Resolution**: When `workflows` is selected, the resolver automatically appends `--profile db` (`llmobs-alloydb`), ensuring Temporal's PostgreSQL database prerequisite is initialized without manual intervention.

### 3.4 Targeted Health Check Module (`scripts/orchestrator/targeted-health.sh`)

`targeted-health.sh` maps Compose service names to runtime container names (`llmobs-alloydb` → `llmobs-alloydb-db`, `llmobs-redis` → `llmobs-redis-ledger`, etc.) and executes protocol-specific health checks (`pg_isready`, `redis-cli ping`, ClickHouse HTTP `/ping`, Traefik sockets) strictly against active services in the selected profile set. Stopped containers are ignored.

### 3.5 Dynamic Endpoint Reporter (`scripts/orchestrator/endpoint-reporter.sh`)

`endpoint-reporter.sh` parses `.env` environment overrides (or default fallbacks) and formats active connection URLs and UI endpoints directly in terminal output:

```text
=====================================================
  Active Services & Configurations                   
=====================================================
  • AlloyDB (PostgreSQL): postgresql://admin:***@localhost:31420/llm_observability
  • Redis Ledger:       redis://:***@localhost:31413/0
=====================================================
```

---

## 4. Consequences and Trade-offs

### Positive Consequences

1. **Significant Resource Reduction**: Running `db` or `network` consumes **~100MB – 1GB RAM**, saving up to 80% RAM compared to full stack execution.
2. **Zero Breaking Changes**: Default `./scripts/manage.sh up` calls without parameters continue to spin up all 10 containers, ensuring 100% backward compatibility for CI/CD pipelines.
3. **Instant Developer Feedback**: Outputting active connection strings immediately after startup eliminates manual port lookup.

### Managed Trade-offs

1. **Service Cross-Communication**: When running a isolated profile (e.g. `db` alone), telemetry spans emitted by local apps will not be collected unless `tracing` or `full` is active. This is expected for isolated database development.
2. **Multi-Profile Teardown**: Teardown via `./scripts/manage.sh down` executes `docker compose --profile "*" down` to ensure containers across all profiles are stopped cleanly.
