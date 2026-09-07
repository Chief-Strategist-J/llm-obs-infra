# Apache Kafka Comprehensive Architecture, Component Deep-Dive & Operational Guide

## 1. System-Wide Kafka High-Level (HLD) & Low-Level (LLD) Design

### 1.1 System High-Level Design (HLD) — Observability Data Pipeline Architecture

In the llm-obs-infra architecture, Apache Kafka serves as an asynchronous, distributed event-streaming buffer separating high-frequency telemetry ingestion from heavy downstream analytics engines.

```mermaid
graph TD
    A1["OpenTelemetry Collectors"] -->|Stream Telemetry| B1["Traefik Load Balancer"]
    A2["Traefik Access Logs"] -->|Stream Telemetry| B1
    A3["Application SDKs"] -->|Stream Telemetry| B1

    B1 -->|Publish Spans and Metrics| C1["llmobs-kafka Broker"]

    subgraph Kafka Cluster Boundary ["llmobs-kafka Broker (cgroup 2048M Limit)"]
        C1 --> D1["JVM Heap (-Xmx1024M)"]
        C1 --> E1["Linux OS Page Cache"]
        E1 -->|Disk Log Writes| F1["Partition Log Segments (/var/lib/kafka/data)"]
    end

    F1 -->|Batch Ingest| G1["ClickHouse Analytics DB"]
    F1 -->|Workflow Events| H1["Temporal Engine"]
    F1 -->|Metrics Pull| I1["Grafana Engine"]
```

---

### 1.2 System Low-Level Design (LLD) — End-to-End Execution Flow

This diagram illustrates the complete internal mechanics of record processing from Producer client memory to Broker disk storage and Consumer fetch execution.

```mermaid
graph TB
    subgraph Producer Internals ["Producer Client Execution"]
        P_App["Application Record"] --> P_Ser["Serializer"]
        P_Ser --> P_Part["Partitioner (MurmurHash2)"]
        P_Part --> P_Buf["RecordAccumulator (32MB Buffer)"]
        P_Buf --> P_Send["Sender Thread"]
    end

    subgraph Broker Internals ["Broker Internal Execution"]
        P_Send -->|TCP Produce Request| B_Net["Acceptor and Network Threads"]
        B_Net --> B_ReqQ["Request Queue"]
        B_ReqQ --> B_Worker["KafkaRequestHandler Worker Threads"]
        B_Worker --> B_Heap["JVM Heap Metadata"]
        B_Worker --> B_PageCache["Linux OS Page Cache"]
        B_PageCache --> B_Log["Active Log Segment (.log)"]
        B_Cleaner["Log Retention Cleaner Thread"] -->|Deletes expired segments| B_ClosedLog["Closed Log Segments (.log)"]
    end

    subgraph Consumer Internals ["Consumer Client Execution"]
        B_PageCache -->|Zero-Copy sendfile| C_Fetch["Consumer Fetcher Thread"]
        C_Fetch --> C_Buf["CompletedFetch Queue"]
        C_Buf --> C_Poll["Consumer poll Loop"]
        C_Poll --> C_Commit["Offset Commit Manager (__consumer_offsets)"]
        C_Commit -->|Commit Offsets| B_Net
    end
```

---

## 2. Kafka Configuration Parameter Naming Conventions & Genesis

Kafka configuration parameters follow three distinct naming conventions depending on where and how they are defined:

```mermaid
graph LR
    P1["1. Broker Properties (server.properties)<br/>e.g. log.segment.bytes"] -->|Dot to Underscore + Uppercase + Prefix| P2["2. Environment Variables (docker-compose.yml)<br/>e.g. KAFKA_LOG_SEGMENT_BYTES"]
    P3["3. JVM Launcher Flags<br/>e.g. -Xms512m -Xmx1024m"] -->|Passed directly to java entrypoint| P2
```

### Naming Conventions Breakdown

| Convention Type | Target Environment | Formatting Pattern & Rules | Example Parameter |
|---|---|---|---|
| **1. Broker Properties** | `config/kafka/server.properties` | **Hierarchical Dot-Notation**: Grouped by functional subsystem (`log.*`, `offsets.topic.*`, `num.partitions`, `transaction.state.log.*`). | `log.segment.bytes` |
| **2. Environment Variables** | `docker-compose.yml` | **Uppercase Underscore Mapping**: Standard Confluent/Docker convention. Prepend `KAFKA_`, convert to uppercase, and replace dots (`.`) with underscores (`_`). | `KAFKA_LOG_SEGMENT_BYTES` |
| **3. JVM Launcher Options** | Container `entrypoint` / Compose `env` | **Standard Java Options**: `-Xms` (Initial Memory Size), `-Xmx` (Maximum Memory Size), and `-XX:` (Expert Garbage Collection / Metaspace options). | `KAFKA_HEAP_OPTS="-Xms512m -Xmx1024m"` |

---

## 3. Broker Architecture & Component Deep-Dive

### 3.1 Broker High-Level Design (HLD)

The broker manages network sockets, metadata coordination via KRaft consensus, memory allocation between Java Heap and Native OS Page Cache, and log segment disk storage.

```mermaid
graph TD
    Client["Producer / Consumer Clients"] -->|Port 9092| SocketListener["Network Socket Listener"]
    KRaftPeer["KRaft Controller Quorum Peers"] -->|Port 9093| ControllerListener["Controller Listener"]

    subgraph Broker Core Engine ["llmobs-kafka Broker Process"]
        SocketListener --> NetPool["Network Processing Pool"]
        ControllerListener --> KRaftEngine["KRaft Metadata Engine (@metadata)"]
        NetPool --> WorkPool["I/O Request Handler Pool"]
        WorkPool --> MemoryMgr["Memory Manager (Heap vs OS Page Cache)"]
        MemoryMgr --> LogEngine["Partition Log Storage Engine"]
    end
```

