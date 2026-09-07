# Apache Kafka Comprehensive Architecture, Component Deep-Dive & Operational Guide

## 1. Executive Master Parameter Reference Specifications

To avoid scrolling back and forth between sections, this master reference provides an immediate, unified list of every Kafka parameter, its definitions, expected environment values, currently configured values, outcomes, trade-offs, and system impacts.

### 1.1 Master Parameter Specifications & Expected Values List

1. **Parameter**: `KAFKA_HEAP_OPTS`
   - **Definition**: Controls initial (`-Xms`) and maximum (`-Xmx`) physical RAM allocated strictly to JVM heap objects (broker metadata, request queues, partition offset indexes).
   - **Expected Values**: Dev: `-Xms512m -Xmx1024m` | Prod: `-Xms1024m -Xmx2048m` | Enterprise: `-Xms4096m -Xmx4096m`
   - **Currently Configured Value**: `-Xms512m -Xmx1024m` (Base Dev in `docker-compose.yml`) / `-Xms1024m -Xmx2048m` (Prod Override in `docker-compose.prod.yml`)
   - **Outcome / System Impact**: Restricts JVM heap to 1024MB max, leaving off-heap headroom for Linux OS Page Cache and Metaspace. Keeps G1GC collection pauses under 50ms on 4 CPU cores.
   - **Why & When to Configure It**: Fixes launcher bug where performance flags broke heap sizing; keeps JVM memory bounded to prevent host RAM starvation.
   - **Scaling & Troubleshooting**: Higher heap reduces RAM available for OS Page Cache. Monitor JMX metric `jvm_gc_pause_seconds` (> 0.5s) or error `java.lang.OutOfMemoryError: Java heap space`. Formula: `Container Limit = JVM Heap (-Xmx) + 1024MB`.

---

2. **Parameter**: `deploy.resources.limits.memory` & `reservations.memory`
   - **Definition**: Establishes hard Linux kernel `cgroups` memory boundaries around the Kafka container process.
   - **Expected Values**: Dev: `2048M` limit, `512M` reservation | Prod: `4096M` limit | Enterprise: `8192M` limit
   - **Currently Configured Value**: Limit: `2048M`, Reservation: `512M` (in `docker-compose.yml`)
   - **Outcome / System Impact**: Guarantees Kafka cannot exceed 2 GB of physical host RAM under any burst condition. Preserves memory headroom for host processes.
   - **Why & When to Configure It**: Prevents a single container from consuming all host RAM and triggering the Linux kernel Out-Of-Memory (OOM) killer against adjacent services.
   - **Scaling & Troubleshooting**: Under-provisioning limit triggers Linux OOM killer (Exit status 137). Monitor via `docker ps -a` or `dmesg | grep -i oom`. Formula: `Container Limit = JVM Heap (-Xmx) + 1024M`.

---

