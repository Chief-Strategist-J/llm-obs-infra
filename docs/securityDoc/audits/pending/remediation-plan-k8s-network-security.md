# Remediation Plan: Kubernetes Network Security & Zero-Trust Architecture (AUD-0008)

| Field | Value |
|---|---|
| Remediation Plan ID | REM-LLMOBS-INFRA-AUD-0008 |
| Target Audit Report | [independent-audit-k8s-network-security.md](./independent-audit-k8s-network-security.md) |
| System / Component | `llm-obs-infra/k8s` (`llmobs` namespace) |
| Author | Infrastructure Security Engineering Team |
| Status | Open — Approved for Execution |
| Target Completion Date | September 30, 2026 |

---

## 1. Executive Summary & Remediation Strategy

This technical remediation plan provides the concrete manifest code changes, architecture patches, file additions, and automated verification commands required to resolve all 7 security findings identified in **SAR-LLMOBS-INFRA-AUD-0008**.

### Key Action Plan Items:
1. **Network Micro-segmentation:** Implement default-deny-all `NetworkPolicy` objects and ingress/egress rules per microservice.
2. **In-Transit Encryption:** Enforce TLS/SSL mode on database drivers and telemetry pipelines; deploy `cert-manager`.
3. **Container Security Hardening:** Inject strict `securityContext` parameters (`runAsNonRoot`, `readOnlyRootFilesystem`, capability drops) across all workload manifests.
4. **Ingress Protection:** Add Traefik Rate Limiting and HSTS Security Headers.
5. **Script Toolchain Update:** Update bootstrap and management bash scripts to enforce security policies.

---

## 2. Remediation Tasks by Finding

### Task 1: Resolve F-001 — Implement Network Micro-segmentation (`NetworkPolicy`)

- **Target Files:**
  - `[NEW]` [k8s/network-policies/00-default-deny-all.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/network-policies/00-default-deny-all.yaml)
  - `[NEW]` [k8s/network-policies/01-allow-dns.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/network-policies/01-allow-dns.yaml)
  - `[NEW]` [k8s/network-policies/allow-alloydb.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/network-policies/allow-alloydb.yaml)
  - `[NEW]` [k8s/network-policies/allow-clickhouse.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/network-policies/allow-clickhouse.yaml)
  - `[NEW]` [k8s/network-policies/allow-otel-collector.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/network-policies/allow-otel-collector.yaml)

#### Manifest Code: `00-default-deny-all.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: llmobs
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

#### Manifest Code: `allow-alloydb.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-alloydb-access
  namespace: llmobs
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: alloydb
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: backend
      ports:
        - protocol: TCP
          port: 5432
```

- [ ] Create `k8s/network-policies/` directory.
- [ ] Apply `00-default-deny-all.yaml` and `01-allow-dns.yaml`.
- [ ] Apply service-specific ingress rules for AlloyDB, ClickHouse, Redis, Kafka, OTEL Collector, and Temporal.
- [ ] **Verification Command:**
  ```bash
  kubectl get netpol -n llmobs
  # Verify blocked unauthorized connection:
  kubectl run net-test --rm -i --tty --image=alpine -n llmobs -- nc -zv llmobs-alloydb-db 5432 (Should timeout)
  ```

---

### Task 2: Resolve F-002 & F-006 — Enforce TLS In-Transit Encryption & Certificate Manager

- **Target Files:**
  - `[MODIFY]` [k8s/configmap.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/configmap.yaml)
  - `[MODIFY]` [k8s/deployments/alloydb-relational-db.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/deployments/alloydb-relational-db.yaml)
  - `[MODIFY]` [k8s/deployments/opentelemetry-collector.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/deployments/opentelemetry-collector.yaml)

#### Code Changes in `alloydb-relational-db.yaml`:
```yaml
spec:
  template:
    spec:
      containers:
        - name: alloydb
          args:
            - "postgres"
            - "-c"
            - "ssl=on"
            - "-c"
            - "ssl_cert_file=/etc/postgres-certs/tls.crt"
            - "-c"
            - "ssl_key_file=/etc/postgres-certs/tls.key"
          volumeMounts:
            - name: alloydb-tls
              mountPath: /etc/postgres-certs
              readOnly: true
      volumes:
        - name: alloydb-tls
          secret:
            secretName: alloydb-tls-credentials
