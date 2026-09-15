# Kubernetes Infrastructure Network Security & Zero-Trust Architecture Audit

| Field | Value |
|---|---|
| Report ID | SAR-LLMOBS-INFRA-AUD-0008 |
| Classification | Confidential |
| Version | 1.0.0 |
| Engagement Type | Independent Architecture, Network Security & Kubernetes Hardening Audit |
| Assessment Date | September 15, 2026 |
| Report Date | September 15, 2026 |
| Target Scope | `llm-obs-infra/k8s/` (Deployments, Services, ConfigMaps, Secrets, Rollouts, and Operations Scripts) |
| Authors | Independent Security & Cloud Infrastructure Architecture Reviewer |
| Status | Open — Remediation Required |
| Remediation Link | [remediation-plan-k8s-network-security.md](./remediation-plan-k8s-network-security.md) |

---

## 1. Executive Summary

This independent security audit evaluates the Kubernetes infrastructure, network security posture, container hardening, and cluster deployment manifests for **`llm-obs-infra`** (`llmobs` namespace) against CIS Kubernetes Benchmarks v1.8, NIST SP 800-53 (SC-7, SC-8, SC-13, AC-4), and NSA/CISA Kubernetes Hardening Guidance.

- **Objective:** Evaluate the 8 container workload deployments (`alloydb`, `clickhouse`, `kafka`, `redis`, `otel-collector`, `tempo`, `grafana`, `temporal`) and 1 Argo Rollout (`canary-rollout`) for network perimeter isolation, intra-cluster traffic encryption, container privilege scoping, and operational script safety.
- **Overall Risk Posture:** **High Risk / Non-Compliant with Zero-Trust Standards**. While the infrastructure includes clean topological ordering, custom health checking, and Argo Rollout integration, the cluster currently operates with **open intra-namespace pod-to-pod networking**, **unencrypted ClusterIP channels**, and **over-privileged container security contexts**.
- **Key Business Impact:** A single compromised frontend or telemetry ingestion container (e.g. `otel-collector`) can perform unrestricted horizontal network scanning and connect directly to internal relational databases (`alloydb`), analytical data stores (`clickhouse`), and workflow engines (`temporal`) without network challenge or transport encryption.

### Severity Summary Breakdown

| Severity | Count | Primary Impact Areas |
|---|---|---|
| Critical (P0) | 2 | Unrestricted pod-to-pod flat network model; Unencrypted plaintext inter-service communication over ClusterIP. |
| High (P1) | 2 | Over-privileged container execution (missing `readOnlyRootFilesystem` and capability drops); Missing Ingress WAF & rate-limiting middlewares. |
| Medium (P2) | 2 | Default ServiceAccount token auto-mounting on non-API workloads; Lack of automated in-cluster TLS certificate lifecycle manager (`cert-manager`). |
| Low (P3) | 1 | Manual bash orchestration lacking CI/CD network policy validation hooks. |

---

## 2. Scope & Rules of Engagement

| Item | Detail |
|---|---|
| In-Scope Assets | `k8s/namespace.yaml`, `k8s/configmap.yaml`, `k8s/secrets.yaml`, `k8s/persistent-volume-claims.yaml`, `k8s/deployments/*.yaml`, `k8s/rollouts/*.yaml`, `k8s/scripts/**/*.sh` |
| Out-of-Scope Assets | Cloud-managed Kubernetes control plane master nodes (GKE/EKS control plane internals) |
| Assessment Type | Static Manifest Analysis, Network Boundary Modeling & Architecture Security Audit |
| Standards Referenced | CIS Kubernetes Benchmark v1.8, NIST SP 800-53 Rev 5, OWASP Cloud-Native Top 10 |

---

## 3. Architecture & Attack Surface Mapping

The infrastructure components in the `llmobs` namespace interact across the following network ports:

