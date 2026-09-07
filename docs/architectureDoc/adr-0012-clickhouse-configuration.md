# ADR-0012: ClickHouse Configuration — Directive-by-Directive Specification

| Field | Value |
|---|---|
| **Document ID** | ADR-0012 |
| **Status** | Accepted (implemented) |
| **Author(s)** | Principal Infrastructure Architect |
| **Target Repository** | `Chief-Strategist-J/llm-obs-infra` |
| **Date** | 2026-09-07 |
| **Version** | 1.0.0 |
| **Scope** | ClickHouse only (`llmobs-clickhouse-analytics`) |
| **Supersedes** | ADR-0011 Decisions 2 and 7 (ClickHouse portions only) |
| **Validated against** | ClickHouse **26.8.2.7** (`clickhouse/clickhouse-server:latest`, digest `sha256:fa394da8…`) |

---

## 1. Executive Summary

ADR-0011 proposed ClickHouse changes from documentation alone. This ADR replaces that ClickHouse
section with a specification where **every directive was booted against a real ClickHouse container
under the production 4096M cgroup and read back out of `system.server_settings` /
`system.settings`** before being committed.

That process mattered. The configuration as written in ADR-0011 **does not start** — it crashes the
server on metadata load (see §3.1). It also missed a 2 GiB cache the image enables by default, and
missed the largest actual disk-growth source in the service (unbounded system log tables).

Three files are changed:

| File | Nature of change |
|---|---|
| `config/clickhouse/config.d/custom.xml` | Server-level: caches, admission control, logger bounds, system-log TTLs |
| `config/clickhouse/users.d/override.xml` | Profile-level: per-query memory, disk spill, queue and timeout behaviour |
| `docker-compose.yml` | **No change.** The 4096M limit is correct and deliberately retained (§7.1) |

---

## 2. Context

`llmobs-clickhouse-analytics` is the analytics store for LLM telemetry. It runs on a 15 GB / 4-core
host, shares that host with nine other services, and is capped at a 4096M Docker cgroup.

ClickHouse's defaults assume a **16 GB minimum** machine that it owns exclusively. Every default
below is sized for that machine, not for a 4 GiB slice of a shared one. The measured gap:

| Setting | Image default (measured) | Meaning at 4096M |
|---|---|---|
| `mark_cache_size` | **5,368,709,120** (5 GiB) | Ceiling exceeds the entire container |
| `uncompressed_cache_size` | **2,147,483,648** (2 GiB) | Half the container, enabled by the image |
| `max_concurrent_queries` | **0** (unlimited) | No admission control whatsoever |
| `max_connections` | **4,096** | 1,024× the core count |
| `max_memory_usage` | **0** (unlimited per query) | One query may consume the whole server |
| System log TTL | none (except `query_log` at 30 d) | Unbounded growth in `clickhouse_data` |

> These are measured values from `system.server_settings.default` on 26.8.2.7, not quoted docs.
> Two of them differ from what ADR-0011 assumed (§7.2).

---

## 3. Validation Methodology

Because ADR-0011's ClickHouse section was written without execution, this ADR was produced by
running the config before writing the decision:

```bash
docker run -d --name ch-adr-validate --memory 4096m \
  -e CLICKHOUSE_DB=llm_telemetry_analytics -e CLICKHOUSE_USER=default \
  -e CLICKHOUSE_PASSWORD=… -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 \
  --ulimit nofile=262144:262144 \
  -v "$PWD/config/clickhouse/config.d:/etc/clickhouse-server/config.d:ro" \
  -v "$PWD/config/clickhouse/users.d:/etc/clickhouse-server/users.d" \
  clickhouse/clickhouse-server:latest
```

Result: **ready in 6 s, zero `<Error>` lines**, all settings read back at their intended values, all
seven system-log TTLs present in `system.tables.engine_full`, and `max_execution_time` observed
firing (`Code: 159 … TIMEOUT_EXCEEDED`).

### 3.1 The defect this caught

ADR-0011 did not propose system-log TTLs, but the first draft of this ADR did — using a uniform
`<ttl>` element on every log table. That configuration **fails to boot**:

```
<Error> Application: Caught exception while loading metadata:
Code: 36. DB::Exception: If 'engine' is specified for system table, TTL parameters
should be specified directly inside 'engine' and 'ttl' setting doesn't make sense.
(BAD_ARGUMENTS)
```

