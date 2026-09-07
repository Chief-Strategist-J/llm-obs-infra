# Apache Kafka Configuration & Operational Reference Guide

## 1. Overview & Role in `llm-obs-infra`

Apache Kafka serves as the high-throughput, fault-tolerant event bus for the `llm-obs-infra` observability stack. It buffers incoming telemetry, traces, and metrics before ingestion into analytics engines like ClickHouse and processing pipelines like OpenTelemetry Collector and Temporal.

Because Kafka manages both in-memory page caching and persistent log segments on disk, improper configuration can lead to host RAM exhaustion, disk bloat from unpurged segments, or unpredictable JVM garbage collection pauses. This guide details each Kafka configuration parameter used in `llm-obs-infra`, explaining its mechanics, current system impact, and scaling procedures.

---

## 2. Configuration Breakdown & Operational Analysis

### 2.1 JVM Heap Sizing (`KAFKA_HEAP_OPTS`)

* **Configuration Key**: `KAFKA_HEAP_OPTS`
* **File Location**: [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml) (Environment variable)
* **Current Value**: `-Xms512m -Xmx1024m` *(Dev/Base)* | `-Xms1024m -Xmx2048m` *(Prod)*

#### What It Does
Controls the Java Virtual Machine (JVM) initial (`-Xms`) and maximum (`-Xmx`) memory allocated strictly to Java heap objects (broker metadata, active request objects, buffer pools).

#### Why We Configured It
Previously, `KAFKA_JVM_PERFORMANCE_OPTS` was used in `docker-compose.yml`. In Apache Kafka startup scripts (`kafka-run-class.sh`), `KAFKA_JVM_PERFORMANCE_OPTS` is meant strictly for JVM garbage collection tuning flags (e.g., `-XX:+UseG1GC`). Heap options specified inside performance flags are ignored or concatenated, causing Kafka to default to internal script defaults (`-Xmx1G -Xms1G`). Switching to `KAFKA_HEAP_OPTS` ensures predictable JVM heap allocation.

#### Impact on Current System
* Keeps heap memory bounded between **512 MB** and **1024 MB**.
* Prevents unpredictable startup behavior and limits GC overhead to predictable cycles.
* Leaves remaining container memory (~1 GB out of 2 GB limit) for off-heap allocations, thread stacks, Metaspace, and OS page cache.