| Workload Name | Component Type | Target Pod Port | Internal DNS Endpoint | Ingress Exposure | Risk Level |
|---|---|---|---|---|---|
| `llmobs-alloydb-db` | Relational Metadata DB | `5432/TCP` | `llmobs-alloydb-db.llmobs.svc.cluster.local` | ClusterIP | High |
| `llmobs-clickhouse-analytics` | Analytics Telemetry DB | `8123/TCP`, `9000/TCP` | `llmobs-clickhouse-analytics.llmobs.svc.cluster.local` | ClusterIP | High |
| `llmobs-redis-ledger` | In-Memory Cache | `6379/TCP` | `llmobs-redis-ledger.llmobs.svc.cluster.local` | ClusterIP | Medium |
| `llmobs-kafka-broker` | Event Streaming Bus | `9092/TCP` | `llmobs-kafka-broker.llmobs.svc.cluster.local` | ClusterIP | High |
| `llmobs-otel-collector` | Telemetry Receiver | `4317/TCP`, `4318/TCP` | `llmobs-otel-collector.llmobs.svc.cluster.local` | ClusterIP | Critical |
| `llmobs-tempo-tracing` | Distributed Tracing | `3200/TCP`, `4317/TCP` | `llmobs-tempo-tracing.llmobs.svc.cluster.local` | ClusterIP | Medium |
| `llmobs-grafana-portal` | Dashboard UI | `3000/TCP` | `llmobs-grafana-portal.llmobs.svc.cluster.local` | ClusterIP / Ingress | Medium |
| `llmobs-temporal-engine` | Workflow Orchestrator | `7233/TCP` | `llmobs-temporal-engine.llmobs.svc.cluster.local` | ClusterIP | High |
| `llmobs-canary-rollout` | Service Registry / Canary | `31426/TCP` | `llmobs-service-registry.llmobs.svc.cluster.local` | ClusterIP / Traefik Split | Medium |

---

## 4. Audit Findings & Threat Analysis

### F-001: Unrestricted Flat Intra-Namespace Network Model (Missing NetworkPolicies)
- **Severity:** P0 - Critical
- **CVSS Score:** 9.8 (`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`)
- **Affected Assets:** Entire `llmobs` namespace (`k8s/namespace.yaml`)
- **Description:** No `NetworkPolicy` manifests exist in the `k8s/` root or subdirectories. In standard Kubernetes network plugins (Calico, Cilium, Flannel), default behavior permits all pods to initiate TCP/UDP connections to any other pod.
- **Impact:** Lateral movement vector. A compromised frontend/canary container can initiate unauthorized TCP connections to PostgreSQL (`5432`), ClickHouse (`9000`), or Redis (`6379`) directly, completely bypassing architectural boundaries.

### F-002: Unencrypted Inter-Service Communications over ClusterIP
- **Severity:** P0 - Critical
- **CVSS Score:** 9.0 (`AV:A/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`)
- **Affected Assets:** `deployments/alloydb-relational-db.yaml`, `deployments/clickhouse-analytics-db.yaml`, `deployments/opentelemetry-collector.yaml`, `deployments/kafka-event-broker.yaml`
- **Description:** Internal endpoints in [configmap.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/configmap.yaml) utilize unencrypted protocols (`http://`, plaintext TCP/gRPC on ports 5432, 8123, 9092, 4317, 7233). Workload containers transmit database credentials, telemetry traces, and SQL queries in cleartext across Kubernetes node network interfaces.
- **Impact:** Packet sniffing and man-in-the-middle (MitM) attacks. Any pod with `CAP_NET_RAW` or host-network access on multi-tenant worker nodes can capture sensitive payload data.

### F-003: Over-Privileged Container Security Contexts
- **Severity:** P1 - High
- **CVSS Score:** 7.8 (`AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`)
- **Affected Assets:** All 8 files under `k8s/deployments/*.yaml`
- **Description:** Deployments lack explicit `securityContext` definitions enforcing non-root execution (`runAsNonRoot: true`), read-only root filesystems (`readOnlyRootFilesystem: true`), and capability drops (`capabilities.drop: ["ALL"]`). Containers execute with root (UID 0) inside container namespaces.
- **Impact:** Container breakout and persistence. Exploited vulnerabilities permit attackers to write malicious binaries to root filesystems, tamper with container configurations, or attempt kernel privilege escalation.

