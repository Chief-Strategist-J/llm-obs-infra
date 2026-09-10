# CI/CD Pipeline Comprehensive Architecture, Parameter Deep-Dive & Operational Guide

> **Validated against GitHub Actions Runner `ubuntu-latest` (Ubuntu 24.04 LTS), ShellCheck v0.10+, kubeconform v0.6.7, Docker Buildx v0.17+, Argo Rollouts CLI v1.7+**. Every workflow configuration in this document is set to `workflow_dispatch` only — no automatic triggers are active. Pipelines fire exclusively when manually dispatched from the GitHub Actions UI.
>
> Companion guides: [`alloydb-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/alloydb-configuration-guide.md) · [`clickhouse-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/clickhouse-configuration-guide.md) · [`kafka-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/kafka-configuration-guide.md) · [`otel-collector-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/otel-collector-configuration-guide.md) · [`kubernetes-deployment-configuration-guide.md`](file:///home/btpl-lap-22/live/llm-obs-infra/docs/configDoc/kubernetes-deployment-configuration-guide.md)

---

## 1. Executive Master Parameter Reference Specifications

To avoid scrolling back and forth between sections, this master reference provides an immediate, unified list of every CI/CD pipeline parameter, its definitions, expected values, currently configured values, outcomes, trade-offs, and system impacts.

### 1.1 Shared Workflow Infrastructure Parameters

1. **Parameter**: `on: workflow_dispatch`
   - **Definition**: GitHub Actions trigger type that allows manual execution from the repository's Actions tab. When `workflow_dispatch` is the sole trigger, the workflow never runs automatically on push, pull request, tag, or release events.
   - **Expected Values**: Present as the only entry under `on:` in all 5 workflows
   - **Currently Configured Value**: Active in all 5 workflow files
   - **Outcome / System Impact**: Prevents any accidental pipeline execution when pushing code or creating pull requests. The workflow appears in GitHub's Actions tab with a "Run workflow" button that accepts input parameters. Without this, pushing any commit matching the old path filters would trigger builds, consuming GitHub Actions minutes and potentially publishing artifacts prematurely.
   - **Why & When to Configure It**: Set as the sole trigger because the infrastructure is in setup phase. When ready for automatic CI/CD, add `push:` and `pull_request:` triggers with `paths:` filters back to the relevant workflows. The `workflow_dispatch` inputs remain functional alongside automatic triggers.
   - **Scaling & Troubleshooting**: If the "Run workflow" button does not appear in the GitHub UI, verify the workflow file exists on the repository's default branch. GitHub only shows `workflow_dispatch` buttons for workflows present on the default branch — not feature branches.

---

2. **Parameter**: `permissions: contents: read`
   - **Definition**: GitHub Actions OIDC token permissions scope. Restricts the `GITHUB_TOKEN` to read-only access on repository contents. This follows the principle of least privilege — workflows should only have the permissions they actually need.
   - **Expected Values**: `contents: read` for validation-only workflows, `contents: read` + `packages: write` for the Docker image build workflow
   - **Currently Configured Value**: `contents: read` on 4 workflows, `contents: read` + `packages: write` on `docker-image-build.yml`
   - **Outcome / System Impact**: Without explicit `permissions:`, GitHub Actions inherits the repository-level default permissions, which may include `write` access to issues, pull requests, packages, and deployments. An explicit `contents: read` block prevents the workflow from accidentally modifying repository contents, creating releases, or pushing packages unless specifically authorized.
   - **Why & When to Configure It**: Security hardening. A compromised or buggy step script with unrestricted `GITHUB_TOKEN` could modify files, create releases, or push packages. The `packages: write` addition on the image build workflow is required because `docker/login-action` uses `GITHUB_TOKEN` to authenticate with GitHub Container Registry (ghcr.io), which requires write access to the `packages` scope.
   - **Scaling & Troubleshooting**: If a workflow step fails with a 403 Permission Denied error on a GitHub API call, the `permissions` block is too restrictive. Add only the specific permission needed (e.g. `issues: write` for commenting on PRs). Never set `permissions: write-all` as a blanket fix.

---

3. **Parameter**: `runs-on: ubuntu-latest`
   - **Definition**: The GitHub-hosted runner environment. `ubuntu-latest` resolves to the latest Ubuntu LTS image (currently Ubuntu 24.04) provided by GitHub. This image includes Docker, Python 3, curl, git, and standard build tools pre-installed.
   - **Expected Values**: `ubuntu-latest` for all workflows
   - **Currently Configured Value**: `ubuntu-latest` in all 5 workflows
   - **Outcome / System Impact**: Provides a clean, ephemeral Linux VM for each workflow run. The runner is destroyed after the job completes, ensuring no state leaks between runs. Docker is pre-installed, which is required for the Compose profile validation workflow and the Docker image build workflow.
   - **Why & When to Configure It**: `ubuntu-latest` is used instead of pinning (e.g. `ubuntu-24.04`) because the workflows do not depend on OS-level specifics. Pin to a specific version only if a workflow breaks on a runner update. Self-hosted runners (`self-hosted`) would be needed for workflows requiring cluster access (e.g. the canary rollout workflow connecting to a real Kubernetes cluster).
   - **Scaling & Troubleshooting**: GitHub-hosted runners have 7 GB RAM, 2 CPUs, and 14 GB SSD. If a workflow exceeds these limits (e.g. building very large Docker images), switch to a larger runner (`ubuntu-latest-large` with 16 GB RAM) or a self-hosted runner. Runner queue times during peak hours (typically US business hours) may cause delayed starts — this is a GitHub infrastructure constraint, not a configuration issue.

---

4. **Parameter**: `uses: actions/checkout@v4`
   - **Definition**: Official GitHub Action that clones the repository into the runner's workspace (`$GITHUB_WORKSPACE`). Version `v4` uses Node.js 20 and supports sparse checkout, submodule initialization, and LFS.
   - **Expected Values**: `actions/checkout@v4` as the first step in every job
   - **Currently Configured Value**: Present as step 1 in all 5 workflows
   - **Outcome / System Impact**: Without this step, the runner workspace is empty and no repository files are available. The action performs a shallow clone (`fetch-depth: 1` by default) for performance. It also configures `git` with the `GITHUB_TOKEN` for authenticated access to private repositories.
   - **Why & When to Configure It**: `v4` is used instead of `v3` because `v3` uses Node.js 16 which reached end-of-life. If you need full git history (e.g. for `git log` analysis or changelog generation), add `fetch-depth: 0`. For monorepos with sparse checkout needs, add `sparse-checkout:` configuration.
   - **Scaling & Troubleshooting**: If checkout fails with authentication errors, verify the `GITHUB_TOKEN` has `contents: read` permission. For submodules, add `submodules: true`. The `.gitmodules` file in this repository references `service-discovery` — if future workflows need that submodule, add `submodules: recursive`.

---

## 2. Shell Script Lint Check Pipeline — Parameter Deep-Dive

**File**: [`.github/workflows/script-lint-check.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/.github/workflows/script-lint-check.yml) (89 lines)

### 2.1 Workflow Dispatch Input Parameters

5. **Parameter**: `inputs.script_path` (type: `string`, required: `false`, default: `""`)
   - **Definition**: Optional path to a single shell script file to lint. When empty, the workflow discovers and lints all `.sh` files under `scripts/`.
   - **Expected Values**: Empty string (lint all) or a valid path like `scripts/manage.sh`
   - **Currently Configured Value**: Default `""` (lint all)
   - **Outcome / System Impact**: When a specific path is provided, the workflow validates only that one file, reducing execution time from ~30 seconds (all scripts) to ~5 seconds (single file). When empty, `find scripts/ -type f -name "*.sh"` discovers every shell script recursively. The `| sort` ensures deterministic ordering across runs — without it, `find` output order depends on filesystem inode allocation and varies between Linux kernels.
   - **Why & When to Configure It**: Use the specific path input when debugging a single script's syntax error — running all scripts takes longer and clutters the output. Leave empty for full repository validation before merging pull requests.
   - **Scaling & Troubleshooting**: If the specified path does not exist, the workflow exits with `exit 1` and a `::error::` annotation. The path is relative to the repository root, not the runner's home directory. Absolute paths will fail because the runner clones the repo into `$GITHUB_WORKSPACE`.

---

### 2.2 Step-Level Parameters

6. **Parameter**: `sudo apt-get install -y shellcheck`
   - **Definition**: Installs ShellCheck, a static analysis tool for shell scripts that detects common bugs, syntax issues, and POSIX compliance problems. The `-y` flag auto-confirms the installation prompt.
   - **Expected Values**: ShellCheck v0.10+ from Ubuntu's package repository
   - **Currently Configured Value**: Installed from `apt-get` on `ubuntu-latest`
   - **Outcome / System Impact**: ShellCheck catches categories of bugs that `bash -n` cannot: unquoted variables (`SC2086`), unused variables (`SC2034`), command injection via word splitting (`SC2046`), and deprecated syntax (`SC2006` for backticks). Without ShellCheck, a script like `rm -rf $DIR/` with an unset `$DIR` would pass `bash -n` but is a catastrophic bug.
   - **Why & When to Configure It**: Installed via `apt-get` rather than a pre-built binary because the Ubuntu runner's package manager is the most reliable source. A pinned version (e.g. from GitHub Releases) would be needed only if a specific ShellCheck version introduced a regression.
   - **Scaling & Troubleshooting**: If `apt-get` fails due to a mirror timeout, the step retries are handled by the default GitHub Actions retry policy. If ShellCheck is too strict for certain scripts, add `# shellcheck disable=SC2086` directives inline rather than reducing the global severity.

---

7. **Parameter**: `bash -n "$script"`
   - **Definition**: Bash's built-in syntax check mode. The `-n` flag reads the script and checks for syntax errors without executing any commands. It verifies that the parser can tokenize and parse the entire file.
   - **Expected Values**: Exit code 0 for valid syntax, non-zero for parse errors
   - **Currently Configured Value**: Applied to every discovered script in a loop
   - **Outcome / System Impact**: Catches hard parse errors: unclosed quotes, missing `fi`/`done`/`esac` keywords, invalid redirections, and broken heredocs. It does **not** catch runtime errors like missing commands, wrong argument counts, or logic bugs — those require ShellCheck or actual execution.
   - **Why & When to Configure It**: `bash -n` is the cheapest possible validation and runs in under 10ms per script. It is always worth running as a first tier before ShellCheck because it catches the class of errors that prevent the script from even loading.
   - **Scaling & Troubleshooting**: `bash -n` checks syntax against the `bash` version installed on the runner (typically bash 5.2). If a script uses features from a newer bash version not yet available on the runner, it may produce false negatives. A script with `#!/bin/sh` shebang that uses bash-specific syntax (arrays, `[[ ]]`) will pass `bash -n` but fail at runtime under `dash` or `sh`.

---

8. **Parameter**: `shellcheck --severity=error --shell=bash "$script"`
   - **Definition**: ShellCheck severity threshold and target shell dialect. `--severity=error` means only issues classified as errors (SC-level `error`) cause the step to fail; warnings and info-level findings are reported but do not block. `--shell=bash` forces ShellCheck to interpret the script as bash regardless of the shebang line.
   - **Expected Values**: Exit code 0 if no error-severity issues found
   - **Currently Configured Value**: `--severity=error` and `--shell=bash`
   - **Outcome / System Impact**: Setting severity to `error` prevents false-positive CI failures from stylistic warnings (e.g. `SC2034: unused variable` which may actually be exported via `source`). The `--shell=bash` flag is necessary because some scripts in the repository lack a shebang line, and ShellCheck defaults to `sh` (POSIX) interpretation when no shebang is present — which would flag every bash-specific construct as an error.
   - **Why & When to Configure It**: `--severity=error` is the right balance for infrastructure scripts where some ShellCheck warnings are intentional (e.g. dynamically sourced variables). Tighten to `--severity=warning` once all existing warnings are resolved. The `--shell=bash` ensures consistent analysis regardless of shebang presence.
   - **Scaling & Troubleshooting**: To investigate a specific ShellCheck code, use `shellcheck --wiki-url` or visit `https://www.shellcheck.net/wiki/SCxxxx`. To suppress a finding in a specific script, add `# shellcheck disable=SCxxxx` above the offending line. Never globally disable codes in the CI pipeline — suppress per-file.

---

9. **Parameter**: `$GITHUB_STEP_SUMMARY`
   - **Definition**: A GitHub Actions special file path. Content written to this file appears as a rich markdown summary on the workflow run's Summary tab. It persists after the run completes and is visible without opening individual step logs.
   - **Expected Values**: Markdown-formatted table of results
   - **Currently Configured Value**: A markdown table listing each script and its pass/fail status
   - **Outcome / System Impact**: Without the summary step, reviewers must open each step's raw log to determine which scripts passed or failed. The summary provides a scannable, persistent record that survives log rotation (GitHub retains summaries for 90 days by default, regardless of log retention settings).
   - **Why & When to Configure It**: The `if: always()` condition ensures the summary is generated even when earlier steps fail. Without `always()`, a failing bash syntax step would skip the summary generation, leaving no structured output for the developer to review.
   - **Scaling & Troubleshooting**: `$GITHUB_STEP_SUMMARY` has a 1 MiB size limit. For repositories with thousands of scripts, truncate the table to the first 100 entries and add a "and N more..." footer.

---

## 3. Compose Profile Validation Pipeline — Parameter Deep-Dive

**File**: [`.github/workflows/compose-profile-validation.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/.github/workflows/compose-profile-validation.yml) (102 lines)

### 3.1 Workflow Dispatch Input Parameters

10. **Parameter**: `inputs.profile` (type: `choice`, required: `false`, default: `""`)
    - **Definition**: Dropdown selector allowing the operator to validate a single Docker Compose profile. The empty string option means "validate all profiles." The 7 profile options (`db`, `analytics`, `streaming`, `workflows`, `tracing`, `network`, `full`) map directly to the `profiles:` arrays in `docker-compose.yml` (ADR-0015).
    - **Expected Values**: Empty (all) or one of the 7 profile names
    - **Currently Configured Value**: Default `""`
    - **Outcome / System Impact**: Selecting a specific profile reduces validation time and focuses the output on a single profile's service graph. The `full` profile includes all 10 containers and is the most comprehensive validation.
    - **Why & When to Configure It**: Use a specific profile when you've modified environment variables or dependencies for only one service group. Use empty (all) before releases to catch cross-profile regressions — e.g. a `depends_on` change in the `tracing` profile that breaks the `full` profile.
    - **Scaling & Troubleshooting**: If a new profile is added to `docker-compose.yml`, it must also be added to both the `inputs.profile.options` list and the `PROFILES` environment variable. Forgetting either causes the new profile to be either unselectable in the UI or unvalidated in the "all" run.

---

### 3.2 Environment Variables

11. **Parameter**: `env.PROFILES: "db analytics streaming workflows tracing network full"`
    - **Definition**: Space-delimited list of all Docker Compose profile names. Used as the iteration target when no specific profile is selected via `workflow_dispatch`.
    - **Expected Values**: All 7 profile names from ADR-0015
    - **Currently Configured Value**: `"db analytics streaming workflows tracing network full"`
    - **Outcome / System Impact**: This variable drives the `for profile in ...` loop in the validation and summary steps. If a profile name is misspelled here, `docker compose --profile <misspelled>` returns zero services but does not error — it silently validates an empty service set, which always passes. This is a Docker Compose behavior, not a GitHub Actions behavior.
    - **Why & When to Configure It**: Must stay synchronized with `docker-compose.yml`. Adding a new profile to Compose without updating this variable means the CI pipeline never validates it. Adding a profile here that does not exist in Compose produces a false-positive pass.
    - **Scaling & Troubleshooting**: To detect phantom profiles, compare the output of `docker compose config --profiles` (which lists all defined profiles) against this variable. A mismatch means the pipeline is stale.

---

### 3.3 Step-Level Parameters

12. **Parameter**: `cp .env.example .env` (Prepare environment step)
    - **Definition**: Copies the `.env.example` file to `.env` so Docker Compose can resolve `${VAR:-default}` variable interpolations. Without a `.env` file, Compose uses only the inline defaults from `${VAR:-default}` syntax and prints warnings for undefined variables.
    - **Expected Values**: `.env` file matching `.env.example` structure
    - **Currently Configured Value**: Conditional copy (`if [ -f .env.example ]`)
    - **Outcome / System Impact**: Docker Compose v2 resolves environment variables from multiple sources in priority order: shell environment > `.env` file > `environment:` block defaults. Without `.env`, variables like `REDIS_PASSWORD` that have defaults in the Compose file (`${REDIS_PASSWORD:-llmobs_redis_s3cret_2024}`) still resolve correctly, but variables without defaults produce `WARNING: The REDIS_PASSWORD variable is not set` noise in the output. The `cp` ensures clean validation output.
    - **Why & When to Configure It**: The `if [ -f .env.example ]` guard prevents the step from failing if `.env.example` is removed in a future commit. The `-f` flag on `cp` overwrites any existing `.env` to ensure a fresh, known-good state.
    - **Scaling & Troubleshooting**: If Compose validation fails with "variable is not set" errors, check that `.env.example` includes all variables referenced in `docker-compose.yml`. The CI runner does not have access to production secrets — this step uses example/default values only.

---

13. **Parameter**: `docker network create llmobs-network 2>/dev/null || true`
    - **Definition**: Creates the external Docker network referenced by `docker-compose.yml`'s `networks: llmobs-network: external: true` declaration. The `2>/dev/null || true` suppresses errors if the network already exists (idempotent).
    - **Expected Values**: Network `llmobs-network` exists after this step
    - **Currently Configured Value**: Created before validation, cleaned up in the `Cleanup` step
    - **Outcome / System Impact**: `docker-compose.yml` declares `llmobs-network` as `external: true`, meaning Compose expects the network to already exist — it will not create it. Without this step, `docker compose config` fails with `network llmobs-network declared as external, but could not be found`. This is the most common CI failure mode for this pipeline.
    - **Why & When to Configure It**: The `|| true` is critical — on subsequent workflow runs within the same runner (rare for GitHub-hosted, common for self-hosted), the network may already exist. Without `|| true`, `docker network create` returns exit code 1 for "network already exists," which fails the step and the entire workflow.
    - **Scaling & Troubleshooting**: The `Cleanup` step (`docker network rm llmobs-network 2>/dev/null || true`) removes the network after validation to avoid leaking Docker resources on self-hosted runners. On GitHub-hosted runners, the VM is destroyed after the job, so cleanup is technically unnecessary but included for correctness.

---

14. **Parameter**: `docker compose --profile "${profile}" config --quiet`
    - **Definition**: Docker Compose v2 configuration validation command. `--profile` selects a specific profile's service set. `config` resolves all variable interpolations, merges override files, and validates the complete service graph. `--quiet` suppresses the resolved YAML output, printing only errors.
    - **Expected Values**: Exit code 0 and no stderr output for valid profiles
    - **Currently Configured Value**: Executed in a loop for each target profile
    - **Outcome / System Impact**: `config --quiet` validates that every service in the profile has valid YAML syntax, all referenced images/volumes/networks exist or are declared, `depends_on` targets resolve to services within the active profile set, and all `${VAR:-default}` interpolations resolve. It does **not** validate that images are pullable, that ports are available, or that healthchecks work — it is purely a configuration-level check.
    - **Why & When to Configure It**: `--quiet` is used instead of raw `config` (which outputs the full resolved YAML) because the validation step only needs pass/fail status. The resolved YAML is verbose (400+ lines for the `full` profile) and clutters the step log.
    - **Scaling & Troubleshooting**: A common false-positive: `config --quiet` passes even when a profile name is misspelled (it returns an empty service set, which is technically valid). Cross-check with `docker compose --profile "${profile}" config --services` to verify the expected services are present. The validation step captures this via the `SERVICES` variable output.

---

## 4. Kubernetes Manifest Validation Pipeline — Parameter Deep-Dive

**File**: [`.github/workflows/kubernetes-manifest-validation.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/.github/workflows/kubernetes-manifest-validation.yml) (131 lines)

### 4.1 Workflow Dispatch Input Parameters

15. **Parameter**: `inputs.manifest_path` (type: `string`, required: `false`, default: `""`)
    - **Definition**: Optional path to a single Kubernetes manifest file. When empty, discovers all `.yaml` and `.yml` files under `k8s/`.
    - **Expected Values**: Empty (all) or a valid path like `k8s/deployments/alloydb-relational-db.yaml`
    - **Currently Configured Value**: Default `""`
    - **Outcome / System Impact**: Single-file validation is useful when iterating on a specific deployment manifest. The discovery command `find k8s/ -type f \( -name "*.yaml" -o -name "*.yml" \)` catches both extension conventions. The `| sort` ensures deterministic log output.
    - **Why & When to Configure It**: Use specific path mode during development to get fast feedback on a single manifest. Use "all" mode before merging to catch cross-manifest issues (e.g. a ConfigMap rename that breaks a `configMapKeyRef` in a Deployment).
    - **Scaling & Troubleshooting**: Paths must be relative to the repository root. The file existence check (`[ ! -f ... ]`) prevents cryptic kubeconform errors on non-existent files.

---

16. **Parameter**: `inputs.kubernetes_version` (type: `string`, required: `false`, default: `"1.31.0"`)
    - **Definition**: The Kubernetes API schema version used by kubeconform for manifest validation. Determines which API versions, field names, and deprecations are enforced.
    - **Expected Values**: A valid Kubernetes release version like `1.28.0`, `1.29.0`, `1.30.0`, `1.31.0`
    - **Currently Configured Value**: Default `"1.31.0"`, also set as `env.K8S_VERSION` fallback
    - **Outcome / System Impact**: kubeconform downloads OpenAPI schemas for the specified version from the official Kubernetes schema repository. If a manifest uses `apiVersion: apps/v1` (stable since K8s 1.9), it validates against any version. If a manifest uses a deprecated or removed API (e.g. `extensions/v1beta1` removed in 1.22), validation fails against newer versions. The Argo Rollouts CRD (`argoproj.io/v1alpha1`) is a custom resource not in the upstream schema — kubeconform reports it as unknown rather than invalid.
    - **Why & When to Configure It**: Set to `1.31.0` because the K8s manifests target Kubernetes 1.31+. Before upgrading a production cluster, run this pipeline with the target version to detect deprecated APIs before they cause runtime failures. For example, transitioning from 1.24 to 1.25 removed `PodSecurityPolicy` — this pipeline would catch manifests still referencing it.
    - **Scaling & Troubleshooting**: kubeconform caches schemas in `/tmp`. If schema download fails (network timeout), the step fails. The `env.K8S_VERSION` provides a fallback when the input is empty (the `${TARGET:-...}` bash default substitution handles this).

---

### 4.2 Step-Level Parameters

17. **Parameter**: `kubeconform -kubernetes-version "${K8S_VER}" -strict -summary -output text`
    - **Definition**: kubeconform is a Kubernetes manifest validator that checks YAML content against the official Kubernetes OpenAPI schemas. Each flag modifies validation behavior.
    - **Expected Values**: Exit code 0 for valid manifests
    - **Currently Configured Value**: All 4 flags active
    - **Flag Breakdown**:
      - `-kubernetes-version`: Validates against the specified K8s schema version's OpenAPI spec. Without this, kubeconform uses its built-in default (usually the latest version at release time), which may differ from the target cluster.
      - `-strict`: Rejects manifests containing fields not defined in the schema. Without `-strict`, kubeconform silently ignores unknown fields — which masks typos like `replicas` misspelled as `replica` that would be silently ignored by `kubectl apply` but have no effect.
      - `-summary`: Outputs a summary line at the end showing total valid, invalid, and skipped resources. Without this, only per-file results are shown.
      - `-output text`: Human-readable output format. Alternatives are `-output json` (machine parseable) and `-output tap` (Test Anything Protocol).
    - **Outcome / System Impact**: The combination of `-strict` and a specific version catches four categories of errors: (1) invalid field names (typos), (2) wrong field types (string vs integer), (3) deprecated APIs for the target version, and (4) missing required fields. Without kubeconform, `kubectl --dry-run=client` catches only categories 3 and 4.
    - **Why & When to Configure It**: `-strict` is aggressive — it will fail on custom resource fields that kubeconform doesn't know about (like Argo Rollouts `Rollout` resources). The pipeline handles this gracefully by using `⚠️ WARN` instead of `❌ FAIL` for schema errors and not setting `exit 1` on schema failures.
    - **Scaling & Troubleshooting**: For custom CRDs, add schema overrides with `-schema-location` pointing to the CRD's OpenAPI schema. For Argo Rollouts specifically: `kubeconform -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/argoproj.io/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'`.

---

18. **Parameter**: `kubectl apply --dry-run=client -f "$manifest"`
    - **Definition**: kubectl's client-side dry-run mode. Parses the manifest, resolves API versions, and validates field types against the kubectl binary's built-in schema — all without contacting a Kubernetes cluster.
    - **Expected Values**: Exit code 0 for valid standard K8s resources, non-zero for CRDs (expected)
    - **Currently Configured Value**: Applied to every discovered manifest with warning (not failure) on errors
    - **Outcome / System Impact**: `--dry-run=client` catches a different class of errors than kubeconform: it validates that the resource `kind` exists in the API server's schema, that `apiVersion` is valid, and that required fields like `metadata.name` are present. It does **not** validate against custom CRDs (like Argo Rollouts `Rollout`) because those schemas are not built into kubectl — they exist only on a live cluster. The `|| echo "::warning::"` pattern reports CRD validation failures as non-blocking warnings rather than pipeline failures.
    - **Why & When to Configure It**: The `--dry-run=client` vs `--dry-run=server` distinction is important. `client` mode works without cluster access (suitable for CI), while `server` mode sends the request to the API server which validates against all installed CRDs. For this pipeline, `client` is used because the CI runner does not have cluster credentials.
    - **Scaling & Troubleshooting**: To enable server-side validation, configure kubectl with cluster credentials (kubeconfig) and switch to `--dry-run=server`. This would catch CRD validation errors and admission webhook rejections.

---

19. **Parameter**: `uses: azure/setup-kubectl@v4` with `version: "v1.31.0"`
    - **Definition**: Official Microsoft Azure GitHub Action that installs a specific version of `kubectl`. Despite the `azure/` namespace, the action simply downloads and installs the upstream `kubectl` binary — it has no Azure-specific behavior.
    - **Expected Values**: kubectl v1.31.0 installed at `/usr/local/bin/kubectl`
    - **Currently Configured Value**: `v1.31.0`
    - **Outcome / System Impact**: Pinning the kubectl version ensures the dry-run validation uses the same API schema version as the target cluster. kubectl includes built-in OpenAPI schemas that change between versions. Using a mismatched version could produce false positives (validating against APIs removed in the target version) or false negatives (rejecting valid APIs added in the target version).
    - **Why & When to Configure It**: The version is pinned to `v1.31.0` to match the `K8S_VERSION` environment variable and the kubeconform target. When upgrading the target cluster version, update both `K8S_VERSION` and this version pin simultaneously.
    - **Scaling & Troubleshooting**: If the `azure/setup-kubectl@v4` action fails (network timeout downloading kubectl), the step fails. As a fallback, replace with `curl -LO "https://dl.k8s.io/release/v1.31.0/bin/linux/amd64/kubectl"`.

---

## 5. Canary Traffic Rollout Pipeline — Parameter Deep-Dive

**File**: [`.github/workflows/canary-traffic-rollout.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/.github/workflows/canary-traffic-rollout.yml) (132 lines)

### 5.1 Workflow Dispatch Input Parameters

20. **Parameter**: `inputs.target_service` (type: `choice`, required: `true`)
    - **Definition**: The Kubernetes service/deployment target for the canary rollout. The choice list provides the deployable services from the K8s manifest suite.
    - **Expected Values**: One of `service-registry-api`, `grafana-portal-ui`, `opentelemetry-collector`, `traefik-ingress-gateway`
    - **Currently Configured Value**: 4 stateless service options
    - **Outcome / System Impact**: The selected service determines which Argo Rollouts `Rollout` resource receives the image update and traffic weight change. Stateful services (AlloyDB, ClickHouse, Kafka) are intentionally excluded because canary deployments for databases require data migration strategies that a simple traffic split cannot handle — a canary database with 5% traffic would need a full data replica, not just a second pod.
    - **Why & When to Configure It**: Add new entries when custom application services (e.g. an API gateway, a worker service) are deployed via Argo Rollouts. Remove entries when a service is decommissioned.
    - **Scaling & Troubleshooting**: If the `Rollout` resource name does not match the expected `llmobs-canary-rollout`, the `kubectl argo rollouts set image` command fails. The pipeline uses `|| echo "::warning::"` to degrade gracefully in CI environments without cluster access.

---

21. **Parameter**: `inputs.image_tag` (type: `string`, required: `true`)
    - **Definition**: The Docker image tag to deploy as the canary revision. Must be a tag that exists in the container registry.
    - **Expected Values**: Semver tag (e.g. `v1.2.3`), SHA tag (e.g. `sha-abc1234`), or `latest`
    - **Currently Configured Value**: No default (required input)
    - **Outcome / System Impact**: The tag is passed to `kubectl argo rollouts set image "llmobs-canary-rollout" "*=${IMAGE_TAG}"`. The `*=` syntax updates all container images in the rollout to the specified tag. If the tag does not exist in the registry, the new pod fails to pull the image and the canary revision enters `ImagePullBackOff` — Argo Rollouts detects this as a failure and does not promote traffic.
    - **Why & When to Configure It**: Always use an immutable tag (semver or SHA) for canary deployments. Using `latest` is dangerous because the tag's content may change between the canary start and promotion, causing the stable revision to receive a different image than what was tested during canary.
    - **Scaling & Troubleshooting**: Verify the tag exists before running the pipeline: `docker manifest inspect <registry>/<image>:<tag>`. If the canary pod shows `ErrImagePull`, check the image name, tag, and registry authentication.

---

22. **Parameter**: `inputs.traffic_weight` (type: `choice`, required: `false`, default: `"5"`)
    - **Definition**: The initial percentage of traffic routed to the canary revision. The Argo Rollouts controller updates the service mesh or ingress to split traffic at this ratio.
    - **Expected Values**: `5`, `10`, `25`, `50`, or `100`
    - **Currently Configured Value**: Default `"5"` (5% of traffic)
    - **Outcome / System Impact**: At 5%, only 1 in 20 requests hits the canary pod. This provides enough traffic to detect startup crashes, error rate spikes, and latency regressions while limiting blast radius to 5% of users. At 100%, the canary effectively replaces the stable revision immediately — this bypasses the progressive rollout safety net and should only be used for emergency hotfixes where the risk of the current stable version exceeds the risk of untested deployment.
    - **Why & When to Configure It**: Start at 5% for normal releases. Jump to 25% or 50% for low-risk configuration changes (e.g. updating an environment variable). Use 100% only when the stable version has a critical bug that the new version fixes and downtime during gradual rollout is unacceptable.
    - **Scaling & Troubleshooting**: The traffic split accuracy depends on the ingress controller's implementation. Traefik's weighted round-robin achieves exact percentages for high-traffic services but may fluctuate for services receiving fewer than 20 requests per minute (at 5% weight, fewer than 1 request per minute reaches the canary).

---

23. **Parameter**: `inputs.namespace` (type: `string`, required: `false`, default: `"llmobs"`)
    - **Definition**: The Kubernetes namespace where the Argo Rollouts `Rollout` resource is deployed.
    - **Expected Values**: `llmobs` (matches `k8s/namespace.yaml`)
    - **Currently Configured Value**: Default `"llmobs"`
    - **Outcome / System Impact**: All `kubectl argo rollouts` commands use `-n "${NAMESPACE}"` to scope operations. Using the wrong namespace silently fails — kubectl reports "rollout not found" rather than checking other namespaces.
    - **Why & When to Configure It**: Change only when deploying to a different namespace (e.g. `llmobs-staging` for pre-production testing). Never use `default` namespace for production workloads.
    - **Scaling & Troubleshooting**: Verify the rollout exists in the target namespace: `kubectl get rollouts -n llmobs`.

---

24. **Parameter**: `inputs.auto_promote` (type: `boolean`, required: `false`, default: `false`)
    - **Definition**: When `true`, the pipeline monitors the rollout and automatically promotes through all canary stages (5% → 25% → 50% → 100%). When `false`, the pipeline sets the initial weight and exits — manual promotion is required for each subsequent stage.
    - **Expected Values**: `false` (default for safety)
    - **Currently Configured Value**: Default `false`
    - **Outcome / System Impact**: With `auto_promote: true`, the pipeline blocks on `kubectl argo rollouts status --watch --timeout 600s`, which streams rollout events for up to 10 minutes. The Argo Rollouts controller handles the actual promotion through the `steps:` defined in the `Rollout` CRD (120-second pauses between stages). With `auto_promote: false`, the pipeline completes immediately after setting the initial weight, and an operator must run `kubectl argo rollouts promote llmobs-canary-rollout -n llmobs` for each subsequent stage.
    - **Why & When to Configure It**: Use `false` for high-risk deployments where human judgment is needed between stages (checking error rates, latency dashboards). Use `true` for automated release pipelines where monitoring is handled by external alerting systems that can trigger `kubectl argo rollouts abort` automatically.
    - **Scaling & Troubleshooting**: The 600-second timeout covers the 4-stage rollout: 3 pauses × 120 seconds = 360 seconds + pod startup time. If the rollout takes longer (slow image pulls, long readiness probes), increase the timeout. If the timeout expires, the rollout continues in the background — it is not aborted.

---

### 5.2 Step-Level Parameters

25. **Parameter**: `environment: production`
    - **Definition**: GitHub Actions environment protection rule. When a job specifies an `environment`, GitHub enforces any protection rules configured for that environment — including required reviewers, wait timers, and deployment branch restrictions.
    - **Expected Values**: Environment named `production` with optional protection rules
    - **Currently Configured Value**: `production` environment on the `canary-rollout` job
    - **Outcome / System Impact**: If `production` environment protection rules are configured in the repository's Settings > Environments, a human must approve the workflow run before the job starts. Without environment protection, anyone with workflow dispatch permissions can deploy to production without approval. If the `production` environment does not exist in Settings, the job runs without any gate — the `environment:` key has no effect until protection rules are configured.
    - **Why & When to Configure It**: Configure the `production` environment in GitHub Settings with at least one required reviewer before using this pipeline for real deployments. Add a 5-minute wait timer for non-urgent deployments to allow reviewer cancellation.
    - **Scaling & Troubleshooting**: If the job is stuck in "Waiting for review," check the repository's Settings > Environments > production for the required reviewer list. If no one is available to review, the job times out after the environment's configured maximum wait time (default: 30 days).

---

26. **Parameter**: `--timeout 600s` on `kubectl argo rollouts status --watch`
    - **Definition**: Maximum wall-clock time the status watch command waits for the rollout to complete before exiting. The watch streams rollout events in real-time.
    - **Expected Values**: 600 seconds (10 minutes)
    - **Currently Configured Value**: `600s`
    - **Outcome / System Impact**: The 4-stage rollout with 120-second pauses between stages takes a minimum of 360 seconds (6 minutes) plus pod scheduling, image pull, and readiness probe time. The 600-second timeout provides 240 seconds of headroom for slow image pulls or extended readiness checks. If the timeout expires, the `kubectl` command exits with a non-zero code, but the rollout continues running on the cluster — the timeout only affects the CI pipeline's visibility, not the actual deployment.
    - **Why & When to Configure It**: Increase for services with long startup times (e.g. Java-based services with 60+ second JVM warmup). Decrease for services with sub-second readiness (e.g. the service registry which reports healthy within 5 seconds).
    - **Scaling & Troubleshooting**: If the pipeline exits with a timeout but the rollout is still progressing, check the rollout status manually: `kubectl argo rollouts get rollout llmobs-canary-rollout -n llmobs`. The `|| echo "::warning::"` ensures a timeout does not fail the entire pipeline.

---

## 6. Docker Image Build Pipeline — Parameter Deep-Dive

**File**: [`.github/workflows/docker-image-build.yml`](file:///home/btpl-lap-22/live/llm-obs-infra/.github/workflows/docker-image-build.yml) (141 lines)

### 6.1 Workflow Dispatch Input Parameters

27. **Parameter**: `inputs.image_name` (type: `choice`, required: `true`)
    - **Definition**: The name of the Docker image to build. Currently limited to `llmobs-service-registry` because it is the only custom application image in the repository — all other services use upstream vendor images (e.g. `redis:7-alpine`, `grafana/grafana:latest`).
    - **Expected Values**: `llmobs-service-registry`
    - **Currently Configured Value**: Single option `llmobs-service-registry`
    - **Outcome / System Impact**: The image name is used to construct the full image reference: `<registry>/<owner>/<image_name>:<tag>`. Adding incorrect names results in orphaned images in the registry. The choice type ensures only valid image names can be selected — preventing typos that would create unexpected registry entries.
    - **Why & When to Configure It**: Add new options when the repository introduces additional custom application Dockerfiles. Do not add entries for vendor images (Redis, Kafka, etc.) — those are maintained by their upstream projects.
    - **Scaling & Troubleshooting**: To list existing images in the registry: `docker manifest inspect ghcr.io/<owner>/llmobs-service-registry:latest`.

---

28. **Parameter**: `inputs.dockerfile_path` (type: `string`, required: `false`, default: `"service-discovery/Dockerfile"`)
    - **Definition**: Relative path from repository root to the Dockerfile used for the build. Validated for existence before the build starts.
    - **Expected Values**: A path to an existing Dockerfile
    - **Currently Configured Value**: `service-discovery/Dockerfile`
    - **Outcome / System Impact**: The Dockerfile path is passed to `docker/build-push-action@v6` as the `file:` parameter. If the path is incorrect, the build fails with a clear error from the validation step (not a cryptic Docker daemon error). The default points to the `service-discovery/` submodule which contains the Service Registry application.
    - **Why & When to Configure It**: Override when building from a different Dockerfile (e.g. a multi-stage Dockerfile in a different directory). The path is relative to the repository root, not to the build context.
    - **Scaling & Troubleshooting**: If the Dockerfile is inside a git submodule, ensure `actions/checkout@v4` is configured with `submodules: true` — otherwise the submodule directory is empty.

---

29. **Parameter**: `inputs.build_context` (type: `string`, required: `false`, default: `"service-discovery"`)
    - **Definition**: The Docker build context directory. All `COPY` and `ADD` instructions in the Dockerfile are relative to this directory. The entire directory is sent to the Docker daemon for building.
    - **Expected Values**: A directory containing the application source code
    - **Currently Configured Value**: `service-discovery`
    - **Outcome / System Impact**: The build context determines which files are available inside the Docker build. A context set to the repository root (`.`) would send all files (including `config/`, `scripts/`, `docs/`) to the Docker daemon — wasting bandwidth and potentially leaking sensitive files into the image. Setting the context to `service-discovery` limits the build to only the application's source files.
    - **Why & When to Configure It**: Always set the build context to the narrowest directory that contains all files needed by the Dockerfile. If a Dockerfile needs files from outside its directory (e.g. shared libraries), the context must be widened or the files must be copied into the context before building.
    - **Scaling & Troubleshooting**: Large build contexts slow down the build because Docker must tar and send the entire directory to the daemon. Use a `.dockerignore` file in the context directory to exclude unnecessary files (node_modules, .git, test data).

---

30. **Parameter**: `inputs.registry` (type: `choice`, required: `false`, default: `"ghcr.io"`)
    - **Definition**: The container registry to push the built image to. Supports GitHub Container Registry (ghcr.io) and Docker Hub (docker.io).
    - **Expected Values**: `ghcr.io` or `docker.io`
    - **Currently Configured Value**: Default `ghcr.io`
    - **Outcome / System Impact**: Each registry uses different authentication: ghcr.io authenticates with `GITHUB_TOKEN` (automatic, no secrets needed), while docker.io requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets. The login step is conditional — only the selected registry's login action runs. Pushing to the wrong registry creates images inaccessible to the deployment pipeline.
    - **Why & When to Configure It**: Use `ghcr.io` for private/internal images (automatically scoped to the GitHub organization). Use `docker.io` for public images or when Kubernetes nodes are configured to pull from Docker Hub. If using a private registry (e.g. AWS ECR, Google Artifact Registry), add a new option and corresponding login action.
    - **Scaling & Troubleshooting**: ghcr.io images are scoped to the GitHub user/org (`ghcr.io/<owner>/<image>`). Visibility defaults to private — make images public in the Packages settings if external clusters need to pull them without authentication.

---

### 6.2 Step-Level Parameters

31. **Parameter**: `uses: docker/setup-buildx-action@v3`
    - **Definition**: Installs Docker Buildx, an extended build driver that supports multi-platform builds, build caching, SBOM generation, and provenance attestation. Buildx replaces the legacy `docker build` command with a more capable build backend.
    - **Expected Values**: Buildx v0.17+ installed and set as the default builder
    - **Currently Configured Value**: `@v3` (latest stable)
    - **Outcome / System Impact**: Without Buildx, the `cache-from`, `cache-to`, `provenance`, and `sbom` options in the build step are unavailable. The legacy `docker build` command does not support GitHub Actions cache backend, SBOM generation, or provenance attestation. Buildx uses BuildKit as the backend, which provides parallel stage execution, better caching, and smaller output images.
    - **Why & When to Configure It**: Always use Buildx for CI builds. The `@v3` version creates a new builder instance with the `docker-container` driver, which runs BuildKit in a container for full feature support. The default `docker` driver does not support all features.
    - **Scaling & Troubleshooting**: If multi-platform builds are needed (e.g. `linux/amd64` + `linux/arm64`), add `platforms: linux/amd64,linux/arm64` to the build step. This requires QEMU emulation for non-native platforms, which is set up with `docker/setup-qemu-action@v3`.

---

32. **Parameter**: `cache-from: type=gha` and `cache-to: type=gha,mode=max`
    - **Definition**: Docker Buildx layer caching using GitHub Actions' built-in cache backend. `cache-from` reads cached layers from previous builds. `cache-to` writes layers to the cache after the current build. `mode=max` caches all layers (not just the final image's layers).
    - **Expected Values**: Cache hit rate >80% for incremental builds
    - **Currently Configured Value**: Both `type=gha` with `mode=max`
    - **Outcome / System Impact**: Without caching, every build starts from scratch — pulling base images, installing dependencies, and compiling from source. With `type=gha`, Docker layers are stored in GitHub's Actions cache (10 GB limit per repository). A typical incremental build (only application code changed, dependencies unchanged) drops from 3-5 minutes to 30-60 seconds because dependency installation layers are cached. `mode=max` ensures all intermediate layers (not just the final image) are cached, which is critical for multi-stage Dockerfiles where intermediate stages produce reusable layers.
    - **Why & When to Configure It**: `type=gha` is the simplest caching option for GitHub Actions — no external registry or storage needed. Alternative: `type=registry` caches layers in the container registry itself, which persists longer than the 7-day GitHub Actions cache TTL but requires registry write access for every build (not just pushes). Use `type=registry` when cache eviction causes frequent cold builds.
    - **Scaling & Troubleshooting**: GitHub's cache has a 10 GB per-repository limit. When the limit is reached, the oldest caches are evicted. If builds consistently miss the cache, check the eviction with `gh actions cache list`. The `mode=max` increases cache size but improves hit rates — the trade-off is worth it for repositories with fewer than 10 active branches.

---

33. **Parameter**: `provenance: true`
    - **Definition**: Generates a SLSA (Supply-chain Levels for Software Artifacts) provenance attestation for the built image. The attestation is a signed, tamper-evident document recording who built the image, when, from which source commit, on which runner, and with which build arguments.
    - **Expected Values**: Provenance attestation attached to the image manifest
    - **Currently Configured Value**: `true`
    - **Outcome / System Impact**: The provenance attestation is stored as an OCI artifact alongside the image in the registry. Tools like `cosign verify-attestation` and `docker buildx imagetools inspect` can read it. Kubernetes admission controllers (e.g. Sigstore Policy Controller, Kyverno) can enforce provenance requirements — rejecting images without valid attestations. Without provenance, there is no cryptographic proof linking the image to its source code.
    - **Why & When to Configure It**: Enable for any image deployed to production. The overhead is minimal (~2 seconds per build). Disable only for local development builds where provenance is unnecessary.
    - **Scaling & Troubleshooting**: Provenance attestations increase the image size in the registry by 5-10 KB. Inspect with: `docker buildx imagetools inspect <image>:<tag> --format '{{json .Provenance}}'`.

---

34. **Parameter**: `sbom: true`
    - **Definition**: Generates a Software Bill of Materials (SBOM) in SPDX format listing every package, library, and dependency included in the image. The SBOM is attached as an OCI artifact alongside the image.
    - **Expected Values**: SPDX SBOM attached to the image manifest
    - **Currently Configured Value**: `true`
    - **Outcome / System Impact**: The SBOM enables vulnerability scanning tools (e.g. Grype, Trivy, Docker Scout) to analyze the image's dependency tree without pulling and extracting the image. It lists OS packages (from `apt-get`/`apk`), language-specific packages (npm, pip), and their versions. This is increasingly required for compliance frameworks (NIST SSDF, EU Cyber Resilience Act).
    - **Why & When to Configure It**: Enable for all production images. The SBOM generation adds 5-15 seconds to the build depending on image complexity. Disable for ephemeral test images where compliance is not a concern.
    - **Scaling & Troubleshooting**: Inspect the SBOM with: `docker buildx imagetools inspect <image>:<tag> --format '{{json .SBOM}}'`. If the SBOM is unexpectedly large, the image contains many packages — consider using a slimmer base image (e.g. `alpine` instead of `debian`).

---

35. **Parameter**: `uses: docker/metadata-action@v5` with tag templates
    - **Definition**: Generates standardized image tags and OCI labels based on the build context (git ref, commit SHA, event type). The `tags:` template produces multiple tags for a single build.
    - **Expected Values**: 2-3 tags per build (explicit tag + SHA tag + conditional `latest`)
    - **Currently Configured Value**: Three tag templates
    - **Tag Template Breakdown**:
      - `type=raw,value=${{ steps.params.outputs.tag }}`: The explicit tag from user input or auto-generated SHA. This is the primary tag used in deployment manifests.
      - `type=raw,value=latest,enable=${{ github.event_name == 'release' }}`: Tags as `latest` only on release events. Since releases are disabled (workflow_dispatch only), this tag is currently inactive. It will activate when release triggers are re-enabled.
      - `type=sha,prefix=sha-,format=short`: Auto-generates a tag from the git commit SHA (e.g. `sha-abc1234`). This provides an immutable, traceable tag that links the image to the exact source commit — even when the explicit tag is `latest` or `stable`.
    - **Outcome / System Impact**: Multiple tags mean a single build is accessible via multiple references. The SHA tag ensures traceability — given an image, you can always find the source commit. Without the SHA tag, a mutable tag like `v1.0` could be overwritten by a different build, breaking reproducibility.
    - **Why & When to Configure It**: The three-tag strategy covers all use cases: explicit tag for deployment, `latest` for convenience, and SHA for audit trails. Add `type=semver,pattern={{version}}` if using conventional versioning with git tags.
    - **Scaling & Troubleshooting**: Each tag creates a new manifest entry in the registry but shares the same layers (no storage duplication). If tag cleanup is needed, use the registry's tag deletion API or retention policies.
