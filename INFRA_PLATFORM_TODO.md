# LLMObs Infrastructure Platform Roadmap & Production Readiness Checklist

This document details critical architectural gaps, production risks, and actionable implementation tasks required to scale the `llm-obs-infra` microservices platform from current baseline infrastructure to enterprise-grade production readiness.

---

## Roadmap Execution Flow

```text
Phase 1 (P0: Data & Network Safety)
  ├── 1. Decouple Stateful Databases from Ephemeral Autoscaling MIGs
  └── 2. Establish Cross-VPC Peering & Cloud DNS Service Discovery

Phase 2 (P1: Traffic, Ingress & Security)
  ├── 3. Internal Load Balancers (L4/L7) for Each Microservice
  ├── 4. GCP Secret Manager Integration (Eliminate Plaintext Secrets)
  └── 5. Private Google Artifact Registry & CI/CD Delivery Pipeline

Phase 3 (P2: Governance, Observability & Hardening)
  ├── 6. GCS Remote Terraform State & Concurrency Locking
  ├── 7. Cloud Monitoring Alert Policies & OTel Trace Aggregation
  └── 8. Identity-Aware Proxy (IAP) Bastionless Access & CMEK Hardening
```

---

## Phase 1: Critical P0 Items (Immediate Reliability & Data Safety)

### 1. Decouple Stateful Services from Ephemeral Autoscaling Nodes
- [ ] **Risk Analysis**: 
  - Each microservice currently runs AlloyDB/PostgreSQL, Redis, and Kafka in Docker Compose on nodes managed by an **Autoscaling Managed Instance Group (MIG)**.
  - Scale-in events and auto-healing health check failures destroy the VM and its boot disk, causing **permanent data loss**.
- [ ] **Action Items**:
  - [ ] **Option A (Cloud Native)**: Provision Managed Cloud SQL / AlloyDB Omni and Memorystore for Redis outside the MIG.
  - [ ] **Option B (Stateful Disks)**: Attach independent regional persistent disks (`google_compute_disk`) and configure `stateful_disk` policies in `google_compute_instance_group_manager`.
  - [ ] Configure automated daily volume snapshots (`google_compute_resource_policy`) with 30-day retention and Point-in-Time-Recovery (PITR).
  - [ ] Separate the stateless application API layer (autoscaled) from the stateful datastore layer (fixed, persistent).

### 2. Cross-VPC Networking & Service Discovery (Break VPC Islands)
- [ ] **Risk Analysis**:
  - The 6 microservices reside in isolated VPCs (`10.0.10.0/24` to `10.0.60.0/24`) without routes between them.
  - Inter-service communication (e.g., `payment` calling `user`, or all services emitting to `audit`) fails internally.
- [ ] **Action Items**:
  - [ ] **Option A (VPC Peering Mesh)**: Provision bilateral `google_compute_network_peering` connecting each service VPC.
  - [ ] **Option B (Shared VPC Hub-and-Spoke)**: Migrate subnets into a unified host VPC with dedicated service projects.
  - [ ] **Private Cloud DNS (`google_dns_managed_zone`)**:
    - Configure private zone `llmobs.internal` accessible across all VPCs.
    - Add DNS records: `auth.llmobs.internal`, `user.llmobs.internal`, `payment.llmobs.internal`, etc.
  - [ ] Create least-privilege inter-service firewall rules allowing traffic only on specific gRPC/HTTP API ports between subnet CIDRs.

---

## Phase 2: High-Priority P1 Items (Traffic Management & Security)

### 3. Internal Load Balancing & Zero-Downtime Rolling Updates
- [ ] **Risk Analysis**:
  - Ephemeral instance IPs change during autoscaling; callers cannot route traffic predictably to new instances without a static endpoint.
- [ ] **Action Items**:
  - [ ] Provision Regional Internal Application Load Balancers (L7) or Internal TCP Load Balancers (L4) for each microservice stack:
    - `google_compute_region_backend_service` pointing to the MIG instance group.
    - `google_compute_forwarding_rule` with a static internal IP.
  - [ ] Configure zero-downtime rolling update policy in each MIG:
    ```hcl
    rolling_update_policy {
      type                  = "PROACTIVE"
      minimal_action        = "REPLACE"
      max_surge_fixed       = 1
      max_unavailable_fixed = 0
      min_ready_sec         = 60
    }
    ```
  - [ ] Deploy Cloud Armor security policies on external ingress to defend against DDoS and automated attacks.

### 4. Secret Management & Identity Governance
- [ ] **Risk Analysis**:
  - Passwords, keys, and tokens are stored in `.env` files and transferred in plaintext over SSH/SCP.