### F-004: Lack of Ingress Edge WAF & Rate-Limiting Middlewares
- **Severity:** P1 - High
- **CVSS Score:** 7.5 (`AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`)
- **Affected Assets:** `rollouts/canary-deployment-rollout.yaml`, Traefik Routing Configuration
- **Description:** The edge entry point (`llmobs-canary-rollout` and Grafana ingress) lacks rate-limiting, IP whitelist controls, and security headers (HSTS, `X-Frame-Options`, `X-Content-Type-Options`).
- **Impact:** Denial-of-Service (DoS) and brute-force vulnerability. Unthrottled traffic can saturate the canary rollout and analytical backends under traffic spikes.

### F-005: Unnecessary Automatic ServiceAccount Token Mounting
- **Severity:** P2 - Medium
- **CVSS Score:** 6.5 (`AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`)
- **Affected Assets:** `deployments/redis-ledger-cache.yaml`, `deployments/tempo-trace-storage.yaml`, `deployments/grafana-portal-ui.yaml`
- **Description:** Deployments do not set `automountServiceAccountToken: false`. Kubernetes automatically injects API access tokens into `/var/run/secrets/kubernetes.io/serviceaccount/token` for workloads that have no requirement to interact with the Kubernetes API server.
- **Impact:** Service Account token exfiltration. If a pod is compromised, the token can be used to query or manipulate the Kubernetes API.

### F-006: Absence of Automated In-Cluster Certificate Lifecycle Management
- **Severity:** P2 - Medium
- **CVSS Score:** 5.3 (`AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N`)
- **Affected Assets:** Cluster Infrastructure Architecture
- **Description:** The cluster lacks an automated certificate issuer (such as `cert-manager`). SSL/TLS certificate management relies on static secrets (`secrets.yaml`), leading to certificate expiration risks or shared static key reuse.
- **Impact:** Manual key rotation overhead and risk of unexpected downtime due to expired TLS certificates.

### F-007: Script-Based Cluster Bootstrap Lacking CI/CD Security Validation
- **Severity:** P3 - Low
- **CVSS Score:** 3.3 (`AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N`)
- **Affected Assets:** `k8s/scripts/bootstrap-cluster.sh`, `k8s/scripts/manage.sh`
- **Description:** Operational shell scripts create foundation namespaces and PVCs but do not execute automated validation checks for NetworkPolicies or container security contexts prior to dispatching workloads.
- **Impact:** Configuration drift and deployment of non-compliant manifests into target environments.

---

## 5. Summary Findings Table

| Finding ID | Severity | CVSS Score | Vulnerability Title | Target Manifest / Component | Remediation Status |
|---|---|---|---|---|---|
| **F-001** | Critical (P0) | 9.8 | Unrestricted Intra-Namespace Pod Connectivity | `k8s/namespace.yaml` / Global | Open (Pending Plan) |
| **F-002** | Critical (P0) | 9.0 | Unencrypted Inter-Service ClusterIP Traffic | `k8s/configmap.yaml`, Deployments | Open (Pending Plan) |
| **F-003** | High (P1) | 7.8 | Over-Privileged Container Security Contexts | `k8s/deployments/*.yaml` | Open (Pending Plan) |
| **F-004** | High (P1) | 7.5 | Missing Ingress WAF & Rate-Limiting Middlewares | `k8s/rollouts/canary-deployment-rollout.yaml` | Open (Pending Plan) |
| **F-005** | Medium (P2) | 6.5 | Unnecessary ServiceAccount Token Auto-Mounting | `k8s/deployments/*.yaml` | Open (Pending Plan) |
| **F-006** | Medium (P2) | 5.3 | Absence of Automated Cert Lifecycle Manager | `k8s/` Infrastructure | Open (Pending Plan) |
| **F-007** | Low (P3) | 3.3 | Manual Bootstrap Lacking CI/CD Policy Validation | `k8s/scripts/bootstrap-cluster.sh` | Open (Pending Plan) |