#### How & Why to Scale / Increase
* **When to increase**: When Kafka logs `java.lang.OutOfMemoryError: Java heap space` or when request queue latency spikes due to high concurrent client connections / large batch sizes.
* **How to increase**: Update the `KAFKA_HEAP_OPTS` environment variable in [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml) or [`docker-compose.prod.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.prod.yml):
  ```yaml
  - KAFKA_HEAP_OPTS=-Xms2048m -Xmx4096m
  ```
* **Hardware Warning**: When increasing `-Xmx4096m`, raise the Docker container memory limit (`limits.memory`) to at least **5120M - 6144M** to prevent OOM Killer termination.

---

### 2.2 Docker Container Memory Boundaries

* **Configuration Keys**: `deploy.resources.limits.memory` & `reservations.memory`
* **File Location**: [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml)
* **Current Value**: Limit: `2048M` | Reservation: `512M`

#### What It Does
Imposes cgroup boundaries on the Kafka container via Docker / Linux kernel engine. The limit guarantees the container cannot exceed 2 GB of physical RAM; reservation guarantees 512 MB is provisioned by the host scheduler.

#### Why We Configured It
Unbounded container memory exposes the host (15 GB total RAM) to catastrophic Linux OOM Killer invocations. Kafka requires native memory outside the JVM heap for direct ByteBuffers, thread stacks, network socket buffers, and internal native libraries.

#### Impact on Current System
* Bounds maximum container RAM to **2048 MB**.
* Protects surrounding containers (`clickhouse`, `alloydb`, `temporal`) from host memory starvation.

#### How & Why to Scale / Increase
* **When to increase**: When scaling JVM Heap (`-Xmx`) above 1 GB, or when high socket connections require larger kernel buffer memory.
* **Calculation Formula**: `Container Limit = JVM Max Heap (Xmx) + 1 GB (Off-Heap / OS Buffers)`.

---

### 2.3 Log Segment Size (`log.segment.bytes`)

* **Configuration Key**: `log.segment.bytes`
* **File Location**: [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `104857600` (100 MB) *(Default was 1073741824 / 1 GB)*

#### What It Does
Defines the maximum byte size of an individual log segment file (`.log`) on disk. When a segment reaches this size, Kafka closes it and rolls a new active segment file.

#### Why We Configured It
**Retention in Kafka applies ONLY to closed (inactive) segments. Active log segments are NEVER deleted.**
Under default 1 GB settings, low-traffic topics or staging environments may take weeks to write 1 GB of data. Until 1 GB is reached, the segment remains active, and old telemetry data is never purged by time-based retention rules, causing disk bloat.

#### Impact on Current System
* Closes segments faster (at 100 MB boundaries), enabling time-based retention to purge old telemetry routinely.
* Prevents small/dev environments from holding gigabytes of un-purged active logs on disk.

#### How & Why to Scale / Increase
* **When to increase**: In high-throughput production (> 50,000 msgs/sec), small segment files cause excessive open file descriptors and disk index fragmentation.
* **How to increase**: Modify [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties):
  ```properties
  log.segment.bytes=536870912 # 512 MB for high throughput
  ```

---

### 2.4 Log Retention Duration (`log.retention.hours`)

* **Configuration Key**: `log.retention.hours`
* **File Location**: [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `24` (24 Hours) *(Default was 168 / 7 Days)*

#### What It Does
Determines how long Kafka retains closed log segments before deleting them from the filesystem.

#### Why We Configured It
Telemetry and trace data in `llm-obs-infra` are ingested in near-real-time by OpenTelemetry collectors and ClickHouse. Keeping 7 days of raw stream logs in Kafka duplicates data already stored in ClickHouse analytics databases, consuming unnecessary storage on host disk (`/dev/sda2`).

#### Impact on Current System
* Bounces log lifetime down to **24 hours**.
* Saves tens of gigabytes of disk space on host disk while maintaining a safe buffer for ingestion delays or consumer downtime.

#### How & Why to Scale / Increase
* **When to increase**: If consumer services (e.g., ClickHouse ingestion, temporal workflows) experience multi-day downtime and require replaying messages older than 24 hours.
* **How to increase**: Adjust [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties):
  ```properties
  log.retention.hours=72 # 3 days retention
  ```

---

### 2.5 Log Segment Roll Interval (`log.roll.hours`)

* **Configuration Key**: `log.roll.hours`
* **File Location**: [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `2` (2 Hours)

#### What It Does
Forces Kafka to roll and close an active log segment after the specified duration, even if the segment has not reached `log.segment.bytes` size.

#### Why We Configured It
In low-throughput topics (e.g., control plane messages or low-frequency telemetry), a 100 MB segment might still take days to fill. `log.roll.hours=2` guarantees that inactive topics close their active segments every 2 hours, ensuring the 24-hour retention cleaner can delete them on schedule.

#### Impact on Current System
* Prevents dormant topics from holding active un-deletable log files indefinitely.
* Smooths out disk usage and log cleanup cycles.

#### How & Why to Scale / Increase
* **When to increase**: If topic throughput is high and continuous, explicit time-based rolling is unnecessary because size-based rolling (`log.segment.bytes`) triggers regularly.
* **How to increase**: Set `log.roll.hours=24` or rely on `log.segment.bytes`.

---

### 2.6 Retention Check Interval (`log.retention.check.interval.ms`)

* **Configuration Key**: `log.retention.check.interval.ms`
* **File Location**: [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `60000` (60 Seconds) *(Default was 300000 / 5 Minutes)*

#### What It Does
Controls how frequently the log cleaner thread checks if any closed log segments are eligible for deletion based on retention time.

#### Why We Configured It
Reduces the delay between a segment expiring (passing the 24-hour mark) and its physical deletion from disk, leading to faster disk space reclamation.

#### Impact on Current System
* Provides near-immediate disk space recovery after segment expiration with negligible CPU cost.

---

### 2.7 Consumer Offsets Partition Count (`offsets.topic.num.partitions`)

* **Configuration Key**: `offsets.topic.num.partitions`
* **File Location**: [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `3` *(Default was 50)*

#### What It Does
Specifies the number of partitions for Kafka's internal `__consumer_offsets` topic, which stores consumer group commit progress.

#### Why We Configured It
By default, Kafka creates **50 partitions** for `__consumer_offsets`. Each partition creates its own folder and active log segment files. On single-node or lightweight infrastructure, 50 partitions pre-allocate 50 open segment files and index structures, creating unnecessary file descriptor and filesystem overhead.

#### Impact on Current System
* Reduces internal offset topic overhead from 50 partitions down to **3 partitions**.
* Saves 47 directory folders and open file handles on disk.

#### How & Why to Scale / Increase
* **When to increase**: In large production clusters with hundreds of distinct consumer groups, increasing offset topic partitions prevents consumer commit lock contention across consumer groups.
* **How to increase**: Set `offsets.topic.num.partitions=25` or `50` in production cluster configuration before initial broker initialization.

---

### 2.8 Default Partition Count (`num.partitions`)

* **Configuration Key**: `num.partitions` / `KAFKA_NUM_PARTITIONS`
* **File Location**: [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml) & [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties)
* **Current Value**: `3`

#### What It Does
Sets the default number of log partitions created for auto-created topics.

#### Why We Configured It
Allows parallel message processing across consumer group members while matching current 4-core host CPU resources.

#### Impact on Current System
* Provides 3-way parallelism for topic processing, matching available CPU resources efficiently without excessive context switching.

---

## 3. Configuration Summary Matrix

| Parameter | Dev / Base Value | Prod Override | Default Kafka Value | Impact / Primary Benefit |
|---|---|---|---|---|
| `KAFKA_HEAP_OPTS` | `-Xms512m -Xmx1024m` | `-Xms1024m -Xmx2048m` | `-Xms1G -Xmx1G` | Bounds JVM heap, fixes env var mismatch |
| Container Memory Limit | `2048M` | `2048M` | Unbounded | Prevents container OOM host crashes |
| `log.segment.bytes` | `104857600` (100 MB) | `536870912` (512 MB) | `1 GB` | Forces faster segment closure for purging |
| `log.retention.hours` | `24` (1 Day) | `72` (3 Days) | `168` (7 Days) | Reclaims host disk space |
| `log.roll.hours` | `2` (2 Hours) | `12` (12 Hours) | `168` (7 Days) | Enforces retention on low-throughput topics |
| `log.retention.check.interval.ms` | `60000` (1 Min) | `60000` (1 Min) | `300000` (5 Min) | Faster disk recovery after expiration |
| `offsets.topic.num.partitions` | `3` | `25` | `50` | Reduces file descriptor & folder bloat |