```

- [ ] Install `cert-manager` in cluster infrastructure.
- [ ] Issue ClusterIssuer and TLS Certificate secrets for `llmobs-alloydb-db` and `llmobs-clickhouse-analytics`.
- [ ] Update [k8s/configmap.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/configmap.yaml) to reference HTTPS/gRPC TLS endpoints.
- [ ] **Verification Command:**
  ```bash
  kubectl exec -it deployment/llmobs-alloydb-db -n llmobs -- psql -U admin -d llm_observability -c "SHOW ssl;"
  ```

---

### Task 3: Resolve F-003 & F-005 — Container Security Context & ServiceAccount Hardening

- **Target Files:**
  - `[MODIFY]` All files under `k8s/deployments/*.yaml`

#### Code Injection for Deployment Spec:
```yaml
spec:
  template:
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
        - name: service-name
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
```

- [ ] Add `automountServiceAccountToken: false` to all workloads.
- [ ] Inject `securityContext` block with non-root user (UID 10001), `readOnlyRootFilesystem: true`, and capability drop `ALL`.
- [ ] Configure `tmpfs` volume mounts for containers requiring `/tmp` scratch directories.
- [ ] **Verification Command:**
  ```bash
  kubectl get pods -n llmobs -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'
  ```

---

### Task 4: Resolve F-004 — Ingress Rate Limiting & Security Headers

- **Target Files:**
  - `[NEW]` [k8s/ingress/traefik-security-middleware.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/ingress/traefik-security-middleware.yaml)
  - `[MODIFY]` [k8s/rollouts/canary-deployment-rollout.yaml](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/rollouts/canary-deployment-rollout.yaml)

#### Manifest Code: `traefik-security-middleware.yaml`
```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: security-headers-and-ratelimit
  namespace: llmobs
spec:
  rateLimit:
    average: 100
    burst: 200
  headers:
    sslRedirect: true
    stsSeconds: 31536000
    browserXssFilter: true
    contentTypeNosniff: true
    frameDeny: true
```

- [ ] Create Traefik Security Middleware definition.
- [ ] Attach middleware annotation to `llmobs-canary-rollout` ingress.
- [ ] **Verification Command:**
  ```bash
  curl -I http://llmobs.local/health | grep -E "Strict-Transport-Security|X-Frame-Options"
  ```

---

### Task 5: Resolve F-007 — Script Toolchain & CI Policy Integration

- **Target Files:**
  - `[MODIFY]` [k8s/scripts/common.sh](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/scripts/common.sh)
  - `[MODIFY]` [k8s/scripts/bootstrap-cluster.sh](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/scripts/bootstrap-cluster.sh)
  - `[MODIFY]` [k8s/scripts/manage.sh](file:///home/btpl-lap-22/live/llm-obs-infra/k8s/scripts/manage.sh)

- [ ] Add `ensure_network_policies()` helper function to `common.sh`.
- [ ] Update `bootstrap-cluster.sh` to apply network policies automatically during cluster bootstrapping.
- [ ] Add `manage.sh network-audit` command to verify active NetworkPolicies and pod security states.
- [ ] **Verification Command:**
  ```bash
  ./k8s/scripts/manage.sh health
  ```

---

## 3. Verification & Sign-Off Matrix

| Finding ID | Title | Verification Method | Owner | Status |
|---|---|---|---|---|
| **F-001** | Network Micro-segmentation | `kubectl get netpol -n llmobs` & connection probes | DevOps / Security | Pending |
| **F-002** | In-Transit TLS Encryption | Port SSL queries (`psql -c "SHOW ssl;"`, OTLP TLS handshake) | Security Eng | Pending |
| **F-003** | SecurityContext Hardening | `kubectl get pods -o json` checking `readOnlyRootFilesystem` | SecOps | Pending |
| **F-004** | Traefik WAF & Rate-Limit | `curl -I` header verification & load burst testing | SRE Team | Pending |
| **F-005** | SA Token Auto-Mounting | Inspecting `/var/run/secrets/kubernetes.io/serviceaccount` | Security Eng | Pending |
| **F-006** | Cert-Manager Integration | `kubectl get certificate -n llmobs` | DevOps | Pending |
| **F-007** | Script CI/CD Policy Check | `./k8s/scripts/manage.sh health` execution | Infra Team | Pending |