Cause: the shipped `config.xml` gives **`opentelemetry_span_log` an explicit `<engine>`** (it has no
`event_time`; it is ordered on `finish_date` / `finish_time_us`). ClickHouse forbids a sibling
`<ttl>` when `<engine>` is present. Because `config.d` files *merge into* the shipped config rather
than replacing it, the conflict is invisible from our file alone.

Fix, now in `custom.xml`: for that one table the retention clause lives **inside** the engine spec
and keys off `finish_date`. This is the only table in the stack needing that treatment, and it is
precisely the table this platform cares about most.

---

## 4. What Changed

### 4.1 `config/clickhouse/config.d/custom.xml` — server scope

| ID | Directive | From | To | Decision |
|---|---|---|---|---|
| C-1 | `max_connections` | `1024` | `512` | Bound idle-socket cost. Deliberately kept well above the query-slot count so it is never the limiter |
| C-2 | `keep_alive_timeout` | `300` | `300` | **Reviewed, retained.** All HTTP clients are pooled; C-1 bounds the risk a shorter value would mitigate |
| C-3 | `max_concurrent_queries` | `100` | `16` | Admission control. 4 slots per core. The primary defence against memory amplification |
| C-4 | `max_server_memory_usage` | `3758096384` | unchanged | **Already correct** at 87.5% of the cgroup. ADR-0011 never mentioned it, which weakened its analysis |
| C-5 | `max_server_memory_usage_to_ram_ratio` | (implicit) | `0.9` | Declared explicitly. Already the default — **no behaviour change**; it makes a lowered container limit self-correcting |
| C-6a | `mark_cache_size` | (default 5 GiB) | `536870912` | Default ceiling exceeded the whole container |
| C-6b | `uncompressed_cache_size` | (image: 2 GiB) | `0` | **Not identified by ADR-0011.** Found by reading `system.server_settings` on a live server |
| C-7 | `<logger>` `size`/`count` | (default ~10 GB) | `100M` × `3` | Bounds the in-container file log, which is not a volume and not covered by the compose logging block |
| C-8 | TTL on 7 `system.*_log` tables | none (except `query_log`) | 3 / 7 days | The actual disk growth. ADR-0011 asserted "disk bloat" but proposed only memory controls |

### 4.2 `config/clickhouse/users.d/override.xml` — profile scope

| ID | Directive | From | To | Decision |
|---|---|---|---|---|
| U-1 | `max_memory_usage` | `2147483648` | unchanged | **Already present.** This is why ADR-0011's proposed `dev-limits.xml` was redundant |
| U-2 | `max_memory_usage_for_all_queries` | `3221225472` | unchanged | Obsolete but harmless. Retained while the image is unpinned |
| U-3 | `max_bytes_before_external_group_by` | (off) | `1073741824` | Spill to disk at half of U-1 — the documented ratio |
| U-4 | `max_bytes_before_external_sort` | (off) | `1073741824` | Same |
| U-5 | `queue_max_wait_ms` | (0) | `3000` | **Required partner to C-3.** Shipping C-3 without this would be a downgrade, not an improvement |
| U-6 | `max_execution_time` | (unlimited) | `300` | A slot is scarce once C-3 is 16; a runaway query holding one is now an availability problem |
| U-7 | `use_uncompressed_cache` | (0) | `0` | Declared explicitly. Governs C-6b from the usage side |

**Implemented as an amendment to `override.xml`, not as a new `dev-limits.xml`** — one file owns the
`default` profile.

### 4.3 `docker-compose.yml`

**No change.** See §6.2.

## 5. Configuration Reference

The directive-by-directive reference — **default value, example values, what each setting means,
what it does in this stack, and its trade-off** — lives in the configuration-guide series, in the
same structure as the Kafka guide:

### → [`docs/configDoc/clickhouse-configuration-guide.md`](../configDoc/clickhouse-configuration-guide.md)

| That guide covers | Section |
|---|---|
| **Master Parameter Specifications** — all 36 parameters with definition, expected values, current value, outcome, rationale and scaling notes | §1.1 |
| System-wide HLD / LLD, with integration config and Python | §2 |
| Server memory & cache deep-dive | §3 |
| Query admission control & connections | §4 |
| Per-query resource governance (profile layer) | §5 |
| Container lifecycle, entrypoint & access provisioning | §6 |
| Network, protocol & endpoints | §7 |
| System log retention & physical storage | §8 |
| MergeTree storage, granules, marks & merge mechanics | §9 |
| Emergency CLI runbooks, gotchas, symptom → lever | §10 |
| Multi-node scale-out and the prod memory-drift gap | §11 |

