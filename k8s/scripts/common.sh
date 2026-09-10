#!/usr/bin/env bash

set -euo pipefail

export K8S_NAMESPACE="llmobs"
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export BOLD='\033[1m'
export NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export K8S_ROOT

log_info() {
  echo -e "${BLUE}${BOLD}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}${BOLD}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}${BOLD}[ERROR]${NC} $1" >&2
}

check_kubectl() {
  if ! command -v kubectl >/dev/null 2>&1; then
    log_error "kubectl command not found. Please install kubectl to manage Kubernetes resources."
    exit 1
  fi

  if ! kubectl cluster-info >/dev/null 2>&1; then
    log_error "Cannot connect to Kubernetes cluster. Ensure kubeconfig is active and cluster is running."
    exit 1
  fi
}

check_argo_rollouts_cli() {
  if kubectl argo rollouts version >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

ensure_foundation() {
  check_kubectl
  log_info "Ensuring foundational namespace, configmap, and secrets in namespace '${K8S_NAMESPACE}'..."
  kubectl apply -f "${K8S_ROOT}/namespace.yaml"
  kubectl apply -f "${K8S_ROOT}/configmap.yaml"
  kubectl apply -f "${K8S_ROOT}/secrets.yaml"
}

ensure_storage() {
  ensure_foundation
  log_info "Ensuring PersistentVolumeClaims in namespace '${K8S_NAMESPACE}'..."
  kubectl apply -f "${K8S_ROOT}/persistent-volume-claims.yaml"
}

resolve_service_manifest() {
  local service_key="$1"
  case "${service_key}" in
    alloydb|alloydb-db|llmobs-alloydb-db|alloydb-relational-db)
      echo "deployments/alloydb-relational-db.yaml:deployment/llmobs-alloydb-db:stateful:5432"
      ;;
    redis|redis-ledger|llmobs-redis-ledger|redis-ledger-cache)
      echo "deployments/redis-ledger-cache.yaml:deployment/llmobs-redis-ledger:stateless:6379"
      ;;
    clickhouse|clickhouse-analytics|llmobs-clickhouse-analytics|clickhouse-analytics-db)
      echo "deployments/clickhouse-analytics-db.yaml:deployment/llmobs-clickhouse-analytics:stateful:8123"
      ;;
    kafka|kafka-broker|llmobs-kafka-broker|kafka-event-broker)
      echo "deployments/kafka-event-broker.yaml:deployment/llmobs-kafka-broker:stateful:9092"
      ;;
    tempo|tempo-tracing|llmobs-tempo-tracing|tempo-trace-storage)
      echo "deployments/tempo-trace-storage.yaml:deployment/llmobs-tempo-tracing:stateful:3200"
      ;;
    otel|otel-collector|opentelemetry-collector|llmobs-opentelemetry-collector)
      echo "deployments/opentelemetry-collector.yaml:deployment/llmobs-opentelemetry-collector:stateless:4318"
      ;;
    grafana|grafana-portal|llmobs-grafana-portal|grafana-portal-ui)
      echo "deployments/grafana-portal-ui.yaml:deployment/llmobs-grafana-portal:stateful:3000"
      ;;
    temporal|temporal-engine|llmobs-temporal-engine|temporal-workflow-engine)
      echo "deployments/temporal-workflow-engine.yaml:deployment/llmobs-temporal-engine:stateless:7233"
      ;;
    canary|rollout|canary-rollout|llmobs-canary-rollout|service-registry)
      echo "rollouts/canary-deployment-rollout.yaml:rollout/llmobs-canary-rollout:rollout:31426"
      ;;
    *)
      echo ""
      ;;
  esac
}

get_all_services() {
  echo "alloydb redis clickhouse kafka tempo otel grafana temporal canary"
}

wait_for_workload() {
  local target_resource="$1"
  local timeout="${2:-180s}"

  log_info "Waiting up to ${timeout} for ${target_resource} in namespace ${K8S_NAMESPACE}..."
  if [[ "${target_resource}" == rollout/* ]]; then
    if check_argo_rollouts_cli; then
      kubectl argo rollouts status "${target_resource}" -n "${K8S_NAMESPACE}" --timeout="${timeout}"
    else
      kubectl rollout status "${target_resource}" -n "${K8S_NAMESPACE}" --timeout="${timeout}" || true
    fi
  else
    kubectl rollout status "${target_resource}" -n "${K8S_NAMESPACE}" --timeout="${timeout}"
  fi
}

check_service_health() {
  local service_name="$1"
  local meta
  meta="$(resolve_service_manifest "${service_name}")"

  if [ -z "${meta}" ]; then
    log_error "Unknown service: ${service_name}"
    return 1
  fi

  local target_resource
  target_resource="$(echo "${meta}" | cut -d: -f2)"

  log_info "Inspecting status and health for ${target_resource}..."
  kubectl get "${target_resource}" -n "${K8S_NAMESPACE}" -o wide 2>/dev/null || {
    log_warn "${target_resource} not found in namespace ${K8S_NAMESPACE}."
    return 1
  }

  echo ""
  log_info "Associated Pods:"
  kubectl get pods -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/part-of=llm-obs-infra" --field-selector "status.phase=Running" 2>/dev/null || true
  kubectl get pods -n "${K8S_NAMESPACE}" -o wide 2>/dev/null
}
