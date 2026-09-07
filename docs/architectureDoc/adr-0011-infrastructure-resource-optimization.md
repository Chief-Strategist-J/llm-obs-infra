# ADR-0011: Infrastructure Resource Optimization — Memory Bounding, Retention Tuning & Configuration Hardening

| Field | Value |
|---|---|
| **Document ID** | ADR-0011 |
| **Status** | Proposed |
| **Author(s)** | Principal Infrastructure Architect |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-07 |
| **Version** | 1.0.0 |

---

## 1. Executive Summary

The current `docker-compose.yml` stack deploys 10 services with a mix of hard memory limits and completely unbounded containers. A cross-reference of each service against its official vendor documentation reveals:

- **2 critical bugs** that cause silent misconfiguration or incorrect behavior today.
- **3 services whose memory limits were set incorrectly** in earlier analysis (they are correct as-is).
- **5 services with zero Docker memory limits**, leaving them able to consume all 15 GB of host RAM unchecked.
- **Configuration gaps** in ClickHouse, Kafka, AlloyDB, Redis, and the OTel Collector that cause unnecessary disk bloat, concurrency spikes, and OOM risk.

This ADR formalises the decisions made, the rejected proposals, and the evidence base for each.

---

## 2. Context

### 2.1 Host Environment

| Resource | Value |
|---|---|
| RAM | 15 GB (available 8.7 GB) |
| Disk (`/dev/sda2`) | 234 GB (65 GB free / 71% used) |
| CPUs | 4 cores |
| OS | Linux (Ubuntu) |

### 2.2 Current Stack Ceiling

| Service | Current Docker Limit | Current Reservation |
|---|---|---|
| `llmobs-kafka` | 2048M | 512M |
| `llmobs-clickhouse` | 4096M | 1024M |
| `llmobs-alloydb` | 2048M | 512M |
| `llmobs-otel-collector` | 1536M | 256M |
| `llmobs-temporal` | **None (Unbounded)** | None |
| `llmobs-tempo` | **None (Unbounded)** | None |
| `llmobs-grafana` | **None (Unbounded)** | None |
| `llmobs-traefik` | **None (Unbounded)** | None |
| `llmobs-service-registry` | **None (Unbounded)** | None |
| `llmobs-redis` | **None (Unbounded, only redis.conf maxmemory)** | None |

Five services have no Docker memory limit. Any one of them can trigger the Linux OOM Killer against the entire host.

---

## 3. Decisions

### Decision 1: Fix Kafka `KAFKA_JVM_PERFORMANCE_OPTS` → `KAFKA_HEAP_OPTS`

**Status:** Accepted

**Context:**
The current `docker-compose.yml` sets JVM heap via:
```yaml
- KAFKA_JVM_PERFORMANCE_OPTS=-Xms512m -Xmx1024m
```
`KAFKA_JVM_PERFORMANCE_OPTS` is the variable for **GC tuning flags only** (e.g. `-XX:+UseG1GC`). JVM heap sizing must be set via `KAFKA_HEAP_OPTS`. This is documented in `kafka-run-class.sh`:
```bash
exec "$JAVA" $KAFKA_HEAP_OPTS $KAFKA_JVM_PERFORMANCE_OPTS ...
```
When `KAFKA_HEAP_OPTS` is absent, `kafka-server-start.sh` forces its own default (`-Xmx1G -Xms1G`) regardless of `KAFKA_JVM_PERFORMANCE_OPTS`. The two variables are concatenated — not merged — creating an unpredictable startup state.

**Decision:** Rename `KAFKA_JVM_PERFORMANCE_OPTS` to `KAFKA_HEAP_OPTS` in `docker-compose.yml`. The heap value (`-Xms512m -Xmx1024m`) is correct and unchanged.