Every component section follows the house pattern: **configuration + Python code → HLD diagram →
LLD diagram → detailed parameter breakdown.**

This split is deliberate. **This ADR records the decision; that guide records the parameters.**

---

## 6. Files Reviewed and Deliberately Unchanged

### 6.1 `config/clickhouse/users.d/default-user.xml`

Reviewed, **not changed by this ADR** — its issues are security, not resources, and belong to the
security audit track. Recorded so the omission is explicit and intentional:

- `<networks><ip>::/0</ip></networks>` accepts connections from any address.
- `<access_management>1</access_management>` lets the shared `default` account `CREATE USER` and `GRANT`.
- The `<default remove="remove"/>`-then-redefine pattern is unusual but functional.

These are already tracked as **H-07** in
`docs/securityDoc/audits/pending/independent-audit-infra-deployment-config.md`. Changing
authentication under a resource-optimization ADR would bury a security decision in the wrong document.

### 6.2 `docker-compose.yml` → `llmobs-clickhouse`

No change. Specifically:

- **`memory: 4096M` retained.** ADR-0011 correctly rejected reducing it, and every value in §4 is
  derived from it. Lowering the container now invalidates C-4 and C-6a.
- **`reservations: 1024M` retained** — a soft floor, correct as-is.
- **`ulimits.nofile: 262144` retained** — ClickHouse's own documented recommendation, and the reason
  C-1 can afford to be generous.
- **`users.d` is mounted read-write** (no `:ro`, unlike `config.d`). Reviewed and left alone: this is
  required by `CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1`. Flagged in the security audit, not here.

---

## 7. Relationship to ADR-0011

### 7.1 Carried forward unchanged

ADR-0011's **rejection** of reducing the ClickHouse container below 4096M is upheld and is the
foundation of this ADR's sizing.

### 7.2 Corrections

| ADR-0011 statement | Correction |
|---|---|
| Mark cache "silently over-allocates marks beyond the cgroup boundary, relying on the Linux page cache as an overflow buffer" | Mechanically wrong. It is a bounded LRU that evicts at its ceiling; the defect is that its *ceiling* (5 GiB) is set above its *enclosure* (4 GiB). Corrected in C-6a. The remediation ADR-0011 proposed was nonetheless right. |
| Decision 7: create a new `users.d/dev-limits.xml` with `max_memory_usage=2147483648` | `users.d/override.xml` **already sets exactly that value**. A second file defining `<profiles><default>` would merge, but leaves two files owning one profile. Implemented as an amendment to `override.xml` instead. |
| Decision 7 makes no mention of `max_server_memory_usage` | It was already present at 3.5 GiB (C-4) and is the primary control. Omitting it made the analysis read as though ClickHouse had no server-level memory protection at all. |
| Decision 2: `<uncompressed_cache_size>0</uncompressed_cache_size>` proposed with the note "rely on OS page cache" | Correct conclusion; the stated premise was incomplete. The image sets it to 2 GiB (not the 8 GiB usually quoted), and the setting that actually governs population is the profile-level `use_uncompressed_cache`. Both are now set (C-6b, U-7). |
| Implied `max_connections` default of 1024 and `max_concurrent_queries` context | Measured defaults on 26.8.2.7 are **4096** and **0 (unlimited)**. The repo's prior values were already reductions from default, not defaults. |
| ADR-0011 §1 cites ClickHouse "disk bloat" | Neither Decision 2 nor 7 addressed disk. Both are memory controls. Actual disk growth (system log tables, in-container file log) is addressed here as C-7 and C-8. |

### 7.3 Prod override drift — flagged, not fixed

`docker-compose.prod.yml` raises ClickHouse to `8192M`, but `max_server_memory_usage` (C-4) is a
hardcoded 3.5 GiB in `config.d`. **Under the prod override ClickHouse would still cap itself at 3.5
GiB and leave ~4.5 GiB unused.**

Not fixed here: prod has no separate `config.d` overlay mount, so correcting it is a structural change
to the prod compose file — outside this ADR's ClickHouse-config scope and requiring its own decision.
Recorded in §9.

---

## 8. Rejected Options