- [ ] **Action Items**:
  - [ ] Provision **GCP Secret Manager** (`google_secret_manager_secret`):
    - `user-db-credentials`
    - `auth-jwt-private-key`
    - `payment-stripe-secret`
  - [ ] Grant `roles/secretmanager.secretAccessor` to each service's dedicated Service Account.
  - [ ] Update `startup.sh` or Docker entrypoint to dynamically pull secrets into memory via `gcloud secrets versions access` at runtime:
    ```bash
    export DB_PASSWORD=$(gcloud secrets versions access latest --secret="user-db-password")
    ```
  - [ ] Remove all plaintext credentials from git tracking and version control history.

### 5. Private Artifact Registry & Automated Delivery Pipeline
- [ ] **Risk Analysis**:
  - Production nodes pull unverified images from public Docker Hub or rely on ad-hoc on-node builds.
- [ ] **Action Items**:
  - [ ] Provision **Google Artifact Registry** (`google_artifact_registry_repository`):
    - Repository type: `DOCKER`, location: `us-central1`.
  - [ ] Grant `roles/artifactregistry.reader` to instance Service Accounts.
  - [ ] Create GitHub Actions / Cloud Build pipeline:
    - Linting and vulnerability scanning (Trivy / Snyk).
    - Immutable semantic tag push: `us-central1-docker.pkg.dev/<project>/llmobs/<service>:${COMMIT_SHA}`.
    - Automated deployment triggers updating instance template image versions.

---

## Phase 3: Platform P2 Items (Governance, Observability & Hardening)

### 6. Remote Terraform State & Concurrency Locking
- [ ] **Risk Analysis**:
  - State files (`terraform.tfstate`) are stored locally; multi-engineer runs or CI/CD deployments risk state corruption and split-brain infrastructure.
- [ ] **Action Items**:
  - [ ] Create GCS bucket `llmobs-tfstate-<project-id>` with **Object Versioning** and **Uniform Bucket-Level Access**.
  - [ ] Update each service's `main.tf` with the remote backend configuration:
    ```hcl
    terraform {
      backend "gcs" {
        bucket = "llmobs-tfstate-your-project-id"
        prefix = "services/user"
      }
    }
    ```
  - [ ] Automate state backup and establish an access policy restricting backend writes to authorized CI/CD service principals.

### 7. Centralized Observability & SRE Alerting
- [ ] **Risk Analysis**:
  - Metrics and logs are sent to GCP, but there are no threshold alert policies, SLO monitors, or dashboards to notify engineers during outages.
- [ ] **Action Items**:
  - [ ] Configure `google_monitoring_alert_policy` rules:
    - **Host High CPU**: Alert when average CPU exceeds 85% for > 5 minutes.
    - **Disk Space Exhaustion**: Alert when disk usage exceeds 80%.
    - **CrashLoop / Health Check Failure**: Alert when healthy instances drop below `min_replicas`.
  - [ ] Configure OpenTelemetry Collectors on nodes to ship traces and metrics directly to Cloud Trace and Prometheus/Cloud Monitoring.
  - [ ] Configure notification channels (PagerDuty, Slack webhook, email) in Terraform.

### 8. Security Hardening & Zero-Trust Access
- [ ] **Risk Analysis**:
  - SSH port 22 is open to `0.0.0.0/0` across all subnets; nodes have public NAT exposure.
- [ ] **Action Items**:
  - [ ] **Enforce Identity-Aware Proxy (IAP) for SSH**:
    - Restrict SSH firewall rules strictly to the Google IAP proxy CIDR: `35.235.240.0/20`.
    - Eliminate external public IP addresses from compute instances (`assign_public_ip = false`).
    - Connect securely without public IPs via:
      `gcloud compute ssh <instance> --tunnel-through-iap --zone=<zone>`
  - [ ] **Customer Managed Encryption Keys (CMEK)**:
    - Encrypt boot disks and persistent storage using Cloud KMS keys (`google_kms_crypto_key`).
  - [ ] **Audit Logging**:
    - Enable Cloud Audit Logs for `DATA_READ`, `DATA_WRITE`, and `ADMIN_READ` across all service APIs.

---

## Quick Reference: Priority Matrix

| Priority | Area | Risk Addressed | Implementation Effort |
|---|---|---|---|
| **P0** | Stateful Datastore Decoupling | Permanent database loss during autoscaling | Medium |
| **P0** | Cross-VPC Peering & Cloud DNS | Microservices unable to communicate internally | Medium |
| **P1** | Internal Load Balancers | Inability to distribute traffic across autoscaled nodes | Medium |
| **P1** | Secret Manager Integration | Plaintext passwords exposed in `.env` and disk | Low |
| **P1** | Artifact Registry & CI/CD | Untrusted images and manual deployment drift | Medium |
| **P2** | GCS Remote Terraform Backend | Team state collisions and concurrency corruption | Low |
| **P2** | Monitoring & Alert Policies | Unmonitored production incidents and crash loops | Medium |
| **P2** | IAP Bastionless SSH & CMEK | Exposed SSH port and unencrypted data at rest | Low |