---

### 3.2 Broker Low-Level Design (LLD)

The low-level broker execution details the socket acceptor, request queues, thread pools, memory boundaries, and physical file layout on disk.

```mermaid
graph TB
    Acceptor["Acceptor Thread"] -->|NIO Select| NetThread1["Network Thread 1"]
    Acceptor -->|NIO Select| NetThread2["Network Thread 2"]

    NetThread1 -->|Push Request| RequestQueue["Request Queue"]
    NetThread2 -->|Push Request| RequestQueue

    RequestQueue -->|Pop Request| IOThread1["KafkaRequestHandler 1"]
    RequestQueue -->|Pop Request| IOThread2["KafkaRequestHandler 2"]

    subgraph Memory Architecture ["Broker Memory Architecture"]
        IOThread1 -->|Allocate Objects| JVMHeap["JVM Heap (-Xmx1024M)<br/>Broker Metadata & Request Queues"]
        IOThread1 -->|Native Buffers| NativeMem["Native Off-Heap Memory<br/>Direct ByteBuffers & Metaspace"]
        IOThread1 -->|Zero-Copy Data| PageCache["Linux OS Page Cache<br/>In-Memory Log Files"]
    end

    subgraph Storage Layout ["Physical Storage Layout (/var/lib/kafka/data)"]
        PageCache -->|Flush| LogFile["00000000000000000000.log<br/>(Message Data)"]
        PageCache -->|Flush| IndexFile["00000000000000000000.index<br/>(Offset Index)"]
        PageCache -->|Flush| TimeIndex["00000000000000000000.timeindex<br/>(Timestamp Index)"]
        PageCache -->|Flush| EpochFile["leader-epoch-checkpoint<br/>(Leader Epochs)"]
    end
```

---

### 3.3 Broker Detailed Configuration Breakdown

#### 3.3.1 `KAFKA_HEAP_OPTS` — JVM Heap Memory Sizing

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `KAFKA_HEAP_OPTS` |
| **Target Location** | [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml) (Line 115) & [`docker-compose.prod.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.prod.yml) (Line 12) |
| **Currently Configured Value** | `-Xms512m -Xmx1024m` *(Dev/Base)* \| `-Xms1024m -Xmx2048m` *(Prod)* |
| **Apache Kafka Default** | `-Xms1G -Xmx1G` |
| **Expected / Recommended Values** | Base Dev: `-Xms512m -Xmx1024m`<br/>Small Prod: `-Xms1024m -Xmx2048m`<br/>High-Throughput Prod: `-Xms4096m -Xmx4096m` |
| **Criticality Rating** | CRITICAL |
| **Definition** | Controls the initial (`-Xms`) and maximum (`-Xmx`) physical memory allocated strictly to Java Virtual Machine (JVM) heap objects (broker metadata, active request queues, partition offset indexes, consumer group coordinator state). |
| **Why & When to Configure It** | **Why Configure It**: Fixes environment variable parsing bugs in `kafka-run-class.sh` launcher scripts and keeps Java memory strictly bounded to prevent host RAM starvation.<br/>**When to Configure**: Must be set on all containerized Kafka brokers. |
| **Outcome / System Impact** | **RAM Outcome**: Restricts JVM heap to 1024MB max, leaving 1024MB off-heap headroom for Linux OS Page Cache and socket buffers.<br/>**GC Outcome**: Keeps G1GC collection pauses under 50ms on 4 CPU cores. |
| **Scaling & Troubleshooting** | **Monitoring Metrics**: `jvm_gc_pause_seconds` > 0.5s or error `java.lang.OutOfMemoryError: Java heap space`.<br/>**Scaling Rule**: `Container Limit = JVM Heap (-Xmx) + 1024MB`. |

---

#### 3.3.2 `deploy.resources.limits.memory` — Docker Container Memory Ceiling

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `deploy.resources.limits.memory` & `reservations.memory` |
| **Target Location** | [`docker-compose.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/docker-compose.yml) (Lines 94-99) |
| **Currently Configured Value** | Limit: `2048M` \| Reservation: `512M` |
| **Apache Kafka Default** | Unbounded (`None`) |
| **Expected / Recommended Values** | Base Dev: `2048M`<br/>Small Prod: `4096M`<br/>High-Throughput Prod: `8192M` |
| **Criticality Rating** | CRITICAL |
| **Definition** | Establishes hard Linux kernel `cgroups` memory boundaries around the Kafka container process. |
| **Why & When to Configure It** | **Why Configure It**: Prevents a single run-away container from consuming all host RAM and crashing adjacent services.<br/>**When to Configure**: Essential on shared multi-container hosts. |
| **Outcome / System Impact** | **Host Protection**: Guarantees Kafka cannot exceed 2 GB of physical host RAM.<br/>**Coexistence**: Preserves guaranteed memory headroom for ClickHouse (`4096M`) and AlloyDB (`2048M`). |
| **Scaling & Troubleshooting** | **Monitoring Metrics**: Container status `Exit 137` in `docker ps -a` or `dmesg \| grep -i oom`.<br/>**Scaling Rule**: `Container Limit = JVM Heap (-Xmx) + 1024M` (minimum 1 GB off-heap buffer). |

