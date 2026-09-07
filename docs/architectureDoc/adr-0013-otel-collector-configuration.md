# ADR-0013: OpenTelemetry Collector Configuration and Memory Protection Specification

| Field | Value |
|---|---|
| **Document ID** | ADR-0013 |
| **Status** | Accepted (implemented) |
| **Author(s)** | Principal Infrastructure Architect |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-08 |
| **Version** | 1.0.0 |
| **Scope** | OpenTelemetry Collector only (`llmobs-otel-collector`) |
| **Supersedes** | ADR-0011 Decision 3 (OTel Collector portions) |
| **Validated against** | OpenTelemetry Collector Contrib `v0.100.0+` (`otel/opentelemetry-collector-contrib:latest`) |

---

## 1. Executive Summary

This ADR formally specifies the memory architecture, ingestion protocols, sanitization pipelines, and container cgroup boundaries for the platform's OpenTelemetry Collector (`llmobs-otel-collector`).

In ADR-0011, Decision 3 identified that the Collector container had an oversized `1536M` Docker memory ceiling while its internal `memory_limiter` processor was misconfigured at `limit_mib: 512` (activating soft throttling at 384 MiB — just 25% of container RAM) without runtime heap bounds (`GOMEMLIMIT`). This caused upstream telemetry to be throttled with HTTP 429 errors while over 1 GB of container RAM sat idle, yet left the container vulnerable to kernel Out-Of-Memory (OOM) kills during sudden burst ingestion.

This ADR implements Decision 3 and formalizes the complete configuration:
1. **Container Memory Ceiling Reduced (1536M -> 1024M)**: Reclaims 512 MB of physical host RAM on the shared 15 GB instance.
2. **Go Runtime GC Boundary Enforced (`GOMEMLIMIT=858993459`)**: Sets Go heap target to 80% of 1024 MiB in bytes, preventing uncoordinated GC expansion from exceeding Docker cgroup limits.
3. **Application Memory Limiter Calibrated (`limit_mib: 800`, `spike_limit_mib: 160`)**: Establishes soft shedding at 640 MiB (62.5%) and hard shedding at 800 MiB (78.1%), leaving 224 MiB of safety buffer for off-heap buffers and network sockets.
4. **OTTL PII Sanitization**: Enforces in-flight regex redaction across trace resources, span attributes, and span events for API keys, bearer tokens, JWTs, and credentials.

---

## 2. Context and Problem Statement

`llmobs-otel-collector` acts as the central telemetry gateway for LLM interaction traces across the platform. It runs on a 15 GB / 4-core Linux host alongside Kafka, ClickHouse, AlloyDB Omni, Redis, and Temporal.

Prior to this decision, the memory architecture suffered from three key defects:
1. **Memory Underutilization and Premature Backpressure**: With `1536M` container RAM and `limit_mib: 512`, the limiter triggered soft backpressure at `512 - 128 = 384 MiB`. Upstream SDKs received `HTTP 429 Too Many Requests` or gRPC `RESOURCE_EXHAUSTED` errors when container memory was only 25% utilized.
2. **Lack of Go Runtime Heap Pacing**: Go applications dynamically double their heap size by default (`GOGC=100`). Without `GOMEMLIMIT`, rapid telemetry surges arriving between the limiter's 1-second check intervals caused heap allocations to spike past 1.5 GB before GC could run, resulting in container termination by the Linux OOM killer (`Exit 137`).
3. **Excessive Container Allocation**: Allocating 1536 MB to the Collector reduced available memory for ClickHouse and Kafka on a resource-constrained host.

---

## 3. Decision Details

### 3.1 Docker Compose Container Specification

In `docker-compose.yml`:
```yaml
  llmobs-otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: llmobs-otel-collector
    restart: unless-stopped
    logging: *default-logging
    deploy:
      resources:
        limits:
          memory: 1024M
        reservations:
          memory: 256M
    command: ["--config=/etc/otel-collector-config.yaml"]
    environment:
      - OTEL_SERVICE_NAME=llmobs-otel-collector
      - GOMEMLIMIT=858993459
    volumes:
      - ./config/otel-collector/otel-collector-config.yaml:/etc/otel-collector-config.yaml:ro
      - ./config/certs:/etc/otel-collector/certs:ro
    ports:
      - "${PORT_OTEL_HTTP:-31417}:4318"
      - "${PORT_OTEL_GRPC:-31418}:4317"
    networks:
      - llmobs-network
```

### 3.2 Memory Limiter Processor Calibration

In `config/otel-collector/otel-collector-config.yaml`:
```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 800
    spike_limit_mib: 160
```

### 3.3 Mathematical Derivation of Headroom

| Metric | Calculation | Byte Value | Percentage of Container |
|---|---|---|---|
| Container Memory Ceiling (`memory.max`) | `1024 MiB` | 1,073,741,824 bytes | 100.0% |
| Go Runtime Memory Limit (`GOMEMLIMIT`) | `80% of 1024 MiB` | 858,993,459 bytes | 80.0% |
| Application Hard Limit (`limit_mib`) | `800 MiB` | 838,860,800 bytes | 78.1% |
| Application Soft Limit (`limit_mib - spike_limit_mib`) | `800 - 160 MiB` | 671,088,640 bytes | 62.5% |
| Non-Heap Operating Safety Buffer | `1024 - 800 MiB` | 234,881,024 bytes | 21.9% |

---

## 4. Consequences

### Positive
- **Host Memory Reclaimed**: Frees 512 MB of physical host RAM for core databases.
- **Elimination of Spurious 429 Errors**: Telemetry pipelines operate unhindered up to 640 MiB before soft backpressure activates.
- **Protection Against Exit 137**: Dual enforcement by Go runtime GC (`GOMEMLIMIT`) and application load shedding (`memory_limiter`) prevents container termination under load.
- **Comprehensive Operational Documentation**: Fully documented in [`docs/configDoc/otel-collector-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/otel-collector-configuration-guide.md).

### Negative / Trade-offs
- In high-throughput environments exceeding 5,000 spans/sec, a 1024M container will engage soft load shedding. Such environments must deploy the horizontal scale-out configuration defined in `docker-compose.prod.yml` (`replicas: 2`, `2048M` limit).

---

## 5. References

- [OpenTelemetry Memory Limiter Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md)
- [Go Runtime Memory Limit Documentation (Go 1.19+)](https://go.dev/doc/gc-guide#Memory_limit)
- [ADR-0011: Infrastructure Resource Optimization](adr-0011-infrastructure-resource-optimization.md)
- [OTel Collector Configuration Guide](../configDoc/otel-collector-configuration-guide.md)