3. **Parameter**: `log.segment.bytes`
   - **Definition**: Maximum byte size per partition segment file before closing and rolling a new active segment file.
   - **Expected Values**: Dev: `104857600` (100 MB) | Medium Prod: `268435456` (256 MB) | High-Throughput Prod: `536870912` (512 MB)
   - **Currently Configured Value**: `104857600` (100 MB in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Reclaims ~30 GB of storage space on `/dev/sda2` by enabling rapid closure of segment files.
   - **Why & When to Configure It**: Kafka log retention ONLY deletes closed segments; active segments are never deleted regardless of age. 100 MB segments allow rapid segment closure.
   - **Scaling & Troubleshooting**: Very small segments under high throughput increase open file handle count. Increase to 512MB under > 50,000 msgs/sec load.

---

4. **Parameter**: `log.retention.hours`
   - **Definition**: Duration in hours that closed segment files are retained on disk before physical deletion.
   - **Expected Values**: Dev: `24` (24 Hours) | Production Buffer: `72` (3 Days) | Long Retention: `168` (7 Days)
   - **Currently Configured Value**: `24` (24 Hours in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Reclaims ~35 GB of disk space on `/dev/sda2` by deleting 1-day-old log segments.
   - **Why & When to Configure It**: Kafka is an intermediate buffer. Retaining logs for 7 days duplicates data and fills host disks.
   - **Scaling & Troubleshooting**: Lower retention shortens the recovery window for offline consumers. Increase to 72h if consumer downtime risks exceed 24 hours.

---

5. **Parameter**: `log.roll.hours`
   - **Definition**: Maximum time window after which an active segment is forcibly closed, even if segment size is less than 100 MB.
   - **Expected Values**: Low-Volume Topics: `2` (2 Hours) | High-Volume Topics: `12` (12 Hours) or `24` (24 Hours)
   - **Currently Configured Value**: `2` (2 Hours in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Guarantees active log segments close within 2 hours, making them eligible for retention cleanup.
   - **Why & When to Configure It**: Low-throughput topics take weeks to write 100 MB. Forced rolls enable regular file deletion.
   - **Scaling & Troubleshooting**: Creates more segment files across dormant topics. Maintain 2h for low-volume telemetry setups.

---

6. **Parameter**: `log.retention.check.interval.ms`
   - **Definition**: Millisecond interval for the log cleaner thread to scan log directories for expired segment files.
   - **Expected Values**: Dev/Base: `60000` (60 Seconds) | Large Cluster: `300000` (5 Minutes)
   - **Currently Configured Value**: `60000` (60 Seconds in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Deletes expired segment files within 60 seconds of expiration, reclaiming disk space rapidly.
   - **Why & When to Configure It**: Rapidly frees disk space on disk-constrained hosts.
   - **Scaling & Troubleshooting**: Scanning too frequently on clusters with 10,000+ partitions generates minor disk I/O overhead.

---

7. **Parameter**: `offsets.topic.num.partitions`
   - **Definition**: Partition count for the internal `__consumer_offsets` tracking topic.
   - **Expected Values**: Dev / Single-Broker: `3` | Medium Prod: `10` to `25` | Enterprise Cluster: `50`
   - **Currently Configured Value**: `3` (in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Saves 188+ open file descriptors and directory entries on single-broker instances.
   - **Why & When to Configure It**: Default 50 partitions waste file descriptors on low-node environments.
   - **Scaling & Troubleshooting**: Lower partitions may cause commit lock contention across 100+ active consumer groups. Scale up to 25 when consumer group count grows.

---

8. **Parameter**: `num.partitions`
   - **Definition**: Default partition count for newly auto-created topics.
   - **Expected Values**: Dev: `3` | Small Prod: `3` to `6` | Enterprise Cluster: `12`+
   - **Currently Configured Value**: `3` (in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Enables 3-way parallel processing across worker threads matching host CPU core count.
   - **Why & When to Configure It**: Default 1 partition bottlenecks all consumer throughput to a single thread.
   - **Scaling & Troubleshooting**: Match partition count to target consumer thread parallelism. Avoid exceeding 100 partitions per broker core.

---

9. **Parameter**: `default.replication.factor` & `offsets.topic.replication.factor`
   - **Definition**: Defines default replica copy count for auto-created user topics and internal `__consumer_offsets`.
   - **Expected Values**: Single-Broker Dev: `1` | Multi-Node Production Cluster: `3`
   - **Currently Configured Value**: `1` (Dev Single-Node) / `3` (Prod Multi-Node)
   - **Outcome / System Impact**: Determines number of physical broker copies storing partition log data.
   - **Why & When to Configure It**: Replication factor of 3 ensures zero data loss if up to 2 brokers fail concurrently.
   - **Scaling & Troubleshooting**: Triples disk storage and network replication bandwidth requirement across nodes.

---

10. **Parameter**: `min.insync.replicas`
    - **Definition**: Minimum number of in-sync replicas (ISR) that must acknowledge a produce request when `acks=all`.
    - **Expected Values**: Dev: `1` | Multi-Broker Production: `2` | High-Availability Cluster: `2` (out of 3 replicas)
    - **Currently Configured Value**: `1` (Dev) / `2` (Prod)
    - **Outcome / System Impact**: Prevents data loss during broker crashes by enforcing minimum write durability quorum.
    - **Why & When to Configure It**: If a leader broker fails, having `min.insync.replicas=2` guarantees at least one replica has identical committed data.
    - **Scaling & Troubleshooting**: If active ISR count falls below `min.insync.replicas`, producers with `acks=all` receive `NotEnoughReplicasException`.

---

11. **Parameter**: `acks` / `KAFKA_ACKS`
    - **Definition**: Dictates leader acknowledgment requirements before completing a produce request (`acks=0`, `acks=1`, `acks=all`).
    - **Expected Values**: Low-Latency: `1` | Production Durability: `all` (or `-1`)
    - **Currently Configured Value**: `all` (Prod) / `1` (Dev)
    - **Outcome / System Impact**: Guarantees zero message loss during broker failovers when combined with `min.insync.replicas=2`.
    - **Why & When to Configure It**: Setting `acks=all` ensures writes are acknowledged by all in-sync replicas before returning success.
    - **Scaling & Troubleshooting**: `acks=all` adds slight write latency compared to `acks=1` but guarantees durability.

---

12. **Parameter**: `linger.ms`
    - **Definition**: Artificial producer delay (in milliseconds) to wait for incoming records to form full batches before sending TCP requests.
    - **Expected Values**: Low-Latency: `0` | Base Ingestion: `10` | High-Throughput: `20` to `50`
    - **Currently Configured Value**: `10` ms
    - **Outcome / System Impact**: Increases network and disk throughput 5x by batching small records into full 16KB batches.
    - **Why & When to Configure It**: Default `linger.ms=0` sends records immediately, causing network socket churn.
    - **Scaling & Troubleshooting**: Adds minor latency (10ms). Increase to 20-50ms during high-volume data ingest.

---

13. **Parameter**: `batch.size`
    - **Definition**: Maximum byte size per partition batch in producer memory buffer.
    - **Expected Values**: Base / Dev: `16384` (16 KB) | Production High-Throughput: `65536` (64 KB)
    - **Currently Configured Value**: `16384` (16 KB)
    - **Outcome / System Impact**: Controls memory allocation per partition batch sent in a produce request.
    - **Why & When to Configure It**: Grouping records into 16KB or 64KB batches reduces CPU overhead and optimizes disk write block sizes.
    - **Scaling & Troubleshooting**: Larger batch size increases producer RAM allocation per topic partition.

---

14. **Parameter**: `enable.auto.commit` & `auto.commit.interval.ms`
    - **Definition**: Controls whether consumer offsets are committed automatically on a periodic timer or explicitly managed in code.
    - **Expected Values**: Reliable Data Pipelines: `false` | Real-Time Dashboard Alerting: `true`
    - **Currently Configured Value**: `false` (Prod) / `true` (Dev)
    - **Outcome / System Impact**: Guarantees at-least-once delivery into target processing systems without data loss.
    - **Why & When to Configure It**: Automatic commit (`true`) risks missing data if the consumer crashes before processing completes.
    - **Scaling & Troubleshooting**: Requires manual `commitSync()` / `commitAsync()` calls after successful processing.

---

15. **Parameter**: `max.poll.interval.ms` & `max.poll.records`
    - **Definition**: `max.poll.records` sets max records per `poll()`. `max.poll.interval.ms` sets max time allowed between `poll()` calls before consumer group eviction.
    - **Expected Values**: Fast Ingest: `max.poll.records=500`, `max.poll.interval.ms=300000` (5 Min) | Heavy DB Batching: `max.poll.records=100`, `max.poll.interval.ms=600000` (10 Min)
    - **Currently Configured Value**: `max.poll.interval.ms=300000` (5 Min) | `max.poll.records=500`
    - **Outcome / System Impact**: Prevents rebalance storms when record processing takes extended time.
    - **Why & When to Configure It**: If record processing takes longer than the interval, Kafka assumes the consumer is dead and triggers group rebalance.
    - **Scaling & Troubleshooting**: Reduce `max.poll.records` or increase `max.poll.interval.ms` for slow processing sinks.

---

16. **Parameter**: `enable.idempotence`
    - **Definition**: Enables Producer ID and sequence number tracking to eliminate duplicate record writes on the broker.
    - **Expected Values**: Standard: `true` | Disabled: `false`
    - **Currently Configured Value**: `true`
    - **Outcome / System Impact**: Guarantees exactly-once record writing to partition logs during producer retries.
    - **Why & When to Configure It**: Prevents duplicate record writes caused by transient network retries.
    - **Scaling & Troubleshooting**: Requires `acks=all` and `max.in.flight.requests.per.connection <= 5`.

---

17. **Parameter**: `cleanup.policy`
    - **Definition**: Defines log segment cleanup strategy (`delete` by age/size, `compact` by key, `compact,delete` hybrid).
    - **Expected Values**: Telemetry Streams: `delete` | State Store Topics: `compact` | Hybrid: `compact,delete`
    - **Currently Configured Value**: `delete`
    - **Outcome / System Impact**: Controls whether segments are purged by time or compacted to retain latest state per key.
    - **Why & When to Configure It**: Use `delete` for streaming records and access logs. Use `compact` for application state caches.
    - **Scaling & Troubleshooting**: Log compaction consumes background CPU and memory for dirty segment cleaner threads.

---

18. **Parameter**: `compression.type`
    - **Definition**: Specifies record batch compression algorithm (`none`, `gzip`, `snappy`, `lz4`, `zstd`).
    - **Expected Values**: High-CPU Ingest: `lz4` or `snappy` | High-Ratio Storage: `zstd` | Legacy: `gzip`
    - **Currently Configured Value**: `lz4` (Producer) / `producer` (Broker Inherit)
    - **Outcome / System Impact**: Reduces network bandwidth usage and disk storage footprint by 3x–7x with minimal CPU overhead.
    - **Why & When to Configure It**: Batching records into `lz4` compresses text JSON records and trace spans efficiently.
    - **Scaling & Troubleshooting**: `lz4` provides optimal CPU-to-compression speed ratio for streaming telemetry.

---

19. **Parameter**: `max.in.flight.requests.per.connection`
    - **Definition**: Maximum number of unacknowledged produce requests the producer client sends on a single TCP connection before blocking.
    - **Expected Values**: Strict Message Ordering + Idempotency: `5` (or `1`) | Non-Idempotent Strict Order: `1`
    - **Currently Configured Value**: `5`
    - **Outcome / System Impact**: Maximizes network pipeline throughput while ensuring message ordering when `enable.idempotence=true`.
    - **Why & When to Configure It**: Setting higher than 1 on non-idempotent producers risks message reordering if retries occur.
    - **Scaling & Troubleshooting**: Always set `<= 5` when `enable.idempotence=true` to maintain strict partition sequence guarantees.

---

20. **Parameter**: `fetch.min.bytes` & `fetch.max.wait.ms`
    - **Definition**: `fetch.min.bytes` sets minimum data bytes broker should return for a fetch request. `fetch.max.wait.ms` sets max time broker waits to accumulate `fetch.min.bytes`.
    - **Expected Values**: Low-Latency: `fetch.min.bytes=1`, `fetch.max.wait.ms=500` | High-Throughput Sink: `fetch.min.bytes=1048576` (1 MB), `fetch.max.wait.ms=500`
    - **Currently Configured Value**: `fetch.min.bytes=1048576` (1 MB) | `fetch.max.wait.ms=500` ms
    - **Outcome / System Impact**: Reduces consumer CPU poll loop iterations and broker network I/O calls by 10x.
    - **Why & When to Configure It**: Stops consumer from executing empty poll loops on low-throughput topics.
    - **Scaling & Troubleshooting**: Increase `fetch.min.bytes` to 1MB or 4MB in batch analytics consumers.

---

21. **Parameter**: `session.timeout.ms` & `heartbeat.interval.ms`
    - **Definition**: `session.timeout.ms` sets max time group coordinator waits for heartbeats before evicting consumer. `heartbeat.interval.ms` sets frequency of background heartbeat thread.
    - **Expected Values**: Production Ingest: `session.timeout.ms=45000` (45s), `heartbeat.interval.ms=3000` (3s) | Aggressive Eviction: `session.timeout.ms=10000` (10s), `heartbeat.interval.ms=3000`
    - **Currently Configured Value**: `session.timeout.ms=45000` | `heartbeat.interval.ms=3000`
    - **Outcome / System Impact**: Eliminates false consumer group rebalances caused by transient network GC pauses.
    - **Why & When to Configure It**: Rule of thumb: `heartbeat.interval.ms` must be `<= 1/3` of `session.timeout.ms`.
    - **Scaling & Troubleshooting**: Increase `session.timeout.ms` to 45s in containerized cloud environments with transient network latency.

---

22. **Parameter**: `num.network.threads` & `num.io.threads`
    - **Definition**: `num.network.threads` sets NIO network acceptor/response threads. `num.io.threads` sets disk read/write request handler threads.
    - **Expected Values**: Base Dev (4 Core): `num.network.threads=3`, `num.io.threads=4` | High-Core Prod (16 Core): `num.network.threads=8`, `num.io.threads=16`
    - **Currently Configured Value**: `num.network.threads=3` | `num.io.threads=4` (in `config/kafka/server.properties`)
    - **Outcome / System Impact**: Prevents request queue contention under high concurrent client connection counts.
    - **Why & When to Configure It**: `num.io.threads` should equal physical CPU core count or disk drive count; `num.network.threads` should equal 50% CPU core count.
    - **Scaling & Troubleshooting**: Monitor JMX metric `RequestHandlerAvgIdlePercent` (< 0.2 means IO threads exhausted).

---

23. **Parameter**: `security.protocol` & `sasl.mechanism`
    - **Definition**: Configures cluster transport security protocol (`PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL`) and authentication mechanism (`PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`).
    - **Expected Values**: Local Dev: `PLAINTEXT` | Internal VPC: `SASL_PLAINTEXT` (SCRAM-SHA-512) | Public/Cross-DC: `SASL_SSL` (SCRAM-SHA-512)
    - **Currently Configured Value**: `PLAINTEXT` (Dev/Internal Docker Network)
    - **Outcome / System Impact**: Enforces encrypted TLS network wire transfers and authenticated client ACL access permissions.
    - **Why & When to Configure It**: Prevents unauthorized client reading/writing to Kafka topics.
    - **Scaling & Troubleshooting**: TLS encryption adds 3–5% CPU overhead for hardware AES-NI packet encryption.

---

24. **Parameter**: `min.cleanable.dirty.ratio` & `segment.ms`
    - **Definition**: `min.cleanable.dirty.ratio` sets dirty record threshold percentage before log cleaner runs. `segment.ms` sets forced segment roll time for compacted topics.
    - **Expected Values**: Normal Compaction: `0.5` (50%), `segment.ms=604800000` (7 Days) | Aggressive Compaction: `0.2` (20%), `segment.ms=86400000` (24 Hours)
    - **Currently Configured Value**: `0.5` | `segment.ms=604800000`
    - **Outcome / System Impact**: Controls background cleaner CPU overhead and state store memory retention.
    - **Why & When to Configure It**: Compacting dirty segments purges old key revisions, saving state store disk space.
    - **Scaling & Troubleshooting**: Monitor JMX cleaner thread stats `max-dirty-percent`.

---

25. **Parameter**: `isolation.level`
    - **Definition**: Controls whether consumer reads uncommitted transactional messages (`read_uncommitted`) or only committed transactions (`read_committed`).
    - **Expected Values**: Non-Transactional Telemetry: `read_uncommitted` | Transactional Ingest / EOS: `read_committed`
    - **Currently Configured Value**: `read_committed` (Prod) / `read_uncommitted` (Dev)
    - **Outcome / System Impact**: Guarantees consumers skip aborted transaction records and control markers.
    - **Why & When to Configure It**: Required when using transactional producers (`begin_transaction`, `commit_transaction`) to prevent reading dirty data.
    - **Scaling & Troubleshooting**: `read_committed` buffers uncommitted messages in consumer memory until transaction commit marker arrives.

---

26. **Parameter**: `buffer.memory` & `max.block.ms`
    - **Definition**: `buffer.memory` sets total bytes available to producer for record accumulator buffering. `max.block.ms` sets max time `send()` blocks when accumulator is full.
    - **Expected Values**: Base Dev: `33554432` (32 MB) | High-Burst Production: `67108864` (64 MB) or `134217728` (128 MB)
    - **Currently Configured Value**: `33554432` (32 MB) | `max.block.ms=60000` (60 Seconds)
    - **Outcome / System Impact**: Bounds producer application RAM usage and throws `TimeoutException` if broker connection fails.
    - **Why & When to Configure It**: Protects producer applications from Out-Of-Memory crashes during network partition outages.
    - **Scaling & Troubleshooting**: Increase `buffer.memory` to 64MB or 128MB when handling large burst traffic spikes.

---

27. **Parameter**: `auto.offset.reset`
    - **Definition**: Controls consumer starting position when no valid initial offset is found in `__consumer_offsets` (`earliest`, `latest`, `none`).
    - **Expected Values**: Batch Ingestion / Data Backfill: `earliest` | Real-Time Monitoring: `latest`
    - **Currently Configured Value**: `earliest`
    - **Outcome / System Impact**: Ensures new consumer groups read from offset 0 rather than dropping historical topic records.
    - **Why & When to Configure It**: Use `earliest` to prevent data loss when deploying new consumer groups.
    - **Scaling & Troubleshooting**: `none` throws `NoOffsetForPartitionException` if no committed offset is located.

---

28. **Parameter**: `group.instance.id` (Static Membership)
    - **Definition**: Unique string identifier assigned to a consumer instance enabling static group membership protocol.
    - **Expected Values**: Dynamic Pods: `None` | Kubernetes StatefulSets / Container Instances: `instance-pod-0`, `instance-pod-1`
    - **Currently Configured Value**: `None` (Dynamic Membership)
    - **Outcome / System Impact**: Eliminates partition rebalances during rolling application container updates.
    - **Why & When to Configure It**: Allows restarting consumers to rejoin within `session.timeout.ms` and reclaim identical partition assignments without triggering group-wide rebalances.
    - **Scaling & Troubleshooting**: Requires setting `session.timeout.ms` to at least 45 seconds.

---

29. **Parameter**: `queued.max.requests` & `socket.request.max.bytes`
    - **Definition**: `queued.max.requests` sets max un-processed requests allowed in memory request queue. `socket.request.max.bytes` sets max byte payload allowed for a single network request.
    - **Expected Values**: Base Dev: `queued.max.requests=500`, `socket.request.max.bytes=104857600` (100 MB) | Production Cluster: `queued.max.requests=10000`, `socket.request.max.bytes=104857600`
    - **Currently Configured Value**: `500` | `104857600` (100 MB)
    - **Outcome / System Impact**: Prevents broker memory exhaustion from client request surges while enforcing request size bounds.
    - **Why & When to Configure It**: Protects broker JVM heap from unbounded request object queue accumulation.
    - **Scaling & Troubleshooting**: Monitor JMX metric `RequestQueueTimeMs`.

---

30. **Parameter**: `unclean.leader.election.enable`
    - **Definition**: Dictates whether out-of-sync replicas (non-ISR) can be elected as partition leader if all ISR replicas fail (`true` or `false`).
    - **Expected Values**: Financial / Loss-Averse Production: `false` | High-Availability Alerting: `true`
    - **Currently Configured Value**: `false`
    - **Outcome / System Impact**: Prevents silent data loss and log divergence during catastrophic broker outages.
    - **Why & When to Configure It**: Setting `false` guarantees that non-ISR replicas containing missing writes are never elected leader.
    - **Scaling & Troubleshooting**: Setting `false` prioritizes data durability over availability during ISR multi-node failures.

---

## 2. System-Wide Kafka High-Level (HLD) & Low-Level (LLD) Design

### 2.1 System Integration Configuration & Python Code

```yaml
services:
  llmobs-kafka:
    image: apache/kafka:latest
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_HEAP_OPTS=-Xms512m -Xmx1024m
```

```python
from confluent_kafka import Producer, Consumer

producer_config = {
    'bootstrap.servers': 'localhost:31414',
    'client.id': 'telemetry-ingest-agent',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 10,
    'batch.size': 16384,
    'max.in.flight.requests.per.connection': 5,
    'compression.type': 'lz4',
    'retries': 5,
    'retry.backoff.ms': 100,
    'buffer.memory': 33554432,
    'max.block.ms': 60000
}
producer = Producer(producer_config)
producer.produce('llmobs-spans', key='trace_101', value='{"span_id": "s101", "duration_ms": 42}')
producer.flush()

consumer_config = {
    'bootstrap.servers': 'localhost:31414',
    'group.id': 'llmobs-clickhouse-ingest',
    'client.id': 'clickhouse-ingest-worker-1',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'auto.commit.interval.ms': 5000,
    'max.poll.interval.ms': 300000,
    'max.poll.records': 500,
    'session.timeout.ms': 45000,
    'heartbeat.interval.ms': 3000,
    'fetch.min.bytes': 1048576,
    'fetch.max.wait.ms': 500,
    'max.partition.fetch.bytes': 1048576,
    'isolation.level': 'read_committed',
    'partition.assignment.strategy': 'cooperative-sticky'
}
consumer = Consumer(consumer_config)
consumer.subscribe(['llmobs-spans'])
```

---

### 2.2 System High-Level Design (HLD) — Pure Kafka Architecture

```mermaid
graph TD
    subgraph KafkaProducerCluster ["Kafka Producer Layer"]
        P1["Producer Client Process 1"]
        P2["Producer Client Process 2"]
    end

    subgraph KafkaClusterBoundary ["Kafka Broker Cluster Boundary"]
        subgraph BrokerCore ["llmobs-kafka Broker Process (cgroup 2048M Limit)"]
            NetListener["Network Socket Listener (Port 9092)"]
            JVMHeap["JVM Heap (-Xmx1024M)"]
            PageCache["Linux OS Page Cache"]
            LogStorage["Partition Log Segments (/var/lib/kafka/data)"]
        end

        subgraph KRaftQuorum ["KRaft Controller Quorum"]
            KRaftEngine["KRaft Metadata Engine (@metadata)"]
        end
    end

    subgraph KafkaConsumerCluster ["Kafka Consumer Layer"]
        C1["Consumer Thread 1 (Worker)"]
        C2["Consumer Thread 2 (Worker)"]
        Coord["Broker Group Coordinator (__consumer_offsets)"]
    end

    P1 -->|Produce Batches| NetListener
    P2 -->|Produce Batches| NetListener
    NetListener --> JVMHeap
    JVMHeap --> PageCache
    PageCache --> LogStorage

    KRaftEngine -->|Metadata Sync| NetListener

    LogStorage -->|Zero-Copy sendfile| C1
    LogStorage -->|Zero-Copy sendfile| C2
    C1 -->|Commit Offsets| Coord
    C2 -->|Commit Offsets| Coord

    style P1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style NetListener fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style JVMHeap fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style PageCache fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style LogStorage fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style KRaftEngine fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style C1 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C2 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style Coord fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1 stroke:#38bdf8,stroke-width:2px;
    linkStyle 2,3,4 stroke:#34d399,stroke-width:2px;
    linkStyle 5 stroke:#818cf8,stroke-width:2px;
    linkStyle 6,7,8,9 stroke:#c084fc,stroke-width:2px;
```

---

### 2.3 System Low-Level Design (LLD) — End-to-End Execution Flow

```mermaid
graph TB
    subgraph ProducerInternals ["Producer Client Execution"]
        P_App["Application Record"] --> P_Ser["Serializer"]
        P_Ser --> P_Part["Partitioner (MurmurHash2)"]
        P_Part --> P_Buf["RecordAccumulator (32MB Buffer)"]
        P_Buf --> P_Send["Sender Thread"]
    end

    subgraph BrokerInternals ["Broker Internal Execution"]
        P_Send -->|TCP Produce Request| B_Net["Acceptor and Network Threads"]
        B_Net --> B_ReqQ["Request Queue"]
        B_ReqQ --> B_Worker["KafkaRequestHandler Worker Threads"]
        B_Worker --> B_Heap["JVM Heap Metadata"]
        B_Worker --> B_PageCache["Linux OS Page Cache"]
        B_PageCache --> B_Log["Active Log Segment (.log)"]
        B_Cleaner["Log Retention Cleaner Thread"] -->|Deletes expired segments| B_ClosedLog["Closed Log Segments (.log)"]
    end

    subgraph ConsumerInternals ["Consumer Client Execution"]
        B_PageCache -->|Zero-Copy sendfile| C_Fetch["Consumer Fetcher Thread"]
        C_Fetch --> C_Buf["CompletedFetch Queue"]
        C_Buf --> C_Poll["Consumer poll Loop"]
        C_Poll --> C_Commit["Offset Commit Manager (__consumer_offsets)"]
        C_Commit -->|Commit Offsets| B_Net
    end

    style P_App fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P_Ser fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P_Part fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P_Buf fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P_Send fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc

    style B_Net fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_ReqQ fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_Worker fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_Heap fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_PageCache fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_Log fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_Cleaner fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B_ClosedLog fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    style C_Fetch fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C_Buf fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C_Poll fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C_Commit fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3 stroke:#38bdf8,stroke-width:2px;
    linkStyle 4,5,6,7,8,9,10 stroke:#34d399,stroke-width:2px;
    linkStyle 11,12,13,14,15 stroke:#c084fc,stroke-width:2px;
```

---

## 3. Broker & KRaft Metadata Architecture Deep-Dive

### 3.1 Broker Configuration & Python Admin Code

```properties
node.id=1
process.roles=broker,controller
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=PLAINTEXT://localhost:31414
num.network.threads=3
num.io.threads=4
socket.send.buffer.bytes=1048576
socket.receive.buffer.bytes=1048576
socket.request.max.bytes=104857600
log.dirs=/var/lib/kafka/data
num.partitions=3
offsets.topic.num.partitions=3
default.replication.factor=1
offsets.topic.replication.factor=1
min.insync.replicas=1
log.segment.bytes=104857600
log.retention.hours=24
log.roll.hours=2
log.retention.check.interval.ms=60000
log.cleaner.enable=true
log.cleaner.threads=2
log.cleaner.dedupe.buffer.size=134217728
```

```python
from confluent_kafka.admin import AdminClient

admin_client = AdminClient({'bootstrap.servers': 'localhost:31414'})
cluster_metadata = admin_client.list_topics(timeout=10)

print(f"Broker Controller Node ID: {cluster_metadata.controller_id}")
for broker_id, broker in cluster_metadata.brokers.items():
    print(f"Active Broker Node: {broker_id} -> {broker.host}:{broker.port}")
```

---

### 3.2 Broker High-Level Design (HLD)

```mermaid
graph TD
    Client["Producer / Consumer Clients"] -->|Port 9092| SocketListener["Network Socket Listener"]
    KRaftPeer["KRaft Controller Quorum Peers"] -->|Port 9093| ControllerListener["Controller Listener"]

    subgraph BrokerCoreEngine ["llmobs-kafka Broker Process"]
        SocketListener --> NetPool["Network Processing Pool"]
        ControllerListener --> KRaftEngine["KRaft Metadata Engine (@metadata)"]
        NetPool --> WorkPool["I/O Request Handler Pool"]
        WorkPool --> MemoryMgr["Memory Manager (Heap vs OS Page Cache)"]
        MemoryMgr --> LogEngine["Partition Log Storage Engine"]
    end

    style Client fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style KRaftPeer fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style SocketListener fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ControllerListener fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style NetPool fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style KRaftEngine fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style WorkPool fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style MemoryMgr fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style LogEngine fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0 stroke:#38bdf8,stroke-width:2px;
    linkStyle 1 stroke:#818cf8,stroke-width:2px;
    linkStyle 2,3,4,5,6 stroke:#34d399,stroke-width:2px;
```

---

### 3.3 Broker Low-Level Design (LLD)

```mermaid
graph TB
    Acceptor["Acceptor Thread"] -->|NIO Select| NetThread1["Network Thread 1"]
    Acceptor -->|NIO Select| NetThread2["Network Thread 2"]

    NetThread1 -->|Push Request| RequestQueue["Request Queue"]
    NetThread2 -->|Push Request| RequestQueue

    RequestQueue -->|Pop Request| IOThread1["KafkaRequestHandler 1"]
    RequestQueue -->|Pop Request| IOThread2["KafkaRequestHandler 2"]

    subgraph MemoryArchitecture ["Broker Memory Architecture"]
        IOThread1 -->|Allocate Objects| JVMHeap["JVM Heap (-Xmx1024M) - Broker Metadata"]
        IOThread1 -->|Native Buffers| NativeMem["Native Off-Heap Memory - Direct ByteBuffers"]
        IOThread1 -->|Zero-Copy Data| PageCache["Linux OS Page Cache - In-Memory Logs"]
    end

    subgraph StorageLayout ["Physical Storage Layout (/var/lib/kafka/data)"]
        PageCache -->|Flush| LogFile["00000000000000000000.log (Message Data)"]
        PageCache -->|Flush| IndexFile["00000000000000000000.index (Offset Index)"]
        PageCache -->|Flush| TimeIndex["00000000000000000000.timeindex (Timestamp Index)"]
        PageCache -->|Flush| EpochFile["leader-epoch-checkpoint (Leader Epochs)"]
    end

    style Acceptor fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style NetThread1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style NetThread2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style RequestQueue fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style IOThread1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style IOThread2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style JVMHeap fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style NativeMem fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style PageCache fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style LogFile fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style IndexFile fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TimeIndex fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style EpochFile fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12 stroke:#34d399,stroke-width:2px;
```

---

### 3.4 Broker Detailed Configuration Breakdown

1. **Parameter**: `KAFKA_HEAP_OPTS`
   - **Definition**: Controls initial (`-Xms`) and maximum (`-Xmx`) physical memory allocated strictly to Java Virtual Machine (JVM) heap objects (broker metadata, active request queues, partition offset indexes, consumer group coordinator state).
   - **Expected Values**: Base Dev: `-Xms512m -Xmx1024m` | Small Prod: `-Xms1024m -Xmx2048m` | High-Throughput Prod: `-Xms4096m -Xmx4096m`
   - **Currently Configured Value**: `-Xms512m -Xmx1024m` (Base Dev in `docker-compose.yml`) / `-Xms1024m -Xmx2048m` (Prod Override in `docker-compose.prod.yml`)
   - **Outcome / System Impact**: Restricts JVM heap to 1024MB max, leaving 1024MB off-heap headroom for Linux OS Page Cache, socket buffers, and Metaspace. Keeps G1GC collection pauses under 50ms on 4 CPU cores.
   - **Why & When to Configure It**: Fixes environment variable parsing bugs in `kafka-run-class.sh` launcher scripts and keeps Java memory strictly bounded to prevent host RAM starvation.
   - **Scaling & Troubleshooting**: Monitor JMX metric `jvm_gc_pause_seconds` (> 0.5s) or error `java.lang.OutOfMemoryError: Java heap space`. Formula: `Container Limit = JVM Heap (-Xmx) + 1024MB`.

---

2. **Parameter**: `deploy.resources.limits.memory` & `reservations.memory`
   - **Definition**: Establishes hard Linux kernel `cgroups` memory boundaries around the Kafka container process.
   - **Expected Values**: Base Dev: `2048M` limit, `512M` reservation | Small Prod: `4096M` limit | High-Throughput Prod: `8192M` limit
   - **Currently Configured Value**: Limit: `2048M`, Reservation: `512M` (in `docker-compose.yml`)
   - **Outcome / System Impact**: Guarantees Kafka cannot exceed 2 GB of physical host RAM under any burst condition. Preserves guaranteed memory headroom for host processes.
   - **Why & When to Configure It**: Prevents a single run-away container from consuming all host RAM and triggering the host Linux kernel Out-Of-Memory (OOM) killer against adjacent services.
   - **Scaling & Troubleshooting**: Monitor container exit status `137` in `docker ps -a` or `dmesg | grep -i oom`. Formula: `Container Limit = JVM Heap (-Xmx) + 1024M` minimum off-heap buffer.

---

3. **Parameter**: `num.network.threads` & `num.io.threads`
   - **Definition**: `num.network.threads` handles incoming TCP NIO network requests. `num.io.threads` handles processing partition disk reads/writes.
   - **Expected Values**: Base Dev (4 Core): `num.network.threads=3`, `num.io.threads=4` | High-Core Prod (16 Core): `num.network.threads=8`, `num.io.threads=16`
   - **Currently Configured Value**: `num.network.threads=3` | `num.io.threads=4` (in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Eliminates broker request queue lock contention under high concurrent producer/consumer connections.
   - **Why & When to Configure It**: `num.io.threads` must match available physical CPU cores or disk spindles. `num.network.threads` should equal 50% CPU core count.
   - **Scaling & Troubleshooting**: Monitor JMX metric `RequestHandlerAvgIdlePercent`. Values < 0.2 indicate thread pool exhaustion.

---

## 4. Producer Architecture & Component Deep-Dive

### 4.1 Producer Configuration & Python Producer Code

```python
from confluent_kafka import Producer
import json, time

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

producer = Producer({
    'bootstrap.servers': 'localhost:31414',
    'client.id': 'telemetry-producer-v1',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 10,
    'batch.size': 16384,
    'max.in.flight.requests.per.connection': 5,
    'compression.type': 'lz4',
    'retries': 5,
    'retry.backoff.ms': 100,
    'buffer.memory': 33554432,
    'max.block.ms': 60000,
    'queue.buffering.max.messages': 100000,
    'queue.buffering.max.kbytes': 1048576
})

for i in range(100):
    payload = json.dumps({'span_id': f's_{i}', 'timestamp': time.time()})
    producer.produce(
        topic='llmobs-spans',
        key=f'trace_{i % 3}',
        value=payload,
        callback=delivery_report
    )
    producer.poll(0)

producer.flush()
```

---

### 4.2 Producer High-Level Design (HLD)

```mermaid
graph TD
    AppThread["Application Thread - send(ProducerRecord)"] --> Serializer["Key/Value Serializers"]
    Serializer --> Partitioner["Partitioner (MurmurHash2 / RoundRobin)"]
    Partitioner --> RecordAccumulator["RecordAccumulator (Memory Buffer)"]

    subgraph BackgroundProcessing ["Background I/O Thread"]
        RecordAccumulator --> SenderThread["Sender Thread"]
        SenderThread --> SocketChannel["Network Client and SocketChannel"]
    end

    SocketChannel -->|TCP Produce Request| KafkaBroker["llmobs-kafka Broker"]

    style AppThread fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Serializer fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Partitioner fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style RecordAccumulator fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style SenderThread fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style SocketChannel fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style KafkaBroker fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4 stroke:#38bdf8,stroke-width:2px;
    linkStyle 5 stroke:#34d399,stroke-width:2px;
```

---

### 4.3 Producer Low-Level Design (LLD)

```mermaid
graph TB
    subgraph ProducerMemoryPool ["Producer Memory Pool (buffer.memory = 32MB)"]
        BatchP0["Partition 0 Batch (batch.size = 16KB)"]
        BatchP1["Partition 1 Batch (batch.size = 16KB)"]
        BatchP2["Partition 2 Batch (batch.size = 16KB)"]
    end

    subgraph BatchTriggerLogic ["Batch Trigger Conditions"]
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

    subgraph InFlightNetworkQueue ["In-Flight Queue (max.in.flight.requests = 5)"]
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

    style BatchP0 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style BatchP1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style BatchP2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Trigger1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Trigger2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style SenderThread fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Req1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Req2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style BrokerNode fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style AckHandler fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Complete fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style RetryQueue fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 stroke:#38bdf8,stroke-width:2px;
```

---

### 4.4 Producer Detailed Configuration Breakdown

1. **Parameter**: `acks` / `KAFKA_ACKS`
   - **Definition**: Dictates leader acknowledgment requirements before completing a produce request: `acks=0` (no ACK), `acks=1` (leader ACK only), `acks=all` (leader + all in-sync replicas ACK).
   - **Expected Values**: Low-Latency: `1` | Durability / Prod: `all` (or `-1`)
   - **Currently Configured Value**: `all` (Prod) / `1` (Dev)
   - **Outcome / System Impact**: Guarantees zero message loss during broker failovers when combined with `min.insync.replicas=2`.
   - **Why & When to Configure It**: Setting `acks=all` guarantees that writes are committed to all in-sync replicas before returning success, preventing message loss if the leader broker dies.
   - **Scaling & Troubleshooting**: Keep `acks=all` in production. For ultra-low latency metrics where data loss is acceptable, set `acks=1`.

---

2. **Parameter**: `linger.ms` & `batch.size`
   - **Definition**: `batch.size` sets the maximum byte size per partition batch. `linger.ms` sets the maximum artificial delay to wait for more records to join the batch before sending.
   - **Expected Values**: Low-Latency: `linger.ms=0`, `batch.size=16384` | High-Throughput: `linger.ms=20..50`, `batch.size=65536`
   - **Currently Configured Value**: `linger.ms=10` | `batch.size=16384` (16 KB)
   - **Outcome / System Impact**: Significantly reduces network packet overhead and broker CPU utilization while increasing batch write efficiency 5x.
   - **Why & When to Configure It**: Default `linger.ms=0` sends records immediately, creating thousands of tiny single-record TCP requests. Setting `linger.ms=10` allows records to group into full 16KB batches.
   - **Scaling & Troubleshooting**: Increase `linger.ms` to 20ms–50ms and `batch.size` to 64KB (65536) under high-throughput ingestion (> 10 MB/sec).

---

3. **Parameter**: `buffer.memory` & `max.block.ms`
   - **Definition**: `buffer.memory` sets total RAM available to the producer to buffer unsent batches. `max.block.ms` sets how long `send()` blocks when the buffer is full before throwing an exception.
   - **Expected Values**: Standard: `33554432` (32 MB) | High-Burst: `67108864` (64 MB) or `134217728` (128 MB)
   - **Currently Configured Value**: `buffer.memory=33554432` (32 MB) | `max.block.ms=60000` (60 Seconds)
   - **Outcome / System Impact**: Bounces producer memory usage to 32 MB and throws `TimeoutException` if network outages persist past 60 seconds.
   - **Why & When to Configure It**: Protects producer application memory from un-bounded growth during broker network outages.
   - **Scaling & Troubleshooting**: Increase `buffer.memory` to 64MB or 128MB in high-throughput applications with bursts.

---

4. **Parameter**: `compression.type`
   - **Definition**: Sets the compression codec for producer batch payloads (`none`, `gzip`, `snappy`, `lz4`, `zstd`).
   - **Expected Values**: Telemetry Stream Ingest: `lz4` | High-Ratio Storage: `zstd`
   - **Currently Configured Value**: `lz4`
   - **Outcome / System Impact**: Reduces network traffic and broker storage requirements by up to 70% with negligible CPU overhead.
   - **Why & When to Configure It**: JSON telemetry records contain high redundancy; `lz4` compresses them efficiently before network transmission.
   - **Scaling & Troubleshooting**: Use `lz4` for high throughput; use `zstd` for maximum disk compression ratio.

---

## 5. Consumer Architecture & Component Deep-Dive

### 5.1 Consumer Configuration & Python Consumer Code

```python
from confluent_kafka import Consumer, KafkaError

consumer = Consumer({
    'bootstrap.servers': 'localhost:31414',
    'group.id': 'llmobs-clickhouse-ingest',
    'client.id': 'clickhouse-consumer-worker',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'auto.commit.interval.ms': 5000,
    'max.poll.interval.ms': 300000,
    'max.poll.records': 500,
    'session.timeout.ms': 45000,
    'heartbeat.interval.ms': 3000,
    'fetch.min.bytes': 1048576,
    'fetch.max.wait.ms': 500,
    'max.partition.fetch.bytes': 1048576,
    'isolation.level': 'read_committed',
    'partition.assignment.strategy': 'cooperative-sticky'
})
consumer.subscribe(['llmobs-spans'])

try:
    while True:
        msg_list = consumer.consume(num_messages=100, timeout=1.0)
        if not msg_list:
            continue
        records_to_insert = [m.value() for m in msg_list if not m.error()]
        consumer.commit(asynchronous=False)
except KeyboardInterrupt:
    pass
finally:
    consumer.close()
```

---

### 5.2 Consumer High-Level Design (HLD)

```mermaid
graph TD
    subgraph ConsumerGroup ["Consumer Group (llmobs-clickhouse-ingest)"]
        C1["Consumer Thread 1"]
        C2["Consumer Thread 2"]
        C3["Consumer Thread 3"]
    end

    subgraph BrokerGroupCoordinator ["Broker Group Coordinator"]
        Coord["Group Coordinator Engine"]
        OffsetTopic["__consumer_offsets Topic"]
    end

    subgraph KafkaTopicPartitions ["Telemetry Topic (3 Partitions)"]
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

    style C1 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C2 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style C3 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style Coord fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style OffsetTopic fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P0 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6 stroke:#c084fc,stroke-width:2px;
```

---

### 5.3 Consumer Low-Level Design (LLD)

```mermaid
graph TB
    subgraph ConsumerPollExecution ["Consumer Thread Execution Loop"]
        PollStart["consumer.poll(Duration.ofMillis(100))"] --> CheckQueue{"CompletedFetch Queue Empty?"}
        CheckQueue -->|Yes| Fetcher["Fetcher Thread sends FetchRequest"]
        CheckQueue -->|No| ConsumerRecords["Return ConsumerRecords Batch"]

        Fetcher -->|Zero-Copy TCP Read| BrokerStorage["Broker OS Page Cache"]
        BrokerStorage --> CompletedQueue["CompletedFetch Queue"]

        ConsumerRecords --> AppProcess["Process Batch (e.g. Ingest Records)"]
        AppProcess --> CommitCheck{"enable.auto.commit = false?"}
        CommitCheck -->|Yes| ManualCommit["commitSync() / commitAsync()"]
        CommitCheck -->|No| AutoCommit["Auto Commit (every 5000ms)"]
        ManualCommit --> OffsetWrite["Write to __consumer_offsets"]
        AutoCommit --> OffsetWrite
    end

    subgraph HeartbeatThread ["Background Heartbeat Thread"]
        HBThread["Heartbeat Thread (heartbeat.interval.ms = 3000)"] -->|Send Heartbeat| CoordNode["Group Coordinator"]
        CoordNode -->|Liveness Valid| OK["Keep Partition Assignment"]
        CoordNode -.->|Session Timeout Exceeded 45s| Dead["Mark Consumer Dead and Trigger Rebalance"]
    end

    style PollStart fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style CheckQueue fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style Fetcher fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style ConsumerRecords fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style CompletedQueue fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style AppProcess fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style CommitCheck fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style ManualCommit fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style AutoCommit fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style HBThread fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    style BrokerStorage fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style OffsetWrite fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CoordNode fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style OK fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style Dead fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12,13 stroke:#c084fc,stroke-width:2px;
```

---

### 5.4 Consumer Detailed Configuration Breakdown

1. **Parameter**: `enable.auto.commit` & `auto.commit.interval.ms`
   - **Definition**: Controls whether consumer offsets are committed automatically in the background on a periodic timer or managed explicitly by application code.
   - **Expected Values**: Analytics & Pipeline DB Sinks: `false` | Stateless Real-Time Alerting: `true`
   - **Currently Configured Value**: `enable.auto.commit=false` (Prod) / `true` (Dev)
   - **Outcome / System Impact**: Guarantees exact telemetry delivery into target sinks without missing records or duplicate insertions.
   - **Why & When to Configure It**: Automatic commit (`true`) risks data loss if the consumer crashes after committing offsets but before completing processing. Setting `false` allows manual commit after processing success (at-least-once delivery).
   - **Scaling & Troubleshooting**: Always set `enable.auto.commit=false` in production data pipelines and call `commitSync()` / `commitAsync()`.

---

2. **Parameter**: `max.poll.interval.ms` & `max.poll.records`
   - **Definition**: `max.poll.records` sets maximum records returned in a single `poll()`. `max.poll.interval.ms` sets maximum time allowed between `poll()` calls before the consumer is marked dead and evicted from the group.
   - **Expected Values**: Fast Ingestion: `max.poll.records=500`, `max.poll.interval.ms=300000` | Heavy Batching: `max.poll.records=100`, `max.poll.interval.ms=600000`
   - **Currently Configured Value**: `max.poll.interval.ms=300000` (5 Min) | `max.poll.records=500`
   - **Outcome / System Impact**: Prevents consumer group rebalance storms during large record batch ingestion operations.
   - **Why & When to Configure It**: If batch processing takes longer than 5 minutes, Kafka assumes the consumer thread is stuck and triggers constant consumer group rebalance storms.
   - **Scaling & Troubleshooting**: If processing high-latency batches, reduce `max.poll.records` to 100 or increase `max.poll.interval.ms` to 600,000ms (10 minutes).

---

3. **Parameter**: `auto.offset.reset`
   - **Definition**: Dictates consumer behavior when no initial offset exists or when offset is out of range: `earliest` (start from oldest available record), `latest` (start from newest incoming record).
   - **Expected Values**: Telemetry Ingestion / Recovery: `earliest` | Real-Time Alerting: `latest`
   - **Currently Configured Value**: `earliest` (Dev/Recovery) / `latest` (Default Ingest)
   - **Outcome / System Impact**: Ensures new ingestion instances process all buffered streams without skipping data.
   - **Why & When to Configure It**: Use `earliest` for new consumer groups that need to process historical buffered streams; use `latest` for real-time dashboard alerting.

---

4. **Parameter**: `session.timeout.ms` & `heartbeat.interval.ms`
   - **Definition**: `session.timeout.ms` sets maximum time group coordinator waits for consumer heartbeat. `heartbeat.interval.ms` sets background heartbeat frequency.
   - **Expected Values**: Standard: `session.timeout.ms=45000`, `heartbeat.interval.ms=3000`
   - **Currently Configured Value**: `session.timeout.ms=45000` | `heartbeat.interval.ms=3000`
   - **Outcome / System Impact**: Eliminates false consumer group rebalances caused by minor network jitter or JVM GC pauses.
   - **Why & When to Configure It**: Rule of thumb is `heartbeat.interval.ms` must be `<= 1/3` of `session.timeout.ms`.

---

## 6. Topic Partitions, Offset Pointers, Watermarks & Rebalancing Deep-Dive

### 6.1 Topic Partitioning & Key Hashing Mechanics

#### Topic Creation & Partition Key Hashing Python Code

```python
from confluent_kafka.admin import AdminClient, NewTopic
import mmh3

admin = AdminClient({'bootstrap.servers': 'localhost:31414'})
new_topic = NewTopic(
    'llmobs-spans',
    num_partitions=3,
    replication_factor=1,
    config={
        'cleanup.policy': 'delete',
        'retention.ms': '86400000',
        'segment.bytes': '104857600',
        'segment.ms': '7200000',
        'min.insync.replicas': '1',
        'compression.type': 'producer'
    }
)
admin.create_topics([new_topic])

def calculate_kafka_partition(key_bytes, num_partitions=3):
    if key_bytes is None:
        return 0
    hash_val = mmh3.hash(key_bytes) & 0x7fffffff
    return hash_val % num_partitions

print(f"Key 'trace_101' maps to Partition: {calculate_kafka_partition(b'trace_101')}")
```

#### Partitioner High-Level Architecture (HLD)

```mermaid
graph TD
    subgraph PartitionerEngine ["Kafka Partitioner Architecture"]
        Record["ProducerRecord (Key, Value)"] --> CheckKey{"Record Key Provided?"}
        CheckKey -->|Yes| MurmurHash["MurmurHash2 Algorithm (to32Bits)"]
        MurmurHash --> ModuloOp["(hash & 0x7fffffff) % num_partitions"]
        ModuloOp --> TargetPartition["Target Partition ID"]

        CheckKey -->|No| StickyPartitioner["Sticky Partitioner (Batch Pool)"]
        StickyPartitioner --> CurrentBatchPartition["Active Batch Partition"]
    end

    style Record fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style CheckKey fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style MurmurHash fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style ModuloOp fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style TargetPartition fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style StickyPartitioner fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style CurrentBatchPartition fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5 stroke:#38bdf8,stroke-width:2px;
```

#### Partition Skew & Hashing Mechanics (LLD)

```mermaid
graph TB
    subgraph PartitionHotspotting ["Partition Hashing & Skew Mechanics"]
        Key1["Key: trace_101"] --> H1["Hash: 41208571"] --> P0["Partition 0 (33% Load)"]
        Key2["Key: trace_102"] --> H2["Hash: 89012444"] --> P1["Partition 1 (33% Load)"]
        Key3["Key: trace_103"] --> H3["Hash: 12048912"] --> P2["Partition 2 (33% Load)"]
        NullKey["Key: None"] --> Sticky["Sticky Batcher"] --> P0
    end

    style Key1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Key2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Key3 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style NullKey fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style H1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style H2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style H3 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Sticky fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style P0 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7 stroke:#38bdf8,stroke-width:2px;
```

---

### 6.2 Offset Pointers, Log End Offset (LEO), High Watermark (HW) & Leader Epochs

#### Consumer Offset Seeking & Inspection Python Code

```python
from confluent_kafka import Consumer, TopicPartition

consumer = Consumer({
    'bootstrap.servers': 'localhost:31414',
    'group.id': 'offset-inspector-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
})

tp = TopicPartition('llmobs-spans', 0)
low_watermark, high_watermark = consumer.get_watermark_offsets(tp)
print(f"Partition 0 Watermarks -> Low: {low_watermark}, High Watermark (HW): {high_watermark}")

consumer.assign([tp])
consumer.seek(TopicPartition('llmobs-spans', 0, 42))

msg = consumer.poll(1.0)
if msg:
    print(f"Read Record at Offset Pointer: {msg.offset()}")

consumer.close()
```

#### Replication Watermarks & High Watermark Sync (HLD)

```mermaid
graph TB
    subgraph ReplicationWatermarks ["Leader vs Replica Watermark Sync"]
        LeaderLEO["Leader Replica LEO: 10"] --> LeaderHW["Leader High Watermark (HW): 8"]
        Follower1LEO["Follower 1 Replica LEO: 8"] --> LeaderHW
        Follower2LEO["Follower 2 Replica LEO: 8"] --> LeaderHW
        LeaderHW --> ConsumerVisible["Consumers can ONLY read up to HW: 8"]
    end

    style LeaderLEO fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style Follower1LEO fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style Follower2LEO fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style LeaderHW fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style ConsumerVisible fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2 stroke:#34d399,stroke-width:2px;
    linkStyle 3 stroke:#f0abfc,stroke-width:2px;
```

#### Partition Log Offset & Pointer Layout (LLD)

```mermaid
graph LR
    subgraph LogSegmentPointers ["Partition Log Offset & Watermark Architecture"]
        O0["Offset 0 (Committed)"] --> O1["Offset 1 (Committed)"]
        O1 --> O2["Offset 2 (Committed)"]
        O2 --> O3["Offset 3 (Committed)"]
        O3 --> O4["Offset 4 (Uncommitted)"]
        O4 --> O5["Offset 5 (Log End)"]
    end

    CommittedPointer["Consumer Committed Offset Pointer: 2 (__consumer_offsets)"] --> O2
    FetchPosition["Consumer Fetch Position Pointer: 3"] --> O3
    HWPointer["High Watermark (HW): 4 (Max Safe Readable Offset)"] --> O4
    LEOPointer["Log End Offset (LEO): 5 (Next Write Target)"] --> O5

    style O0 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style O1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style O2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style O3 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style O4 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style O5 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    style CommittedPointer fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style FetchPosition fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style HWPointer fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style LEOPointer fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4 stroke:#34d399,stroke-width:2px;
    linkStyle 5,6 stroke:#c084fc,stroke-width:2px;
    linkStyle 7,8 stroke:#f0abfc,stroke-width:2px;
```

---

### 6.3 Consumer Group Rebalance Protocols & Static Membership

#### Consumer Static Membership Python Code

```python
from confluent_kafka import Consumer

static_consumer = Consumer({
    'bootstrap.servers': 'localhost:31414',
    'group.id': 'llmobs-analytics-cluster',
    'group.instance.id': 'ingest-worker-pod-0',
    'session.timeout.ms': 45000,
    'heartbeat.interval.ms': 3000,
    'enable.auto.commit': False,
    'partition.assignment.strategy': 'cooperative-sticky'
})
static_consumer.subscribe(['llmobs-spans'])
```

#### Cooperative Sticky Rebalance Protocol Architecture (HLD)

```mermaid
graph TD
    subgraph CooperativeRebalance ["Cooperative Sticky Rebalance Protocol"]
        State1["Group State: STABLE"] --> MemberJoin["New Consumer Joins / Departs"]
        MemberJoin --> State2["Group State: PREPARING_REBALANCE"]
        State2 --> RevokeStep["Revoke ONLY Migrating Partitions (Cooperative)"]
        RevokeStep --> State3["Group State: COMPLETING_REBALANCE"]
        State3 --> AssignStep["Assign Revoked Partitions to New Member"]
        AssignStep --> State4["Group State: STABLE (Zero Downtime for Unaffected Partitions)"]
    end

    style State1 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style MemberJoin fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style State2 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style RevokeStep fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style State3 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style AssignStep fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style State4 fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5 stroke:#c084fc,stroke-width:2px;
```

#### Group Coordinator Protocol State Machine (LLD)

```mermaid
graph TB
    subgraph RebalanceStateMachine ["Group Coordinator LLD Protocol Execution & Static Membership"]
        ClientInit["Consumer Container Start"] --> JoinReq["Send JoinGroup Request (with group.instance.id)"]
        JoinReq --> CoordEval{"Group Coordinator Check"}

        CoordEval -->|Dynamic Member| DynamicJoin["Generate Dynamic Member ID"]
        CoordEval -->|Static Member| StaticJoin["Lookup Registered group.instance.id"]

        DynamicJoin --> TriggerFullRebalance["Trigger Group Rebalance (PREPARING_REBALANCE)"]
        StaticJoin --> CheckSession{"Rejoin within session.timeout.ms (45s)?"}

        CheckSession -->|Yes| BypassRebalance["Bypass Rebalance - Retain Partition Assignment"]
        CheckSession -->|No| EvictStatic["Evict Static Member & Revoke Partitions"]
        EvictStatic --> TriggerFullRebalance

        TriggerFullRebalance --> LeaderAssign["Group Leader Computes Cooperative Assignment"]
        LeaderAssign --> SyncReq["Send SyncGroup Request"]
        BypassRebalance --> SyncReq
        SyncReq --> ActiveLoop["Transition to STABLE - Resume Fetch Loop & Heartbeat"]
    end

    style ClientInit fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style JoinReq fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style CoordEval fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style DynamicJoin fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style StaticJoin fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style TriggerFullRebalance fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CheckSession fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style BypassRebalance fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style EvictStatic fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style LeaderAssign fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style SyncReq fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style ActiveLoop fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11 stroke:#c084fc,stroke-width:2px;
```

---

## 7. Topic Segment Lifecycle & Physical Storage Management

### 7.1 Topic Segment Storage Configuration & Code

```python
from confluent_kafka.admin import AdminClient, NewTopic

admin = AdminClient({'bootstrap.servers': 'localhost:31414'})
topic_spec = NewTopic(
    'llmobs-spans',
    num_partitions=3,
    replication_factor=1,
    config={
        'segment.bytes': '104857600',
        'retention.ms': '86400000',
        'segment.ms': '7200000',
        'cleanup.policy': 'delete'
    }
)
admin.create_topics([topic_spec])
```

---

### 7.2 Topic Segment Storage High-Level Design (HLD)

```mermaid
graph TD
    subgraph LogicalTopic ["Logical Telemetry Topic (llmobs-spans)"]

        P0["Partition 0 (Broker 1 Leader)"]
        P1["Partition 1 (Broker 2 Leader)"]
        P2["Partition 2 (Broker 3 Leader)"]
    end

    subgraph PhysicalDiskStorage ["Physical Disk Directory Structure"]
        P0 --> D0["/var/lib/kafka/data/llmobs-spans-0/"]
        P1 --> D1["/var/lib/kafka/data/llmobs-spans-1/"]
        P2 --> D2["/var/lib/kafka/data/llmobs-spans-2/"]
    end

    style P0 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style D0 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style D1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style D2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2 stroke:#34d399,stroke-width:2px;
```

---

### 7.3 Topic Segment Storage Low-Level Design (LLD)

```mermaid
graph TB
    subgraph PartitionDirectoryEngine ["Partition Engine (/var/lib/kafka/data/llmobs-spans-0/)"]
        WriteOp["Produce Record Appended"] --> ActiveSegment["Active Segment: 00000000000000000200.log (Currently Appending Write)"]

        ActiveSegment --> RollCondition{"Segment Full 100MB or Time Expired 2h?"}
        RollCondition -->|Yes| CloseSegment["Close Active Segment - Mark INACTIVE"]
        CloseSegment --> OpenNew["Open New Active Segment (.log)"]
        RollCondition -->|No| KeepWriting["Continue Appending Writes"]

        subgraph IndexLookups ["Offset and Time Index Files"]
            OffsetIndex["00000000000000000000.index (Maps Offset to Physical Byte Position)"]
            TimeIndex["00000000000000000000.timeindex (Maps Timestamp to Offset)"]
        end

        CloseSegment --> OffsetIndex
        CloseSegment --> TimeIndex

        subgraph LogRetentionCleaner ["Log Retention Cleaner Thread"]
            CleanerScan["Retention Scan (Every 60 Seconds)"] --> RetentionCheck{"Closed Segment Age Exceeds 24 Hours?"}
            RetentionCheck -->|Yes| UnlinkFile["Unlink and Delete Segment Files"]
            RetentionCheck -->|No| RetainSegment["Retain File on Disk"]
        end

        CloseSegment --> CleanerScan
    end

    style WriteOp fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ActiveSegment fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style RollCondition fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CloseSegment fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style OpenNew fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style KeepWriting fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style OffsetIndex fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TimeIndex fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CleanerScan fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style RetentionCheck fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style UnlinkFile fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style RetainSegment fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10 stroke:#34d399,stroke-width:2px;
```

---

### 7.4 Topic Segment Detailed Configuration Breakdown

1. **Parameter**: `log.segment.bytes`
   - **Definition**: Maximum byte size per partition segment file before closing and rolling a new active segment file.
   - **Expected Values**: Low/Dev: `104857600` (100 MB) | Medium Prod: `268435456` (256 MB) | High-Throughput Prod: `536870912` (512 MB) or `1073741824` (1 GB)
   - **Currently Configured Value**: `104857600` (100 MB in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Reclaims ~30 GB of storage space on `/dev/sda2` by preventing inactive topics from holding onto gigabytes of un-purged active segments.
   - **Why & When to Configure It**: Retention rules apply ONLY to closed segments. Active segments are NEVER deleted regardless of age. Setting 100 MB allows low/medium volume topics to close segments rapidly for daily deletion.
   - **Scaling & Troubleshooting**: Increase to 512MB or 1GB in high-throughput production (> 50,000 msgs/sec) to avoid excessive file handle creation.

---

2. **Parameter**: `log.retention.hours`
   - **Definition**: Duration in hours that closed segment files are retained on disk before physical deletion.
   - **Expected Values**: Base Dev: `24` (24 Hours) | Production Buffer: `72` (3 Days) | Long-Buffer Ingest: `168` (7 Days)
   - **Currently Configured Value**: `24` (24 Hours in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Reclaims ~35 GB of disk space on `/dev/sda2` by deleting 1-day-old segments.
   - **Why & When to Configure It**: Kafka is an intermediate buffer. Telemetry data is consumed almost immediately. Retaining 7 days duplicates data and consumes host storage.

---

3. **Parameter**: `log.roll.hours`
   - **Definition**: Maximum time window after which an active segment is forcibly closed, even if segment size is less than 100 MB.
   - **Expected Values**: Low-Volume Topics: `2` (2 Hours) | High-Volume Topics: `12` (12 Hours) or `24` (24 Hours)
   - **Currently Configured Value**: `2` (2 Hours in `config/kafka/server.properties`)
   - **Outcome / System Impact**: Eliminates storage leaks on dormant or low-volume topics.
   - **Why & When to Configure It**: Low-throughput topics take weeks to write 100 MB. Forced rolls every 2 hours guarantee active segments close and become eligible for 24-hour deletion.

---

## 8. Exactly-Once Semantics (EOS), Idempotency & Transactions

### 8.1 Transactional Producer & EOS Python Code

```python
from confluent_kafka import Producer, Consumer

tx_producer = Producer({
    'bootstrap.servers': 'localhost:31414',
    'transactional.id': 'llmobs-producer-tx-1',
    'enable.idempotence': True,
    'transaction.timeout.ms': 900000,
    'acks': 'all',
    'linger.ms': 10,
    'batch.size': 16384,
    'max.in.flight.requests.per.connection': 5
})
tx_producer.init_transactions()

try:
    tx_producer.begin_transaction()
    tx_producer.produce('llmobs-spans', key='t1', value='{"span": 1}')
    tx_producer.produce('llmobs-metrics', key='m1', value='{"metric": 1}')
    tx_producer.commit_transaction()
except Exception as e:
    tx_producer.abort_transaction()

eos_consumer = Consumer({
    'bootstrap.servers': 'localhost:31414',
    'group.id': 'eos-analytics-sink',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'isolation.level': 'read_committed',
    'max.poll.interval.ms': 300000,
    'session.timeout.ms': 45000
})
```

---

### 8.2 Idempotent Producer Mechanics (HLD)

```mermaid
graph TD
    subgraph IdempotentProtocol ["Idempotent Producer Protocol"]
        P1["Producer Client (enable.idempotence=true)"] -->|"1. Allocate Producer ID - PID"| B1["Broker Sequence Tracker"]
        P1 -->|"2. Send Record Batch - PID 101 Seq 0"| B1
        B1 -->|"3. Persist Batch Seq 0"| S1["Partition Log"]
        B1 -.->|"4. Network ACK Drops or Times Out"| P1
        P1 -->|"5. Retry Batch - PID 101 Seq 0"| B1
        B1 -->|"6. Detect Duplicate Seq 0"| D1["Discard Duplicate Payload & Re-ACK"]
    end

    style P1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style B1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style S1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style D1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,3,4 stroke:#38bdf8,stroke-width:2px;
    linkStyle 2,5 stroke:#34d399,stroke-width:2px;
```

---

### 8.3 Two-Phase Commit Transaction Coordinator Execution Flow (LLD)

```mermaid
graph TB
    subgraph TransactionCoordinatorLLD ["Transactional 2PC State Machine LLD"]
        TxInit["tx_producer.init_transactions()"] --> FindCoord["Locate Transaction Coordinator"]
        FindCoord --> BeginTx["tx_producer.begin_transaction()"]
        BeginTx --> SendData["Produce Records to Partitions"]

        SendData --> CommitReq["tx_producer.commit_transaction()"]
        CommitReq --> WritePrepare["Write PREPARE_COMMIT to __transaction_state"]
        WritePrepare --> WriteMarkers["Write COMMIT Control Markers to Partitions"]
        WriteMarkers --> WriteComplete["Write COMPLETE_COMMIT to __transaction_state"]
        WriteComplete --> TransactionDone["Transaction Complete"]
    end

    style TxInit fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style FindCoord fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style BeginTx fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style SendData fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style CommitReq fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style WritePrepare fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style WriteMarkers fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style WriteComplete fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TransactionDone fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7 stroke:#38bdf8,stroke-width:2px;
```

---

### 8.4 EOS Configuration Breakdown

1. **Parameter**: `enable.idempotence`
   - **Definition**: Ensures that the broker processes exactly one copy of a message batch sent by a producer, even if the producer retries due to network timeouts.
   - **Expected Values**: Standard: `true` | Legacy/Disabled: `false`
   - **Currently Configured Value**: `true`
   - **Outcome / System Impact**: Eliminates duplicate record insertions into target sinks.
   - **Why & When to Configure It**: Eliminates duplicate records in telemetry pipelines caused by transient network retries.

---

2. **Parameter**: `isolation.level`
   - **Definition**: Controls whether consumers read uncommitted transactional messages (`read_uncommitted`) or only messages belonging to committed transactions (`read_committed`).
   - **Expected Values**: Non-Transactional: `read_uncommitted` | Transactional Ingest: `read_committed`
   - **Currently Configured Value**: `read_committed` (Prod) / `read_uncommitted` (Default)
   - **Outcome / System Impact**: Filters out uncommitted records before writing to processing targets.
   - **Why & When to Configure It**: Prevents consumers from reading dirty records from aborted producer transactions.

---

## 9. Log Compaction Mechanics & Cleanup Policies (`cleanup.policy`)

### 9.1 State Store Compaction Python Code

```python
from confluent_kafka import Producer

producer = Producer({
    'bootstrap.servers': 'localhost:31414',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 10,
    'batch.size': 16384
})

producer.produce('user-service-registry', key='service_auth', value='v2.1.0')
producer.produce('user-service-registry', key='service_deprecated', value=None)
producer.flush()
```

---

### 9.2 Log Compaction Lifecycle Design (HLD)

```mermaid
graph LR
    subgraph BeforeCompaction ["Before Compaction"]
        K1_V1["Key: K1, Val: V1 (Seq 1)"]
        K2_V1["Key: K2, Val: V1 (Seq 2)"]
        K1_V2["Key: K1, Val: V2 (Seq 3)"]
        K2_V2["Key: K2, Val: V2 (Seq 4)"]
    end

    subgraph LogCompactionCleaner ["Log Compaction Cleaner"]
        CleanerThread["Log Cleaner Deduplication Thread"]
    end

    K2_V2 -->|Deduplicate Keys| CleanerThread

    subgraph AfterCompaction ["After Compaction"]
        K1_V2_Post["Key: K1, Val: V2 (Seq 3)"]
        K2_V2_Post["Key: K2, Val: V2 (Seq 4)"]
    end

    CleanerThread -->|Write Compacted Segment| K1_V2_Post

    style K1_V1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style K2_V1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style K1_V2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style K2_V2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CleanerThread fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style K1_V2_Post fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style K2_V2_Post fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1 stroke:#f0abfc,stroke-width:2px;
```

---

### 9.3 Log Compaction Cleaner Thread Execution Flow (LLD)

```mermaid
graph TB
    subgraph LogCleanerLLD ["Log Cleaner Thread Low-Level Execution"]
        ScanTrigger["Cleaner Trigger (dirty ratio >= 0.5)"] --> BuildMap["Build In-Memory Skimpy Offset Map"]
        BuildMap --> ScanDirty["Scan Dirty Log Segments"]
        ScanDirty --> DedupeKeys["Keep Highest Offset Per Message Key"]
        DedupeKeys --> WriteClean["Write Compacted Records to Clean Segment"]
        WriteClean --> SwapSegments["Atomic File Swap -> Replace Dirty Segment"]
        SwapSegments --> PurgeTombstones["Purge Expired Tombstones (delete.retention.ms)"]
    end

    style ScanTrigger fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style BuildMap fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ScanDirty fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style DedupeKeys fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style WriteClean fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style SwapSegments fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style PurgeTombstones fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5 stroke:#f0abfc,stroke-width:2px;
```

---

### 9.4 Compaction Configuration Breakdown

1. **Parameter**: `cleanup.policy`
   - **Definition**: `delete` purges closed segments based on time/size. `compact` retains the latest record value per message key forever. `compact,delete` compacts by key and enforces time-based expiration.
   - **Expected Values**: Stream Telemetry: `delete` | Key-Value State Store: `compact` | Hybrid Retention: `compact,delete`
   - **Currently Configured Value**: `delete` (Telemetry Streams) / `compact` (State Stores)
   - **Outcome / System Impact**: Prevents unbounded growth on key-value state store topics.
   - **Why & When to Configure It**: Use `delete` for streaming records and access logs. Use `compact` for user profiles, service registries, and stateful application lookup caches.

---

2. **Parameter**: `min.cleanable.dirty.ratio`
   - **Definition**: Controls the percentage of uncompacted ("dirty") records required in a log segment before the compaction cleaner thread executes.
   - **Expected Values**: Standard: `0.5` (50%) | Frequent Compaction: `0.2` (20%)
   - **Currently Configured Value**: `0.5` (50% Dirty Ratio)
   - **Outcome / System Impact**: Keeps state store compaction latency predictable while limiting background CPU usage.
   - **Why & When to Configure It**: Lower values compact state store topics more aggressively at the cost of minor CPU background threads.

---

## 10. Native Kafka Emergency CLI Commands & Incident Runbooks

### 10.1 Emergency Incident 1: Host Disk Storage 100% Full

```bash
docker exec -it llmobs-kafka-broker kafka-logdirs.sh \
  --bootstrap-server localhost:9092 \
  --describe

docker exec -it llmobs-kafka-broker kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name llmobs-spans \
  --alter \
  --add-config retention.ms=3600000

docker exec -it llmobs-kafka-broker kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic llmobs-spans
```

---

### 10.2 Emergency Incident 2: Under-Replicated Partitions (URP)

```bash
docker exec -it llmobs-kafka-broker kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --under-replicated-partitions

docker exec -it llmobs-kafka-broker kafka-logdirs.sh \
  --bootstrap-server localhost:9092 \
  --describe
```

---

### 10.3 Emergency Incident 3: Consumer Group Lag & Offset Reset

```bash
docker exec -it llmobs-kafka-broker kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group llmobs-clickhouse-ingest

docker exec -it llmobs-kafka-broker kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group llmobs-clickhouse-ingest \
  --reset-offsets \
  --to-latest \
  --execute \
  --topic llmobs-spans
```

---

### 10.4 Emergency Operational Workflow High-Level Design (HLD)

```mermaid
graph TD
    subgraph IncidentDetection ["Incident Detection & Alerts"]
        Alert1["Disk Utilization > 90% Alert"]
        Alert2["Under-Replicated Partitions > 0 Alert"]
        Alert3["Consumer Lag > Threshold Alert"]
    end

    subgraph KafkaAdminTooling ["Native Kafka CLI Diagnostic Engine"]
        LogDirsCLI["kafka-logdirs.sh --describe"]
        TopicsCLI["kafka-topics.sh --describe --under-replicated-partitions"]
        ConsumerCLI["kafka-consumer-groups.sh --describe"]
    end

    subgraph RemediationEngine ["Dynamic Remediation & Recovery Execution"]
        ConfigsCLI["kafka-configs.sh --alter --add-config retention.ms"]
        ReassignCLI["kafka-reassign-partitions.sh --execute"]
        ResetOffsetCLI["kafka-consumer-groups.sh --reset-offsets --to-latest"]
    end

    subgraph ClusterRecovery ["Cluster & Ingest Stabilization"]
        StorageReclaimed["OS Disk Space Purged & Reclaimed"]
        ISRRestored["ISR Pool Fully Synchronized"]
        LagCleared["Ingest Consumer Pipeline Stabilized"]
    end

    Alert1 --> LogDirsCLI --> ConfigsCLI --> StorageReclaimed
    Alert2 --> TopicsCLI --> ReassignCLI --> ISRRestored
    Alert3 --> ConsumerCLI --> ResetOffsetCLI --> LagCleared

    style Alert1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Alert2 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style Alert3 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style LogDirsCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TopicsCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ConsumerCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ConfigsCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ReassignCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ResetOffsetCLI fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style StorageReclaimed fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style ISRRestored fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc
    style LagCleared fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8 stroke:#34d399,stroke-width:2px;
```

---

### 10.5 Incident Remediation Low-Level Design (LLD)

```mermaid
graph TB
    subgraph StorageIncidentLLD ["Incident 1: Disk Exhaustion Remediation Flow"]
        DiskFull["Host Disk Usage 100%"] --> InspectLogDirs["Execute kafka-logdirs.sh"]
        InspectLogDirs --> TargetTopic["Identify Large Log Directories"]
        TargetTopic --> AlterRetention["Execute kafka-configs.sh --add-config retention.ms=3600000"]
        AlterRetention --> TriggerPurge["Broker LogCleaner Thread Scans Inactive Segments"]
        TriggerPurge --> UnlinkFiles["Unlink Closed Segments -> Space Reclaimed"]
    end

    subgraph URPIncidentLLD ["Incident 2: Under-Replicated Partitions Remediation Flow"]
        URPAlert["URP Count > 0 Detected"] --> FindPartition["Execute kafka-topics.sh --under-replicated-partitions"]
        FindPartition --> CheckBroker["Identify Failed Broker / Unhealthy Disk"]
        CheckBroker --> TriggerRebind["Execute kafka-reassign-partitions.sh"]
        TriggerRebind --> ReplicaFetch["Replica Re-Syncs Data from Leader"]
        ReplicaFetch --> ISRJoin["Re-join ISR Pool (URP = 0)"]
    end

    subgraph ConsumerLagLLD ["Incident 3: Emergency Consumer Lag Reset Flow"]
        LagSpike["Unrecoverable Consumer Lag Spike"] --> InspectGroup["Execute kafka-consumer-groups.sh --describe"]
        InspectGroup --> StopConsumer["Stop Consumer Service Container"]
        StopConsumer --> ResetOffsets["Execute --reset-offsets --to-latest --execute"]
        ResetOffsets --> CommitNewOffset["Write New Offset Pointer to __consumer_offsets"]
        CommitNewOffset --> RestartConsumer["Start Consumer Service Container"]
    end

    style DiskFull fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style InspectLogDirs fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TargetTopic fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style AlterRetention fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TriggerPurge fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style UnlinkFiles fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc

    style URPAlert fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style FindPartition fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style CheckBroker fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style TriggerRebind fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ReplicaFetch fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ISRJoin fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc

    style LagSpike fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style InspectGroup fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style StopConsumer fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style ResetOffsets fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc
    style CommitNewOffset fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style RestartConsumer fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 stroke:#34d399,stroke-width:2px;
```

---

## 11. Multi-Broker Scale-Out Architecture (Single-Node to 3-Node KRaft)

### 11.1 Multi-Broker Production Override Configuration & Connection Code

```yaml
services:
  llmobs-kafka-1:
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@llmobs-kafka-1:9093,2@llmobs-kafka-2:9093,3@llmobs-kafka-3:9093
      - KAFKA_HEAP_OPTS=-Xms2048m -Xmx2048m
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=3
      - KAFKA_DEFAULT_REPLICATION_FACTOR=3
      - KAFKA_MIN_INSYNC_REPLICAS=2
```

```python
from confluent_kafka import Producer

cluster_producer = Producer({
    'bootstrap.servers': 'kafka1:9092,kafka2:9092,kafka3:9092',
    'client.id': 'multi-node-prod-producer',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 20,
    'batch.size': 65536,
    'max.in.flight.requests.per.connection': 5,
    'compression.type': 'lz4',
    'retries': 10,
    'retry.backoff.ms': 100
})
```

---

### 11.2 Multi-Broker KRaft Cluster Architecture Design (HLD)

```mermaid
graph LR
    subgraph MultiBrokerCluster ["Multi-Broker KRaft Cluster Architecture"]
        B1["Kafka Broker 1 (Node ID 1) - Heap: 2048M"]
        B2["Kafka Broker 2 (Node ID 2) - Heap: 2048M"]
        B3["Kafka Broker 3 (Node ID 3) - Heap: 2048M"]

        B1 -->|KRaft Sync| B2
        B2 -->|KRaft Sync| B3
        B3 -->|KRaft Sync| B1
    end

    style B1 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style B3 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2 stroke:#34d399,stroke-width:2px;
```

---

### 11.3 KRaft Consensus Leader & Partition Replication Protocol (LLD)

```mermaid
graph TB
    subgraph KRaftReplicationLLD ["KRaft Leader Election & Quorum Sync LLD"]
        Controller1["Broker 1 (Active Controller Leader)"] -->|Publish Metadata Record| MetadataLog["@metadata Partition Log"]
        MetadataLog -->|Replicate Metadata Record| Controller2["Broker 2 (Controller Follower)"]
        MetadataLog -->|Replicate Metadata Record| Controller3["Broker 3 (Controller Follower)"]

        subgraph PartitionReplication ["Data Partition Leader & ISR Sync"]
            P_Leader["Partition 0 Leader (Broker 1)"] -->|Fetch Replica Request| P_Follower2["Partition 0 Replica (Broker 2)"]
            P_Leader -->|Fetch Replica Request| P_Follower3["Partition 0 Replica (Broker 3)"]
            P_Follower2 -->|Update LEO in Leader| ISR_Quorum["In-Sync Replicas (ISR Pool)"]
            P_Follower3 -->|Update LEO in Leader| ISR_Quorum
            ISR_Quorum --> AdvanceHW["Advance High Watermark (HW)"]
        end
    end

    style Controller1 fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style MetadataLog fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style Controller2 fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc
    style Controller3 fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc

    style P_Leader fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P_Follower2 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style P_Follower3 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style ISR_Quorum fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc
    style AdvanceHW fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#f8fafc

    linkStyle 0,1,2,3,4,5,6,7 stroke:#34d399,stroke-width:2px;
```