---

## 4. Producer Architecture & Component Deep-Dive

### 4.1 Producer High-Level Design (HLD)

The producer accepts records from application threads, serializes keys/values, assigns target partitions via MurmurHash2 algorithm, buffers records in memory batches, and asynchronously transmits batches to the broker.

```mermaid
graph TD
    AppThread["Application Thread<br/>send(ProducerRecord)"] --> Serializer["Key/Value Serializers"]
    Serializer --> Partitioner["Partitioner (MurmurHash2 / RoundRobin)"]
    Partitioner --> RecordAccumulator["RecordAccumulator (Memory Buffer)"]

    subgraph Background Processing ["Background I/O Thread"]
        RecordAccumulator --> SenderThread["Sender Thread"]
        SenderThread --> SocketChannel["Network Client and SocketChannel"]
    end

    SocketChannel -->|TCP Produce Request| KafkaBroker["llmobs-kafka Broker"]
```

---

### 4.2 Producer Low-Level Design (LLD)

The low-level producer design reveals batching mechanics (`batch.size`, `linger.ms`), memory buffer pools (`buffer.memory`), inflight request tracking, retry logic, and acknowledgment handling.

```mermaid
graph TB
    subgraph Producer Memory Pool ["Producer Memory Pool (buffer.memory = 32MB)"]
        BatchP0["Partition 0 Batch<br/>(batch.size = 16KB)"]
        BatchP1["Partition 1 Batch<br/>(batch.size = 16KB)"]
        BatchP2["Partition 2 Batch<br/>(batch.size = 16KB)"]
    end

    subgraph Batch Trigger Logic ["Batch Trigger Conditions"]
        Trigger1["Condition 1: Batch Size Full (16 KB)"]
        Trigger2["Condition 2: Linger Time Expired (linger.ms = 10ms)"]
    end

    BatchP0 --> Trigger1
    BatchP1 --> Trigger1
    BatchP2 --> Trigger1
    BatchP0 --> Trigger2
    BatchP1 --> Trigger2
    BatchP2 --> Trigger2

    Trigger1 --> SenderThread["Sender Thread"]
    Trigger2 --> SenderThread

    subgraph In-Flight Network Queue ["In-Flight Queue (max.in.flight.requests = 5)"]
        Req1["In-Flight Produce Request 1"]
        Req2["In-Flight Produce Request 2"]
    end

    SenderThread --> Req1
    SenderThread --> Req2
    Req1 -->|Produce Request| BrokerNode["Broker Leader Replica"]
    Req2 -->|Produce Request| BrokerNode

    BrokerNode -->|acks=all Response| AckHandler["ACK / Retry Handler"]
    AckHandler -->|Success| Complete["Complete RecordFuture"]
    AckHandler -.->|Error and Retries Available| RetryQueue["Retry Backoff (retry.backoff.ms = 100ms)"]
    RetryQueue --> SenderThread
```

---

### 4.3 Producer Detailed Configuration Breakdown

#### 4.3.1 `acks` / `KAFKA_ACKS` — Producer Acknowledgment Level

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `acks` / `KAFKA_ACKS` |
| **Target Location** | Client Producer SDK Configuration |
| **Currently Configured Value** | `all` (or `-1`) *(Prod)* \| `1` *(Dev)* |
| **Apache Kafka Default** | `all` (since Kafka 3.0) |
| **Expected / Recommended Values** | `0` (Fire & forget) \| `1` (Leader ACK) \| `all` (Full ISR Consensus) |
| **Criticality Rating** | CRITICAL |
| **Definition** | Dictates leader acknowledgment requirements before completing a produce request: `acks=0` (no ACK), `acks=1` (leader ACK only), `acks=all` (leader + all in-sync replicas ACK). |
| **Why & When to Configure It** | **Why Configure It**: Setting `acks=all` guarantees that writes are committed to all in-sync replicas before returning success, preventing message loss if the leader broker dies.<br/>**When to Configure**: Mandatory for critical telemetry, financial, and trace data. |
| **Outcome / System Impact** | **Durability Outcome**: Guarantees zero message loss during broker outages when paired with `min.insync.replicas=2`.<br/>**Latency Impact**: Adds minor round-trip latency to write operations. |
| **Scaling & Troubleshooting** | Keep `acks=all` in production. If ultra-low latency metrics tolerate minor data loss, set `acks=1`. |

---

#### 4.3.2 `linger.ms` & `batch.size` — Producer Batching Mechanics

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `linger.ms` & `batch.size` |
| **Target Location** | Client Producer SDK Configuration |
| **Currently Configured Value** | `linger.ms=10` \| `batch.size=16384` (16 KB) |
| **Apache Kafka Default** | `linger.ms=0` \| `batch.size=16384` |
| **Expected / Recommended Values** | Low-Latency: `linger.ms=0`, `batch.size=16384`<br/>High-Throughput: `linger.ms=20..50`, `batch.size=65536` |
| **Criticality Rating** | HIGH |
| **Definition** | `batch.size` sets the maximum byte size per partition batch. `linger.ms` sets the maximum artificial delay to wait for more records to join the batch before sending. |
| **Why & When to Configure It** | Default `linger.ms=0` sends records immediately, creating thousands of tiny single-record TCP requests. Setting `linger.ms=10` allows records to group into full 16KB batches, increasing network and disk throughput by up to 5x. |
| **Outcome / System Impact** | Significantly reduces network packet overhead and broker CPU utilization while increasing batch write efficiency. |
| **Scaling & Troubleshooting** | Increase `linger.ms` to 20ms–50ms and `batch.size` to 64KB (65536) under high-throughput ingestion (> 10 MB/sec). |

