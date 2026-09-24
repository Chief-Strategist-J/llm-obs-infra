# CRITICAL INFRASTRUCTURE TODO & PRODUCTION DEFECT REMEDIATION

This document tracks **only high-severity, production-blocking architectural defects** in the `llm-obs-infra` microservices platform. Every item listed here poses an immediate risk of **permanent data loss, split-brain data corruption, complete service outage, or security compromise**.

---

## Critical Severity Matrix (Production Killers)

| # | Critical Vulnerability / Defect | Failure Mode | Severity | Impact |
|---|---|---|---|---|
| **1** | **Databases on Autoscaled Ephemeral Nodes** | Node scale-in or auto-healing deletes VM disk; data is destroyed | **CRITICAL P0** | **Permanent Data Loss** |
| **2** | **Kafka & Database Split-Brain Upon Scaling** | When MIG scales to 2+ nodes, multiple un-replicated DBs and Kafkas run concurrently | **CRITICAL P0** | **Data Corruption & Lost Events** |
| **3** | **Isolated VPCs (No Cross-Service Routing)** | Microservices reside in separate VPCs with no routes or peering | **CRITICAL P0** | **Inter-Service Deadlock** |
| **4** | **Single Availability Zone Failure** | All resources locked to `us-central1-a`; single DC failure brings down platform | **CRITICAL P0** | **Total Downtime** |
| **5** | **Cloud NAT Port Exhaustion Under LLM Load** | Concurrent outbound LLM API calls exhaust NAT ports, dropping requests | **CRITICAL P0** | **Silent API Timeouts** |
| **6** | **Unbounded Boot Disk Log Exhaustion** | Docker, Postgres WAL, and Kafka logs fill 50GB root disk; node hangs | **CRITICAL P1** | **Host Crash & Docker Hang** |
| **7** | **No Load Balancers for Autoscaled Replicas** | No stable VIP or L4/L7 routing across dynamically spawned nodes | **CRITICAL P1** | **Unreachable New Replicas** |
| **8** | **Plaintext Credentials on Disk & In Git** | Default passwords stored in `.env` and version control | **CRITICAL P1** | **Full Credential Compromise** |
| **9** | **GCP Project Quota Ceiling Collision** | Scaling 6 services x 3 nodes hits GCP default CPU and SSD quotas | **CRITICAL P1** | **Autoscaling Allocation Failure** |
| **10**| **Local Terraform State Concurrency Risk** | State stored in local `.tfstate`; team or CI runs cause split-brain infra | **CRITICAL P1** | **Infrastructure Destruction** |

---

## 1. Permanent Data Loss: Databases on Autoscaling Nodes
- [x] **Mitigated / Fixed for Root Platform Stack**:
  - Attached persistent host storage volume bindings in `docker-compose.prod.yml` mapping `alloydb_data`, `alloydb_archive`, `redis_data`, `kafka_data`, `clickhouse_data`, and `tempo_data` to `${LLMOBS_DATA_DIR:-/mnt/disks/llmobs-data}`.
  - Added dedicated `redis_data:/data` volume mount in `docker-compose.yml` to prevent ephemeral Redis loss.
  - Added `stop_grace_period: 60s` to AlloyDB, Kafka, ClickHouse, and Redis to ensure transactional checkpoints and commit logs are completely flushed to disk prior to shutdown.
  - Created automated storage initialization script `scripts/prepare-persistent-storage.sh`.
- [x] **Mitigated / Fixed for Microservices**:
  - Bound microservice databases, redis ledgers, and kafka brokers across `services/{audit,auth,notifications,payment,storage,user}/docker-compose.yml` to `${LLMOBS_DATA_DIR:-./data}/...`.
  - Added safe shutdown grace periods (`60s` for DBs/Kafka, `30s` for Redis) to protect from abrupt kill signals.
  - Injected non-destructive `ensure_data_storage` function into all `services/*/scripts/deploy.sh` to auto-initialize directories with `0777` permissions or reuse existing data.
- [x] **Mitigated / Fixed for Kubernetes Stack (`k8s/`)**:
  - Added dedicated `redis-data-pvc` (10Gi RWO) to `k8s/persistent-volume-claims.yaml`.
  - Mounted `/data` in `k8s/deployments/redis-ledger-cache.yaml` with `--dir /data --appendonly yes` persistence flags.
  - Updated `k8s/scripts/common.sh` to classify Redis as `stateful`, ensuring storage claims are applied before deployment.

---

## 2. Split-Brain Data Corruption: Multiple Un-Replicated Nodes
- [ ] **Defect**:
  - When autoscaler triggers and scales a service from 1 to 2 or 3 instances, **each new VM boots its own local PostgreSQL and local Kafka container**.
  - Requests hitting Node 1 write to Database 1; requests hitting Node 2 write to Database 2.
  - Events published on Node 1 never reach consumers on Node 2.
- [ ] **Critical Fix**:
  - Keep the autoscaled compute layer **strictly stateless** (only APIs, proxy layers, workers).
  - Centralize the datastore and event streaming bus so all compute replicas connect to a single authoritative cluster (or primary-replica setup).

---

## 3. Inter-Service Deadlock: Isolated VPC Networks
- [ ] **Defect**:
  - Each microservice is deployed into its own separate VPC (`llmobs-auth-vpc`, `llmobs-payment-vpc`, etc.).
  - There are no routes, peerings, or shared networks connecting them.
  - Service-to-service calls (e.g. `payment` calling `auth` or `user`) cannot reach private IPs and fail immediately.