**Source:** [Apache Kafka kafka-server-start.sh](https://github.com/apache/kafka/blob/trunk/bin/kafka-server-start.sh)

---

### Decision 2: Fix ClickHouse Mark Cache (5 GiB Default Exceeds 4 GiB Container)

**Status:** ~~Accepted~~ — **SUPERSEDED by [ADR-0012](adr-0012-clickhouse-configuration.md)**

> The remediation is correct but the stated mechanism is not, and the proposal is incomplete
> (the image also ships a 2 GiB `uncompressed_cache_size`). Implement ADR-0012 §4.4 instead.

**Context:**
ClickHouse's `mark_cache_size` defaults to **5 GiB (5,368,709,120 bytes)**. The current container memory limit is `4096M`. The mark cache ceiling **exceeds the container ceiling**. ClickHouse silently over-allocates marks beyond the cgroup boundary, relying on the Linux page cache as an overflow buffer. Under any moderate query load, the Linux OOM Killer terminates the container (`Exit 137`).

The official ClickHouse documentation explicitly warns:
> *"Lower the size of the mark cache in config.xml (it can be set as low as 500 MB, but cannot be zero)."*

**Decision:** Add to `config/clickhouse/config.d/custom.xml`:
```xml
<mark_cache_size>536870912</mark_cache_size>        <!-- 512 MiB -->
<uncompressed_cache_size>0</uncompressed_cache_size> <!-- Disabled — rely on OS page cache -->
```

**Source:** [ClickHouse Docs — mark_cache_size](https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#mark_cache_size)

---

### Decision 3: Reduce OTel Collector Container Limit (1536M → 1024M) and Fix `limit_mib`

**Status:** Accepted (Implemented — see [ADR-0013](adr-0013-otel-collector-configuration.md))

**Context:**
The `memory_limiter` processor is set to `limit_mib: 512` inside a `1536M` container. Per official OpenTelemetry documentation, `limit_mib` must be set to **80–90% of the total memory allocated to the Collector process/container**. The Collector process consumes ~50 MiB above `limit_mib` due to Go runtime non-heap allocations.

At `1536M` container with `limit_mib: 512`, the limiter sits at 33% of the container ceiling. The soft limit (`limit_mib - spike_limit_mib` = 384 MiB) triggers backpressure far too early. The `memory_limiter` never protects at the correct boundary — the container can grow to 1.5 GB before Docker OOMs it without the limiter ever activating.

**Decision:**
- Reduce container limit to `1024M` (from 1536M).
- Set `limit_mib: 800` (80% of 1024 MiB).
- Set `spike_limit_mib: 160` (20% of 800 MiB).
- Add `GOMEMLIMIT=858993459` (80% of 1024 MiB in bytes) to cap Go heap growth independently.

**Source:** [OTel Memory Limiter README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md)

---

### Decision 4: Add Docker Memory Limits to 5 Unbounded Services

**Status:** Accepted

**Context:**
Temporal, Grafana Tempo, Grafana, Traefik, and Service Registry have no Docker memory limits. Official minimum requirements per vendor documentation:

| Service | Official Minimum | Idle RSS | Docker Limit Set | Reservation Set |
|---|---|---|---|---|
| Temporal (`auto-setup`) | 500MB–1.5GB dev stack | 240–500 MB | `1024M` | `256M` |
| Grafana Tempo (monolithic) | 512MB–1GB low-throughput dev | 200–512 MB | `1024M` | `128M` |
| Grafana | **512 MB** (official documented minimum) | 100–300 MB | `512M` | `128M` |
| Traefik | Go binary; not officially specified | 20–50 MB | `256M` | `64M` |
| Service Registry | Go binary; similar to Traefik | 10–30 MB | `128M` | `32M` |

> Note: Grafana Tempo officially recommends 4–8 GB for full monolithic mode. However, at low-throughput dev ingestion rates (< 100 spans/sec), the official getting-started documentation confirms 512 MB–1 GB is functional. The `1024M` limit is set conservatively above the minimum with room for growth.

**Sources:**
- [Grafana System Requirements](https://grafana.com/docs/grafana/latest/setup-grafana/installation/system-requirements/)
- [Temporal Self-Hosted Guide](https://docs.temporal.io/self-hosted-guide)
- [Grafana Tempo Requirements](https://grafana.com/docs/tempo/latest/operations/requirements/)

---

### Decision 5: Add Redis Docker Container Limit (512M) and Explicit AOF Settings

**Status:** Accepted

**Context:**
`redis.conf` sets `maxmemory 256mb` but there is no Docker container memory limit. Redis AOF background rewrites use `fork()` + copy-on-write (COW). During a rewrite, memory usage can temporarily spike to **2× the in-memory dataset size**. Without a container ceiling, this spike is unconstrained on the host.

The Redis documentation rule of thumb: set the Docker container limit to at least **2× `maxmemory`** to give AOF fork headroom.

Additionally, `auto-aof-rewrite-percentage` and `auto-aof-rewrite-min-size` are not declared in `redis.conf`. While the defaults (100%, 64MB) are correct, they must be explicitly declared to prevent silent changes across Redis version upgrades. Redis 7 also introduces `maxmemory-clients` to cap client output buffers.

**Decision:**
- Add `deploy.resources.limits.memory: 512M` and `reservations.memory: 64M` to `llmobs-redis` in `docker-compose.yml`.
- Add the following to `config/redis/redis.conf`:
  ```conf
  auto-aof-rewrite-percentage 100
  auto-aof-rewrite-min-size 64mb
  maxmemory-clients 5%
  ```

**Source:** [Redis Memory Optimization](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/memory-optimization/), [Redis Persistence Docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

---

### Decision 6: Tune Kafka Log Retention and Segment Size

**Status:** Accepted

**Context:**
Default Kafka settings: `log.retention.hours=168` (7 days), `log.segment.bytes=1073741824` (1 GB).

A critical behaviour of Kafka: **retention applies only to closed (inactive) segments**. Active segments are never deleted. On a low-traffic dev stack, a 1 GB active segment may never fill — meaning test data is never purged and `__consumer_offsets` (50 partitions by default) creates up to 50 open 1 GB reservation files per topic.

**Decision:** Add to `config/kafka/server.properties`:
```properties
log.segment.bytes=104857600       # 100 MB per segment (was: 1 GB)
log.retention.hours=24            # 1 day retention (was: 7 days)
log.roll.hours=2                  # Force segment roll every 2h even if not full
log.retention.check.interval.ms=60000  # Check every 60s (was: 5 min)
offsets.topic.num.partitions=3    # Reduce from 50 (each creates its own segment file)
```

**Source:** [Apache Kafka Broker Configs](https://kafka.apache.org/documentation/#brokerconfigs_log.segment.bytes)

---

### Decision 7: Reduce ClickHouse Concurrency Limits and Add Per-Query Memory Cap

**Status:** ~~Accepted~~ — **SUPERSEDED by [ADR-0012](adr-0012-clickhouse-configuration.md)**

> Do **not** create `users.d/dev-limits.xml`: `users.d/override.xml` already sets
> `max_memory_usage=2147483648`. `max_concurrent_queries=16` without `queue_max_wait_ms`
> turns burst load into immediate errors. Implement ADR-0012 §5 instead.

**Context:**
`max_connections=1024` and `max_concurrent_queries=100`. In ClickHouse, a single query can spawn parallel threads across all available CPU cores and allocate hundreds of megabytes to gigabytes. 100 concurrent queries on a 4-CPU machine means each query competes for the same 4 cores with potential for extreme memory amplification.

**Decision:**
- In `config/clickhouse/config.d/custom.xml`:
  ```xml
  <max_connections>512</max_connections>
  <max_concurrent_queries>16</max_concurrent_queries>
  ```
- Create `config/clickhouse/users.d/dev-limits.xml`:
  ```xml
  <clickhouse>
    <profiles>
      <default>
        <max_memory_usage>2147483648</max_memory_usage>
        <max_bytes_before_external_group_by>1073741824</max_bytes_before_external_group_by>
        <max_bytes_before_external_sort>1073741824</max_bytes_before_external_sort>
        <queue_max_wait_ms>3000</queue_max_wait_ms>
      </default>
    </profiles>
  </clickhouse>
  ```

**Source:** [ClickHouse max_concurrent_queries](https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#max_concurrent_queries)

---

### Decision 8: Reduce AlloyDB `max_connections` and `work_mem`

**Status:** Accepted

**Context:**
`max_connections=200`. Each PostgreSQL connection spawns an independent backend process. In a dev environment, realistic active connections are ~10–20 (ORM pool + psql CLI + background workers). `work_mem=16MB` is applied per operation per query — not per session. A query with multiple sorts and hash joins can allocate several multiples of `work_mem`. The PostgreSQL default is 4MB.

**Decision:** In `config/alloydb/postgresql.conf`:
```ini
max_connections = 60     # was: 200
work_mem = 8MB           # was: 16MB
```

> The **2048M Docker container limit is unchanged**. Google AlloyDB Omni documentation specifies 2 GB as the hard minimum requirement. Reducing below 2048M causes AlloyDB Omni to fail to start.

**Source:** [PostgreSQL 15 Connection Settings](https://www.postgresql.org/docs/15/runtime-config-connection.html), [AlloyDB Omni Install Docs](https://cloud.google.com/alloydb/docs/omni/install-containers)

---

### Decision 9: Reduce Docker json-file Log Caps

**Status:** Accepted

**Context:**
`default-logging` allows 50 MB × 3 files = **150 MB per container**. With 9 containers on default logging, the theoretical log ceiling is **1.35 GB** of container log files on disk. `audit-logging` allows 100 MB × 10 files = **1 GB** for AlloyDB alone. The Docker documentation's own `daemon.json` example uses `max-size: "10m"` and `max-file: "3"` as the canonical recommendation.

**Decision:** In `docker-compose.yml`:
```yaml
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"    # was: 50m
    max-file: "3"

x-audit-logging: &audit-logging
  driver: "json-file"
  options:
    max-size: "20m"    # was: 100m
    max-file: "5"      # was: 10
```

**Source:** [Docker json-file Logging Driver](https://docs.docker.com/engine/logging/drivers/json-file/)

---

## 4. Rejected Proposals

The following changes were initially proposed but are **rejected** based on official documentation research:

### Rejected: Reduce Kafka Container Limit Below 2048M

**Rejected.** The official Kafka startup script defaults to `-Xmx1G`. The Docker container limit must be at least **JVM Xmx + 512MB–1GB** to account for non-heap memory (Metaspace, thread stacks, NIO direct buffers). With `-Xmx1024m`, the minimum safe container is 1536M–2048M. Current `2048M` is correct.

**Source:** [Confluent System Requirements](https://docs.confluent.io/platform/current/installation/system-requirements.html)

---

### Rejected: Reduce ClickHouse Container Below 4096M

**Rejected.** ClickHouse officially documents:
> *"If you use less than 16 GB of RAM, you may encounter various memory exceptions because default settings are not optimized for such low memory environments."*

A 4 GB Docker container is already an aggressive constraint for ClickHouse on a 16 GB host. The current `4096M` is the practical minimum.

**Source:** [ClickHouse Operational Tips](https://clickhouse.com/docs/en/operations/tips)

---

### Rejected: Reduce AlloyDB Container Below 2048M

**Rejected.** Google AlloyDB Omni's official installation documentation lists **2 GB of RAM** as the hard minimum hardware requirement. The container will fail to start below this threshold.

**Source:** [AlloyDB Omni Install Docs](https://cloud.google.com/alloydb/docs/omni/install-containers)

---

### Rejected: Tighten Healthcheck Intervals

**Rejected.** Current healthcheck intervals range from `3s` to `10s`. Per Docker official documentation, intervals of `3s`–`5s` are **appropriate for development environments** as they speed up container boot validation. Relaxing to `15s`–`30s` is only recommended for production.

**Source:** [Dockerfile HEALTHCHECK Reference](https://docs.docker.com/reference/dockerfile/#healthcheck)

---

## 5. Consequences

### Positive

- Two critical misconfigurations (ClickHouse mark cache, Kafka env variable) are remediated with zero service downtime.
- All 10 services now have Docker memory ceilings, preventing a single rogue container from OOM-killing the host.
- Kafka log disk usage is bounded to 24 hours of data with 100 MB segment rolls.
- ClickHouse is protected against concurrent query memory explosion via per-query caps and disk-spill settings.
- OTel Collector `memory_limiter` now triggers at the correct threshold (80% of container, not 33%).
- Docker log disk ceiling reduced from ~2.35 GB (theoretical max) to ~340 MB (theoretical max).

### Negative / Trade-offs

- **Grafana Tempo** at `1024M` is below the official recommended 4–8 GB for full monolithic mode. Must be increased before any load testing or high-ingestion scenario.
- **AlloyDB** at `2048M` remains at Google's documented hard minimum. No headroom for Columnar Engine or AlloyDB AI features (those require 8 GB per vCPU).
- **ClickHouse `max_concurrent_queries=16`** may require tuning upward if integration tests issue high volumes of parallel analytical queries.

---

## 6. Compliance Checklist

| # | Change | File(s) Affected | Status |
|---|---|---|---|
| 1 | Fix `KAFKA_JVM_PERFORMANCE_OPTS` → `KAFKA_HEAP_OPTS` | `docker-compose.yml` | ⬜ Pending |
| 2 | Add ClickHouse `mark_cache_size=512MiB` | `config/clickhouse/config.d/custom.xml` | ✅ Superseded by ADR-0012 |
| 3 | Fix OTel Collector container limit + `limit_mib` ratio | `docker-compose.yml`, `config/otel-collector/otel-collector-config.yaml` | ✅ Implemented (see [ADR-0013](adr-0013-otel-collector-configuration.md)) |
| 4 | Add Docker limits to Temporal, Tempo, Grafana, Traefik, Registry | `docker-compose.yml` | ⬜ Pending |
| 5 | Add Redis Docker container limit (512M) | `docker-compose.yml` | ⬜ Pending |
| 6 | Explicit Redis AOF settings + `maxmemory-clients` | `config/redis/redis.conf` | ⬜ Pending |
| 7 | Kafka log retention + segment size tuning | `config/kafka/server.properties` | ⬜ Pending |
| 8 | ClickHouse concurrency limits (do **not** create `dev-limits.xml`) | `config/clickhouse/config.d/custom.xml`, `config/clickhouse/users.d/override.xml` | ✅ Superseded by ADR-0012 |
| 9 | AlloyDB `max_connections=60`, `work_mem=8MB` | `config/alloydb/postgresql.conf` | ⬜ Pending |
| 10 | Docker log caps: `default 50m→10m`, `audit 100m→20m` | `docker-compose.yml` | ⬜ Pending |

---

## 7. References

| Document | URL |
|---|---|
| Apache Kafka kafka-server-start.sh | https://github.com/apache/kafka/blob/trunk/bin/kafka-server-start.sh |
| Apache Kafka Broker Configs | https://kafka.apache.org/documentation/#brokerconfigs |
| Confluent Platform System Requirements | https://docs.confluent.io/platform/current/installation/system-requirements.html |
| ClickHouse Operational Tips | https://clickhouse.com/docs/en/operations/tips |
| ClickHouse mark_cache_size | https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#mark_cache_size |
| ClickHouse max_concurrent_queries | https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#max_concurrent_queries |
| Google AlloyDB Omni Requirements | https://cloud.google.com/alloydb/docs/omni/install-containers |
| PostgreSQL 15 Resource Configuration | https://www.postgresql.org/docs/15/runtime-config-resource.html |
| OpenTelemetry Memory Limiter Processor | https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md |
| Temporal Self-Hosted Guide | https://docs.temporal.io/self-hosted-guide |
| Grafana Minimum System Requirements | https://grafana.com/docs/grafana/latest/setup-grafana/installation/system-requirements/ |
| Grafana Tempo Resource Requirements | https://grafana.com/docs/tempo/latest/operations/requirements/ |
| Docker json-file Logging Driver | https://docs.docker.com/engine/logging/drivers/json-file/ |
| Docker HEALTHCHECK Reference | https://docs.docker.com/reference/dockerfile/#healthcheck |
| Redis Memory Optimization | https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/memory-optimization/ |
| Redis Persistence (AOF) Docs | https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/ |