---

#### 4.3.3 `buffer.memory` & `max.block.ms` — Producer Memory Allocation

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `buffer.memory` & `max.block.ms` |
| **Target Location** | Client Producer SDK Configuration |
| **Currently Configured Value** | `buffer.memory=33554432` (32 MB) \| `max.block.ms=60000` (60 Seconds) |
| **Apache Kafka Default** | `buffer.memory=33554432` \| `max.block.ms=60000` |
| **Expected / Recommended Values** | Standard: `33554432` (32 MB)<br/>High-Burst: `67108864` (64 MB) or `134217728` (128 MB) |
| **Criticality Rating** | HIGH |
| **Definition** | `buffer.memory` sets total RAM available to the producer to buffer unsent batches. `max.block.ms` sets how long `send()` blocks when the buffer is full before throwing an exception. |
| **Why & When to Configure It** | Protects producer application memory from un-bounded growth during broker network outages. |
| **Outcome / System Impact** | Bounces producer memory usage to 32 MB and throws `TimeoutException` if network outages persist past 60 seconds. |
| **Scaling & Troubleshooting** | Increase `buffer.memory` to 64MB or 128MB in high-throughput applications with bursts. |

---

## 5. Consumer Architecture & Component Deep-Dive

### 5.1 Consumer High-Level Design (HLD)

Consumers join Consumer Groups coordinated by a designated Broker Group Coordinator. Partitions are distributed among group members, and records are fetched in batches using long polling.

```mermaid
graph TD
    subgraph Consumer Group ["Consumer Group (llmobs-clickhouse-ingest)"]
        C1["Consumer Thread 1"]
        C2["Consumer Thread 2"]
        C3["Consumer Thread 3"]
    end

    subgraph Broker Group Coordinator ["Broker Group Coordinator"]
        Coord["Group Coordinator Engine"]
        OffsetTopic["__consumer_offsets Topic"]
    end

    subgraph Kafka Topic Partitions ["Telemetry Topic (3 Partitions)"]
        P0["Partition 0"]
        P1["Partition 1"]
        P2["Partition 2"]
    end

    C1 -->|Fetch & Process| P0
    C2 -->|Fetch & Process| P1
    C3 -->|Fetch & Process| P2

    C1 -->|Heartbeat and Offset Commit| Coord
    C2 -->|Heartbeat and Offset Commit| Coord
    C3 -->|Heartbeat and Offset Commit| Coord
    Coord -->|Persist Offsets| OffsetTopic
```

---

### 5.2 Consumer Low-Level Design (LLD)

The low-level consumer design illustrates group join protocol (`JoinGroup`/`SyncGroup`), poll execution, batch fetch queues, manual vs automatic offset commits, and consumer rebalance mechanics.

```mermaid
graph TB
    subgraph Consumer Poll Execution ["Consumer Thread Execution Loop"]
        PollStart["consumer.poll(Duration.ofMillis(100))"] --> CheckQueue{"CompletedFetch Queue Empty?"}
        CheckQueue -- Yes --> Fetcher["Fetcher Thread sends FetchRequest"]
        CheckQueue -- No --> ConsumerRecords["Return ConsumerRecords Batch"]

        Fetcher -->|Zero-Copy TCP Read| BrokerStorage["Broker OS Page Cache"]
        BrokerStorage --> CompletedQueue["CompletedFetch Queue"]

        ConsumerRecords --> AppProcess["Process Batch (e.g. Insert into ClickHouse)"]
        AppProcess --> CommitCheck{"enable.auto.commit = false?"}
        CommitCheck -- Yes --> ManualCommit["commitSync() / commitAsync()"]
        CommitCheck -- No --> AutoCommit["Auto Commit (every 5000ms)"]
        ManualCommit --> OffsetWrite["Write to __consumer_offsets"]
        AutoCommit --> OffsetWrite
    end

    subgraph Heartbeat & Liveness Thread ["Background Heartbeat Thread"]
        HBThread["Heartbeat Thread (heartbeat.interval.ms = 3000)"] -->|Send Heartbeat| CoordNode["Group Coordinator"]
        CoordNode -->|Liveness Valid| OK["Keep Partition Assignment"]
        CoordNode -.->|Session Timeout Exceeded 45s| Dead["Mark Consumer Dead and Trigger Rebalance"]
    end
```

---

### 5.3 Consumer Detailed Configuration Breakdown

#### 5.3.1 `enable.auto.commit` & `auto.commit.interval.ms` — Offset Commit Control

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `enable.auto.commit` & `auto.commit.interval.ms` |
| **Target Location** | Client Consumer SDK Configuration |
| **Currently Configured Value** | `enable.auto.commit=false` *(Prod)* \| `true` *(Dev)* |
| **Apache Kafka Default** | `enable.auto.commit=true` \| `auto.commit.interval.ms=5000` |
| **Expected / Recommended Values** | Analytics & Pipeline DB Sinks: `false`<br/>Stateless Real-Time Alerting: `true` |
| **Criticality Rating** | CRITICAL |
| **Definition** | Controls whether consumer offsets are committed automatically in the background on a periodic timer or managed explicitly by application code. |
| **Why & When to Configure It** | Automatic commit (`true`) risks data loss if the consumer crashes after committing offsets but before completing ClickHouse database writes. Setting `false` allows manual commit after database write success (at-least-once delivery). |
| **Outcome / System Impact** | Guarantees exact telemetry delivery into ClickHouse without missing records. |
| **Scaling & Troubleshooting** | Always set `enable.auto.commit=false` in production data pipelines and call `commitSync()` / `commitAsync()`. |