| Option | Verdict |
|---|---|
| Reduce container below `4096M` | **Rejected.** Upholds ADR-0011. ClickHouse documents degraded behaviour under 16 GB; 4 GiB is already aggressive. |
| Reduce `background_pool_size` (default 16) to 8 on a 4-core host | **Rejected.** Merges are I/O-bound and the pool is shared and demand-created. Starving it risks `TOO_MANY_PARTS`, a far worse failure than transient merge-thread contention. |
| Reduce `max_thread_pool_size` (default 10000) | **Rejected.** A ceiling, not a preallocation. Threads are created on demand and already bounded by `max_threads` × `max_concurrent_queries`. Pure churn. |
| Lower `keep_alive_timeout` 300 → 30 (the default) | **Rejected.** See C-2. Pooled clients only; C-1 bounds the socket risk this would mitigate. |
| Disable `metric_log` entirely (`<metric_log remove="1"/>`) | **Rejected.** Cheaper than a TTL, but this is an *observability platform* — deleting the server's own metrics to save disk is the wrong trade. A 3-day TTL bounds it while keeping it queryable. |
| Set `max_memory_usage` per query to 3.5 GiB ÷ 16 = 224 MiB | **Rejected.** Arithmetically tidy, operationally useless — it would reject ordinary analytical queries. Deliberate oversubscription with C-4 as backstop is correct (U-1). |
| Drop `max_memory_usage_for_all_queries` now | **Rejected for this change.** Obsolete but harmless; removal on an unpinned `:latest` image is unnecessary risk for zero benefit. §9. |

---

## 9. Consequences

### Positive

- Config is **verified to boot** on the exact image the stack pulls — including a `BAD_ARGUMENTS`
  crash that the documentation-only approach would have shipped.
- Every cache ceiling now fits inside the container: 5 GiB → 512 MiB marks, 2 GiB → 0 uncompressed.
- Concurrency bounded at 16 with a 3 s queue and a 300 s runaway cap, as one coherent mechanism.
- Large aggregations spill to disk instead of failing.
- Disk growth bounded on both axes ClickHouse actually grows: system log tables (TTL) and the
  in-container file log (300 MB, was ~10 GB).
- One profile file owns the `default` profile, not two.

### Negative / Trade-offs

- **Colder mark cache.** 512 MiB vs 5 GiB means more index re-reads on wide scans. Accepted; revisit
  only alongside a container increase.
- **`max_concurrent_queries=16` may throttle heavy integration tests.** Symptom is
  `TOO_MANY_SIMULTANEOUS_QUERIES` after 3 s. Raise C-3 and U-5 together, never C-3 alone.
- **Spill-to-disk consumes `/var/lib/clickhouse/tmp`** on the 65 GB-free host filesystem. Bounded per
  query by U-1/U-6, but a heavy query is now slower rather than failing fast.
- **`max_execution_time=300` will kill a genuinely long analytical query.** Deliberate: the slot is
  scarce. Override per session where needed.
- **7/3-day system log TTLs shorten the forensic window.** A week-old incident will not have
  `trace_log` rows. Accepted for a dev stack.

### Open items (not fixed here)

1. **Prod memory drift** (§7.3) — `docker-compose.prod.yml` grants 8192M that C-4 caps at 3.5 GiB.
   Needs a prod `config.d` overlay; own decision.
