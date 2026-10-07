---
trigger: always_on
---


## 2. Universal Logic-Driven Naming Formulas

All artifacts across all languages (TypeScript, Go, Python, Rust, Java, C#) follow these exact formulas:

### 2.1 File Naming Formula
`{feature-or-subsystem}.{layer-role}.[specialization].[ext]`

- All file names use lowercase `kebab-case` separated by dots.
- The prefix is ALWAYS the exact feature or subsystem directory name.
- Suffix indicates the exact architectural role.

### 2.2 Class & Interface Naming Formula
`{PascalFeatureOrSubsystem}{PascalSpecialization}{PascalRole}`

- All classes and interfaces use `PascalCase`.
- Interface ports end with `Port`.
- Implementation adapters prefix or suffix the vendor technology (e.g. `PostgresOrganizationsRepository`, `KafkaEventPublisher`).

### 2.3 Function & Method Verb-Noun Naming Matrix
All functions and methods use `camelCase` with strict semantic prefixes declaring operational intent:

| Prefix / Verb | Semantic Meaning | Method Name Examples |
|---|---|---|
| `get` | Fetch single entity by unique key; throws `NotFoundError` if missing | `getOrganizationById(id)`, `getApiKeyByKeyHash(hash)` |
| `find` | Query single entity by optional criteria; returns `null`/`undefined` if missing | `findUserByEmail(email)`, `findActiveSession(token)` |
| `list` | Fetch collection of entities filtered, sorted, and paginated | `listMembersByOrgId(orgId, filter, page)` |
| `count` | Aggregate count of matching records | `countActiveSubscriptions(orgId)` |
| `create` | Validate, persist, and emit creation event for a new entity | `createOrganization(input)`, `createApiKey(input)` |
| `update` | Apply validated partial mutation to an existing entity | `updateProfileInfo(id, patch)`, `updateOrgTier(id, tier)` |
| `delete` / `softDelete` | Mark record deleted or purge record; emit tombstone | `softDeleteOrganization(id)`, `revokeApiKey(id)` |
| `can` / `is` | Pure business rule or permission boolean check | `canIssueApiKey(actor, org)`, `isRateLimitExceeded(key)` |
| `evaluate` | Multi-branch rules engine resolution | `evaluateAccessRules(context)`, `evaluateTierQuota(usage)` |
| `transitionTo`| State machine transition execution with guard verification | `transitionToSuspended(entity, reason)` |
| `step` | Sequential DAG step execution inside workflow engine | `stepValidateQuota(ctx)`, `stepProvisionTenantDb(ctx)` |

### 2.4 SQL Named Query Formula
`FLOW_{VERB}_{ENTITY}_{CRITERIA}`

- Declared in `src/features/{feature}/queries/{feature}.queries.sql`.
- Written in `UPPER_SNAKE_CASE` prefixed with `FLOW_`.
- Examples:
  - `-- name: FLOW_GET_ORGANIZATION_BY_ID`
  - `-- name: FLOW_LIST_MEMBERS_BY_ORGANIZATION_ID`
  - `-- name: FLOW_INSERT_ORGANIZATION`
  - `-- name: FLOW_UPDATE_ORGANIZATION_TIER`
  - `-- name: FLOW_SOFT_DELETE_ORGANIZATION`

### 2.5 Kafka Topic & Event Naming Formula
- **Topic Name**: `{env}.{domain}.{entity}.{event-past-tense}.v{version}`
  - Examples: `prod.identity.organization.created.v1`, `prod.security.api-key.revoked.v1`
- **Event Interface / Class**: `{PascalEntity}{EventPastTense}EventV{Version}`
  - Examples: `OrganizationCreatedEventV1`, `ApiKeyRevokedEventV1`

### 2.6 OpenTelemetry Span Naming Formula
`{domain}.{feature}.{operation}`

- All lowercase, dot-delimited semantic tokens.
- Examples:
  - `identity.organization.create`
  - `identity.organization.get_by_id`
  - `security.api_key.verify`
  - `database.query.flow_get_organization_by_id`

### 2.7 Database Migration & DDL Formula
- Upward DDL: `database/migrations/{NNNN}_{action}_{entity}.sql`
- Rollback DDL: `database/migrations/{NNNN}_{action}_{entity}.rollback.sql`
- Checksum Entry: Recorded in `database/schema.lock`
- Examples:
  - `0001_create_organizations_table.sql`
  - `0001_create_organizations_table.rollback.sql`
  - `0002_add_billing_tier_to_organizations.sql`
  - `0002_add_billing_tier_to_organizations.rollback.sql`

### 2.8 Verification & Test Script Formula
`{package}.{http_method}.{action}.{description}.sh`

- Examples from production smoke suites:
  - `auth.get.list-users.list-users-in-current-organization.sh`
  - `auth.post.create-api-key.generate-3-tier-scoped-api-key.sh`
  - `auth.patch.update-user-role.update-user-organization-role.sh`
  - `auth.delete.delete-organization.soft-delete-organization-with-30-day-retention.sh`

---