---

#### 5.3.2 `max.poll.interval.ms` & `max.poll.records` — Processing Loop Liveness

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `max.poll.interval.ms` & `max.poll.records` |
| **Target Location** | Client Consumer SDK Configuration |
| **Currently Configured Value** | `max.poll.interval.ms=300000` (5 Min) \| `max.poll.records=500` |
| **Apache Kafka Default** | `max.poll.interval.ms=300000` \| `max.poll.records=500` |
| **Expected / Recommended Values** | Fast Processing: `max.poll.records=500`, `max.poll.interval.ms=300000`<br/>Heavy DB Batching: `max.poll.records=100`, `max.poll.interval.ms=600000` |
| **Criticality Rating** | HIGH |
| **Definition** | `max.poll.records` sets maximum records returned in a single `poll()`. `max.poll.interval.ms` sets maximum time allowed between `poll()` calls before the consumer is marked dead and evicted from the group. |
| **Why & When to Configure It** | If ClickHouse batch inserts take longer than 5 minutes, Kafka assumes the consumer thread is stuck and triggers constant consumer group rebalance storms. |
| **Outcome / System Impact** | Prevents rebalance storms during large ClickHouse batch ingestion operations. |
| **Scaling & Troubleshooting** | If processing high-latency batches, reduce `max.poll.records` to 100 or increase `max.poll.interval.ms` to 600,000ms (10 minutes). |

---

#### 5.3.3 `auto.offset.reset` — Offset Fallback Behavior

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `auto.offset.reset` |
| **Target Location** | Client Consumer SDK Configuration |
| **Currently Configured Value** | `earliest` *(Dev/Recovery)* \| `latest` *(Default Ingest)* |
| **Apache Kafka Default** | `latest` |
| **Expected / Recommended Values** | Telemetry Ingestion / Recovery: `earliest`<br/>Real-Time Alerting: `latest` |
| **Criticality Rating** | HIGH |
| **Definition** | Dictates consumer behavior when no initial offset exists or when offset is out of range: `earliest` (start from oldest available record), `latest` (start from newest incoming record). |
| **Why & When to Configure It** | Use `earliest` for new consumer groups that need to process historical buffered streams; use `latest` for real-time dashboard alerting. |
| **Outcome / System Impact** | Ensures new ingestion instances process all buffered streams without skipping data. |

---

## 6. Topic & Partition Management Architecture

### 6.1 Topic & Partition High-Level Design (HLD)

Topics are logical representations of event streams, physically divided into append-only log partitions distributed across brokers for horizontal scalability and high availability.

```mermaid
graph TD
    subgraph Logical Topic ["Logical Telemetry Topic (llmobs-spans)"]
        direction TB
        P0["Partition 0 (Broker 1 Leader)"]
        P1["Partition 1 (Broker 2 Leader)"]
        P2["Partition 2 (Broker 3 Leader)"]
    end

    subgraph Physical Disk Storage ["Physical Disk Directory Structure"]
        P0 --> D0["/var/lib/kafka/data/llmobs-spans-0/"]
        P1 --> D1["/var/lib/kafka/data/llmobs-spans-1/"]
        P2 --> D2["/var/lib/kafka/data/llmobs-spans-2/"]
    end
```

---

### 6.2 Topic & Partition Low-Level Design (LLD)

The low-level partition lifecycle shows log segment creation, active segment append operations, closed segment rolling, index file lookups, and log cleaner deletion execution.

```mermaid
graph TB
    subgraph Partition Directory Engine ["Partition Engine (/var/lib/kafka/data/llmobs-spans-0/)"]
        WriteOp["Produce Record Appended"] --> ActiveSegment["Active Segment: 00000000000000000200.log<br/>(Currently Appending Write)"]

        ActiveSegment --> RollCondition{"Segment Full 100MB or Time Expired 2h?"}
        RollCondition -- Yes --> CloseSegment["Close Active Segment -> Mark INACTIVE"]
        CloseSegment --> OpenNew["Open New Active Segment (.log)"]
        RollCondition -- No --> KeepWriting["Continue Appending Writes"]

        subgraph Index Lookups ["Offset and Time Index Files"]
            OffsetIndex["00000000000000000000.index<br/>(Maps Offset -> Physical Byte Position)"]
            TimeIndex["00000000000000000000.timeindex<br/>(Maps Timestamp -> Offset)"]
        end

        CloseSegment --> IndexLookups

        subgraph Log Retention Cleaner ["Log Retention Cleaner Thread"]
            CleanerScan["Retention Scan (Every 60 Seconds)"] --> RetentionCheck{"Closed Segment Age Exceeds 24 Hours?"}
            RetentionCheck -- Yes --> UnlinkFile["Unlink and Delete Segment Files"]
            RetentionCheck -- No --> RetainSegment["Retain File on Disk"]
        end

        CloseSegment --> CleanerScan
    end
```

---

### 6.3 Topic & Partition Detailed Configuration Breakdown