- [ ] **Critical Fix**:
  - Provision **VPC Network Peering** (`google_compute_network_peering`) in a full mesh between the 6 VPCs, or
  - Consolidate all 6 service subnets into a single **Shared VPC** or **Hub-and-Spoke** network.
  - Deploy **Private Cloud DNS** (`*.llmobs.internal`) with resolution across all subnets.

---

## 4. Total Outage Risk: Single Availability Zone Lock
- [ ] **Defect**:
  - All compute instances and subnets are hardcoded to a single availability zone (`us-central1-a`).
  - If Google Cloud zone `us-central1-a` suffers hardware degradation or an outage, the entire microservices stack goes offline.
- [ ] **Critical Fix**:
  - Convert `google_compute_instance_group_manager` to **Regional Managed Instance Group (Regional MIG)** (`google_compute_region_instance_group_manager`).
  - Distribute node instances evenly across 3 availability zones (`us-central1-a`, `us-central1-b`, `us-central1-c`).

---

## 5. Silent API Drop: Cloud NAT Port Exhaustion Under LLM Load
- [ ] **Defect**:
  - The platform issues thousands of concurrent outbound API calls to LLM providers (OpenAI, Anthropic) and third-party gateways.
  - Default Cloud NAT configuration assigns minimal ephemeral ports per VM.
  - Under load, NAT port pools exhaust, resulting in silent socket timeouts, failed LLM completions, and dropped payment webhooks.
- [ ] **Critical Fix**:
  - In `google_compute_router_nat`:
    - Configure `min_ports_per_vm = 4096` (or calculate based on expected concurrent socket count).
    - Enable `enable_endpoint_independent_mapping = false` to preserve port allocation.
    - Allocate multiple static external IP addresses to the NAT gateway.

---

## 6. Host Crash: Unbounded Boot Disk Exhaustion
- [ ] **Defect**:
  - Docker containers, Postgres WAL logs, Kafka partition segments, and system journal logs all write to the single 50GB root disk (`/`).
  - When disk usage hits 100%, the Docker daemon deadlocks, SSH fails, health check probes fail, and instances enter an unrecoverable crash loop.
- [ ] **Critical Fix**:
  - Attach a **dedicated secondary disk** mounted at `/var/lib/docker`.
  - Install the **Google Cloud Ops Agent** to stream system and container logs off-box to Cloud Logging immediately.
  - Configure log rotation in `/etc/docker/daemon.json` with strict upper bounds (`max-size: 50m`, `max-file: 3`).

---

## 7. Traffic Blindness: Missing Internal Load Balancers
- [ ] **Defect**:
  - When the autoscaler spawns new instances, they receive ephemeral IPs.
  - There is no load balancer or virtual IP in front of the MIG to balance traffic across the instances.
  - Calling services only know about one IP, so additional scaled instances sit 100% idle while the primary instance crashes under load.
- [ ] **Critical Fix**:
  - Deploy an **Internal TCP/UDP Load Balancer (ILB)** or **Regional Internal Application Load Balancer** (`google_compute_region_backend_service`) in front of each service's MIG.
  - Map static internal IP addresses or private DNS names (`auth.internal.llmobs`, etc.) to the load balancer forwarding rules.

---

## 8. Full Security Breach: Hardcoded Credentials on Disk & Git
- [ ] **Defect**:
  - Default passwords (e.g. `user_s3cret_2026`) and configuration variables are stored in plaintext `.env` files and synced via SSH.
  - If any node is compromised, all database and message bus credentials are leaked in cleartext.
- [ ] **Critical Fix**:
  - Provision **Google Cloud Secret Manager** (`google_secret_manager_secret`).
  - Grant `roles/secretmanager.secretAccessor` strictly to each service's dedicated Service Account.
  - Inject secrets into container processes in-memory at boot time without saving `.env` files to disk.

---

## 9. Autoscaler Failure: GCP Project Quota Saturation
- [ ] **Defect**:
  - 6 microservices x 3 max replicas = up to 18 `e2-standard-4` instances (72 vCPUs, 288GB RAM, 900GB SSD).
  - Default GCP projects have strict regional quotas (often 24 to 32 vCPUs and limited SSD quotas).
  - During a traffic spike, autoscaling requests will be rejected by GCP with `QUOTA_EXCEEDED` or `ZONE_RESOURCE_POOL_EXHAUSTED`.
- [ ] **Critical Fix**:
  - Request quota increases in Google Cloud Console for `CPUS_ALL_REGIONS` and `IN_USE_ADDRESSES`.
  - Configure machine sizing according to actual workload demand (e.g. `e2-standard-2` or `e2-medium` for lower-tier services).

---

## 10. Split-Brain Infrastructure: Local Terraform State
- [ ] **Defect**:
  - Terraform state is stored locally in `terraform.tfstate`.
  - Multiple engineers or CI/CD pipelines will operate on divergent local states, causing duplicate resource creations, lock errors, and accidental deletions.
- [ ] **Critical Fix**:
  - Provision a secure, version-controlled GCS bucket (`llmobs-tfstate-<project-id>`).
  - Add the remote backend to `main.tf`:
    ```hcl
    terraform {
      backend "gcs" {
        bucket = "llmobs-tfstate-<project-id>"
        prefix = "services/<service_name>"
      }
    }
    ```