2. **Retroactive TTLs** — config TTLs apply at table *creation*. The `clickhouse_data` volume does
   not currently exist, so this is not needed for the present deployment. If this config is ever
   rolled onto a volume with pre-existing system tables, run the `ALTER TABLE … MODIFY TTL`
   statements in [`clickhouse-configuration-guide.md` §10.3](../configDoc/clickhouse-configuration-guide.md#103-emergency-incident-2-disk-100-full-on-devsda2).
3. **`max_memory_usage_for_all_queries` removal** — obsolete no-op; drop when the image is pinned.
4. **`default-user.xml` network scope and `access_management`** — security track, audit H-07.

---

## 10. Verification

The runnable commands live with the config, in
[`clickhouse-configuration-guide.md` §10.3](../configDoc/clickhouse-configuration-guide.md#103-emergency-incident-2-disk-100-full-on-devsda2) — including the
safe recipe for testing a config change in a throwaway container before committing it.

**Acceptance criteria for this ADR** (all confirmed on ClickHouse 26.8.2.7 under a 4096M cgroup):

| Check | Expected | Result |
|---|---|---|
| Container reaches ready state | two `Ready for connections` events | ✅ 4 s |
| `docker logs … \| grep '<Error>'` | no output | ✅ 0 lines |
| `system.server_settings` | `max_connections=512`, `max_concurrent_queries=16`, `mark_cache_size=536870912`, `uncompressed_cache_size=0`, `max_server_memory_usage=3758096384` | ✅ all |
| `system.settings` | `max_memory_usage=2147483648`, both `max_bytes_before_external_*=1073741824`, `queue_max_wait_ms=3000`, `max_execution_time=300`, `use_uncompressed_cache=0` | ✅ all |
| `system.tables.engine_full` | non-empty TTL on all 7 tables in [guide §8.4](../configDoc/clickhouse-configuration-guide.md#84-retention-detailed-configuration-breakdown), with `opentelemetry_span_log` on `finish_date` | ✅ 7/7 |
| `max_execution_time` enforcement | `Code: 159 … TIMEOUT_EXCEEDED` | ✅ observed |

---

## 11. Compliance Checklist

| # | Change | File | Status |
|---|---|---|---|
| C-1 | `max_connections` 1024 → 512 | `config.d/custom.xml` | ✅ Done |
| C-2 | `keep_alive_timeout` 300 — reviewed, retained | `config.d/custom.xml` | ✅ Reviewed |
| C-3 | `max_concurrent_queries` 100 → 16 | `config.d/custom.xml` | ✅ Done |
| C-4 | `max_server_memory_usage` 3.5 GiB — retained, documented | `config.d/custom.xml` | ✅ Reviewed |
| C-5 | `max_server_memory_usage_to_ram_ratio` 0.9 declared | `config.d/custom.xml` | ✅ Done |
| C-6a | `mark_cache_size` 5 GiB → 512 MiB | `config.d/custom.xml` | ✅ Done |
| C-6b | `uncompressed_cache_size` 2 GiB → 0 | `config.d/custom.xml` | ✅ Done |
| C-7 | Logger file-log bounded to 100M × 3 | `config.d/custom.xml` | ✅ Done |
| C-8 | TTLs on 7 system log tables (span log via `<engine>`) | `config.d/custom.xml` | ✅ Done |
| U-1 | `max_memory_usage` 2 GiB — retained, documented | `users.d/override.xml` | ✅ Reviewed |
| U-2 | `max_memory_usage_for_all_queries` — retained as legacy | `users.d/override.xml` | ✅ Reviewed |
| U-3 | `max_bytes_before_external_group_by` 1 GiB | `users.d/override.xml` | ✅ Done |
| U-4 | `max_bytes_before_external_sort` 1 GiB | `users.d/override.xml` | ✅ Done |
| U-5 | `queue_max_wait_ms` 3000 | `users.d/override.xml` | ✅ Done |
| U-6 | `max_execution_time` 300 | `users.d/override.xml` | ✅ Done |
| U-7 | `use_uncompressed_cache` 0 | `users.d/override.xml` | ✅ Done |
| — | Container limit 4096M unchanged | `docker-compose.yml` | ✅ No change |
| — | ADR-0011 `users.d/dev-limits.xml` **not** created | — | ✅ Superseded by U-1..U-7 |

---

## 12. References

| Document | URL |
|---|---|
| ClickHouse Server Configuration Parameters | https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings |
| ClickHouse `mark_cache_size` | https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#mark_cache_size |
| ClickHouse `max_concurrent_queries` | https://clickhouse.com/docs/en/operations/server-configuration-parameters/settings#max_concurrent_queries |
| ClickHouse System Log Tables | https://clickhouse.com/docs/en/operations/system-tables/query_log |
| ClickHouse Settings Profiles | https://clickhouse.com/docs/en/operations/settings/settings-profiles |
| ClickHouse Memory Settings (`max_memory_usage`) | https://clickhouse.com/docs/en/operations/settings/query-complexity#settings_max_memory_usage |
| ClickHouse Operational Tips (low-memory guidance) | https://clickhouse.com/docs/en/operations/tips |
| ClickHouse Configuration Files (`config.d` merge semantics) | https://clickhouse.com/docs/en/operations/configuration-files |
| **ClickHouse Configuration Guide (36-parameter master list, HLD/LLD, Python, runbooks)** | `docs/configDoc/clickhouse-configuration-guide.md` |
| ADR-0011 — Infrastructure Resource Optimization | `docs/architectureDoc/adr-0011-infrastructure-resource-optimization.md` |
| Independent Infra Audit (H-07, `users.d` write mount) | `docs/securityDoc/audits/pending/independent-audit-infra-deployment-config.md` |