#### 6.3.1 `log.segment.bytes` — Partition Log Segment File Size

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `log.segment.bytes` |
| **Target Location** | [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties) (Line 15) |
| **Currently Configured Value** | `104857600` (100 MB) |
| **Apache Kafka Default** | `1073741824` (1 GB) |
| **Expected / Recommended Values** | Low/Dev: `104857600` (100 MB)<br/>Medium Prod: `268435456` (256 MB)<br/>High-Throughput Prod: `536870912` (512 MB) or `1073741824` (1 GB) |
| **Criticality Rating** | CRITICAL |
| **Definition** | Maximum byte size per partition segment file before closing and rolling a new active segment file. |
| **Why & When to Configure It** | **Retention rules apply ONLY to closed segments. Active segments are NEVER deleted regardless of age.** Setting 100 MB allows low/medium volume topics to close segments rapidly for daily deletion. |
| **Outcome / System Impact** | Reclaims ~30 GB of storage space on `/dev/sda2` by preventing inactive topics from holding onto gigabytes of un-purged active segments. |
| **Scaling & Troubleshooting** | Increase to 512MB or 1GB in high-throughput production (> 50,000 msgs/sec) to avoid excessive file handle creation. |

---

#### 6.3.2 `log.retention.hours` — Closed Log Lifetime

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `log.retention.hours` |
| **Target Location** | [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties) (Line 16) |
| **Currently Configured Value** | `24` (24 Hours / 1 Day) |
| **Apache Kafka Default** | `168` (168 Hours / 7 Days) |
| **Expected / Recommended Values** | Base Dev: `24` (24 Hours)<br/>Production Buffer: `72` (3 Days)<br/>Long-Buffer Ingest: `168` (7 Days) |
| **Criticality Rating** | HIGH |
| **Definition** | Duration in hours that closed segment files are retained on disk before physical deletion. |
| **Why & When to Configure It** | Kafka is an intermediate buffer. Telemetry data is consumed almost immediately by ClickHouse. Retaining 7 days duplicates data and consumes host storage. |
| **Outcome / System Impact** | Reclaims ~35 GB of disk space on `/dev/sda2` by deleting 1-day-old segments. |

---

#### 6.3.3 `log.roll.hours` — Time-Based Segment Rolling

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `log.roll.hours` |
| **Target Location** | [`config/kafka/server.properties`](file:///home/btpl-lap-22/live/llm-obs-infra/config/kafka/server.properties) (Line 17) |
| **Currently Configured Value** | `2` (2 Hours) |
| **Apache Kafka Default** | `168` (168 Hours / 7 Days) |
| **Expected / Recommended Values** | Low-Volume Topics: `2` (2 Hours)<br/>High-Volume Topics: `12` (12 Hours) or `24` (24 Hours) |
| **Criticality Rating** | HIGH |
| **Definition** | Maximum time window after which an active segment is forcibly closed, even if segment size is less than 100 MB. |
| **Why & When to Configure It** | Low-throughput topics take weeks to write 100 MB. Forced rolls every 2 hours guarantee active segments close and become eligible for 24-hour deletion. |
| **Outcome / System Impact** | Eliminates storage leaks on dormant or low-volume topics. |

---

## 7. Exactly-Once Semantics (EOS), Idempotency & Transactions

### 7.1 Idempotent Producer Mechanics (`enable.idempotence=true`)

When a network timeout occurs while a producer transmits a batch to the broker, the producer retries. Without idempotency, the broker accepts duplicate records.

```mermaid
graph TD
    subgraph Idempotent Producer Protocol
        P1["Producer Client (enable.idempotence=true)"] -->|1. Allocate Producer ID (PID)| B1["Broker Sequence Tracker"]
        P1 -->|2. Send Record Batch (PID: 101, Seq: 0)| B1
        B1 -->|3. Persist Batch Seq 0| S1["Partition Log"]
        B1 -.->|4. Network ACK Drops / Times Out| P1
        P1 -->|5. Retry Batch (PID: 101, Seq: 0)| B1
        B1 -->|6. Detect Duplicate Seq 0| D1["Discard Duplicate Payload & Re-ACK"]
    end
```

---

### 7.2 EOS Configuration Breakdown

#### 7.2.1 `enable.idempotence` — Producer Sequence Tracking

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `enable.idempotence` |
| **Target Location** | Client Producer SDK Configuration |
| **Currently Configured Value** | `true` |
| **Apache Kafka Default** | `true` (since Kafka 3.0) |
| **Expected / Recommended Values** | Standard: `true`<br/>Legacy/Disabled: `false` |
| **Criticality Rating** | CRITICAL |
| **Definition** | Ensures that the broker processes exactly one copy of a message batch sent by a producer, even if the producer retries due to network timeouts. |
| **Why & When to Configure It** | Eliminates duplicate records in telemetry and trace metrics pipelines caused by transient network retries. |
| **Outcome / System Impact** | Eliminates duplicate span insertions into ClickHouse. |

---

#### 7.2.2 `isolation.level` — Consumer Read Isolation

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `isolation.level` |
| **Target Location** | Client Consumer SDK Configuration |
| **Currently Configured Value** | `read_committed` *(Prod)* \| `read_uncommitted` *(Default)* |
| **Apache Kafka Default** | `read_uncommitted` |
| **Expected / Recommended Values** | Non-Transactional: `read_uncommitted`<br/>Transactional Ingest: `read_committed` |
| **Criticality Rating** | HIGH |
| **Definition** | Controls whether consumers read uncommitted transactional messages (`read_uncommitted`) or only messages belonging to committed transactions (`read_committed`). |
| **Why & When to Configure It** | Prevents consumers from reading dirty records from aborted producer transactions. |
| **Outcome / System Impact** | Filters out uncommitted records before writing to ClickHouse. |

---

## 8. Log Compaction Mechanics & Cleanup Policies (`cleanup.policy`)

### 8.1 Log Compaction Lifecycle

Log compaction retains the latest value for each key within a partition log.

```mermaid
graph LR
    subgraph Before Compaction
        K1_V1["Key: K1, Val: V1 (Seq 1)"]
        K2_V1["Key: K2, Val: V1 (Seq 2)"]
        K1_V2["Key: K1, Val: V2 (Seq 3)"]
        K2_V2["Key: K2, Val: V2 (Seq 4)"]
    end

    subgraph Log Compaction Cleaner
        CleanerThread["Cleaner Thread"]
    end

    Before Compaction --> CleanerThread

    subgraph After Compaction
        K1_V2_Post["Key: K1, Val: V2 (Seq 3)"]
        K2_V2_Post["Key: K2, Val: V2 (Seq 4)"]
    end

    CleanerThread --> After Compaction
```

---

### 8.2 Compaction Configuration Breakdown

#### 8.2.1 `cleanup.policy` — Topic Storage Deletion vs Compaction

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `cleanup.policy` |
| **Target Location** | Topic Configuration / `server.properties` |
| **Currently Configured Value** | `delete` *(Telemetry Streams)* \| `compact` *(State Stores)* |
| **Apache Kafka Default** | `delete` |
| **Expected / Recommended Values** | Stream Telemetry: `delete`<br/>Key-Value State Store: `compact`<br/>Hybrid Retention: `compact,delete` |
| **Criticality Rating** | HIGH |
| **Definition** | `delete` purges closed segments based on time/size. `compact` retains the latest record value per message key forever. `compact,delete` compacts by key and enforces time-based expiration. |
| **Why & When to Configure It** | Use `delete` for streaming telemetry spans and access logs. Use `compact` for user profiles, service registries, and stateful application lookup caches. |
| **Outcome / System Impact** | Prevents unbounded growth on key-value state store topics. |

---

#### 8.2.2 `min.cleanable.dirty.ratio` — Compaction Execution Trigger

| Dimension | Technical Specification & Operational Guidance |
|---|---|
| **Parameter Key** | `min.cleanable.dirty.ratio` |
| **Target Location** | `config/kafka/server.properties` |
| **Currently Configured Value** | `0.5` (50% Dirty Ratio) |
| **Apache Kafka Default** | `0.5` |
| **Expected / Recommended Values** | Standard: `0.5` (50%)<br/>Frequent Compaction: `0.2` (20%) |
| **Criticality Rating** | MEDIUM |
| **Definition** | Controls the percentage of uncompacted ("dirty") records required in a log segment before the compaction cleaner thread executes. |
| **Why & When to Configure It** | Lower values compact state store topics more aggressively at the cost of minor CPU background threads. |

---

## 9. Native Kafka Emergency CLI Commands & Incident Runbooks

### 9.1 Emergency Incident 1: Host Disk Storage 100% Full

When `/var/lib/kafka/data` hits 100%, Kafka locks active log segments or shuts down.

```bash
# Step 1: Identify top storage-consuming topics
docker exec -it llmobs-kafka-broker kafka-logdirs.sh \
  --bootstrap-server localhost:9092 \
  --describe

# Step 2: Dynamically override retention to 1 hour for the bloated topic
docker exec -it llmobs-kafka-broker kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name llmobs-spans \
  --alter \
  --add-config retention.ms=3600000

# Step 3: Verify retention cleaner purges closed log segments
docker exec -it llmobs-kafka-broker kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic llmobs-spans
```

---

### 9.2 Emergency Incident 2: Under-Replicated Partitions (URP)

```bash
# Step 1: List all under-replicated partitions across the cluster
docker exec -it llmobs-kafka-broker kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --under-replicated-partitions

# Step 2: Check broker disk directories for I/O errors or full drives
docker exec -it llmobs-kafka-broker kafka-logdirs.sh \
  --bootstrap-server localhost:9092 \
  --describe
```

---

### 9.3 Emergency Incident 3: Consumer Group Lag & Offset Reset

```bash
# Step 1: Inspect consumer group lag across all topics
docker exec -it llmobs-kafka-broker kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group llmobs-clickhouse-ingest

# Step 2: Reset consumer group offsets to latest (skip broken buffer)
docker exec -it llmobs-kafka-broker kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group llmobs-clickhouse-ingest \
  --reset-offsets \
  --to-latest \
  --execute \
  --topic llmobs-spans
```

---

## 10. Master Parameter Summary Matrix

| Config Parameter | Definition | Expected Values | Currently Configured Value | Outcome / Impact | Why We Need To Set Up | Trade-off |
|---|---|---|---|---|---|---|
| `KAFKA_HEAP_OPTS` | Sets initial (`-Xms`) and maximum (`-Xmx`) physical RAM allocated strictly to JVM heap. | Dev: `-Xms512m -Xmx1024m`<br/>Prod: `-Xms1024m -Xmx2048m` | `-Xms512m -Xmx1024m` | Bounds JVM heap to 1024MB max; reduces G1GC pause times to < 50ms. | Fixes launcher bug where performance flags broke heap sizing; keeps JVM heap bounded. | Higher heap reduces RAM available for ClickHouse and OS Page Cache. |
| `deploy.resources.limits.memory` | Enforces hard Linux kernel cgroups memory limit around container process. | Base: `2048M`<br/>Prod: `4096M` | `2048M` (Limit)<br/>`512M` (Reservation) | Guarantees container RAM cannot exceed 2048MB; protects surrounding services. | Prevents Kafka from consuming all 15 GB host RAM during telemetry spikes. | Under-provisioning limit triggers Linux OOM killer (Exit status 137). |
| `log.segment.bytes` | Sets max byte size of active `.log` file before closing and rolling a new segment. | Dev: `100 MB`<br/>Prod: `512 MB` | `104857600` (100 MB) | Allows daily log retention to delete expired data; reclaims ~30 GB storage. | Kafka retention ONLY deletes closed segments; 100 MB segments ensure rapid closure. | Very small segments under high load increase file handles and disk fragmentation. |
| `log.retention.hours` | Defines duration closed log segments are retained on disk before deletion. | Dev: `24` (24 Hours)<br/>Prod: `72` (3 Days) | `24` (24 Hours) | Reclaims ~35 GB of disk space on `/dev/sda2` by deleting 1-day-old segments. | Kafka is an intermediate buffer; telemetry is ingested into ClickHouse immediately. | Lower retention means consumers have a shorter window to recover from outages. |
| `log.roll.hours` | Forcibly closes active segment after time window even if segment size < 100 MB. | Dev: `2` (2 Hours)<br/>Prod: `12` (12 Hours) | `2` (2 Hours) | Guarantees active log segments close within 2 hours for predictable deletion. | Low-throughput topics take weeks to reach 100 MB; forced rolls enable daily deletion. | Creates more segment files across dormant or low-volume topics. |
| `log.retention.check.interval.ms` | Sets millisecond interval for log cleaner thread to scan directories for expired files. | Base: `60000` (60s)<br/>Prod: `60000` (60s) | `60000` (60 Seconds) | Deletes expired segment files within 60 seconds of expiration; near-instant cleanup. | Rapidly deletes expired segments to free space on disk-constrained hosts. | Checking too frequently on 10,000+ partitions generates minor disk I/O. |
| `offsets.topic.num.partitions` | Defines partition count for internal `__consumer_offsets` tracking topic. | Base: `3`<br/>Prod: `25` | `3` | Cuts offset topic folders from 50 to 3; saves 188+ open file descriptors. | Default 50 partitions waste directories and open file handles on single-broker setup. | Lower partitions may cause commit lock contention across 100+ consumer groups. |
| `num.partitions` | Sets default partition count for auto-created telemetry topics. | Base: `3`<br/>Prod: `3` | `3` | Enables 3-parallel consumer threads across 4 host CPU cores without thrash. | Enables 3-way parallel processing across worker threads matching CPU capacity. | Higher partitions increase metadata overhead and open segment file handles. |
| `acks` | Producer acknowledgment requirements before completing write request. | Dev: `1`<br/>Prod: `all` | `all` (or `-1`) | Guarantees zero message loss during broker outages in production. | Setting `all` guarantees message persistence across in-sync replicas before returning. | `acks=all` increases write latency slightly compared to `acks=1`. |
| `linger.ms` | Artificial producer delay to wait for records to form full batch before sending. | Base: `10`<br/>Prod: `20` | `10` ms | Increases network ingestion throughput and reduces CPU socket overhead. | Batching small records into 16KB batches increases network and disk throughput 5x. | Adds minor artificial delay (10ms) to record transmission. |
| `batch.size` | Maximum byte size per partition batch in producer memory buffer. | Base: `16 KB`<br/>Prod: `64 KB` | `16384` (16 KB) | Optimizes disk sequential write blocks and network socket payloads. | Controls memory batch size sent in a single produce request. | Larger batch size increases producer memory allocation per partition. |
| `enable.auto.commit` | Controls whether consumer commits offsets automatically or via manual code. | Dev: `true`<br/>Prod: `false` | `false` | Guarantees at-least-once processing into ClickHouse without data gaps. | Manual commit (`false`) prevents data loss if consumer crashes mid-processing. | Requires explicit `commitSync()` or `commitAsync()` code handling. |
| `max.poll.interval.ms` | Maximum time allowed between consumer `poll()` calls before eviction. | Base: `300000`<br/>Prod: `600000` | `300000` (5 Minutes) | Eliminates consumer group rebalance storms during long database writes. | Prevents rebalance storms when ClickHouse batch inserts take extended time. | Setting too high delays failure detection when a consumer actually dies. |
| `enable.idempotence` | Enables Producer ID and sequence tracking to eliminate duplicate record writes. | Base: `true`<br/>Prod: `true` | `true` | Guarantees exact-once message writing to topic partition logs. | Prevents duplicate record writes caused by producer network retries. | Negligible CPU overhead for sequence number validation. |
| `cleanup.policy` | Defines topic log cleanup strategy (`delete`, `compact`, `compact,delete`). | Telemetry: `delete`<br/>State: `compact` | `delete` | Prevents unbounded growth on key-value state store topics. | Controls whether log segments are deleted by time or compacted by record key. | Compaction requires background CPU and memory for dirty segment cleaner threads. |

---

## 11. Multi-Broker Scale-Out Architecture (Single-Node to 3-Node KRaft)

```mermaid
graph TB
    subgraph Multi-Broker KRaft Cluster Architecture
        direction LR
        B1["Kafka Broker 1 (Node ID 1)<br/>Heap: 2048M | cgroup: 4096M"]
        B2["Kafka Broker 2 (Node ID 2)<br/>Heap: 2048M | cgroup: 4096M"]
        B3["Kafka Broker 3 (Node ID 3)<br/>Heap: 2048M | cgroup: 4096M"]

        B1 -->|KRaft Sync| B2
        B2 -->|KRaft Sync| B3
        B3 -->|KRaft Sync| B1
    end
```
