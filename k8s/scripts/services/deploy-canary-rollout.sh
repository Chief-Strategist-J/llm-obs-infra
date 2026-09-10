#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common.sh"

SERVICE_KEY="canary"
ACTION="${1:-up}"
shift || true

if [ "${ACTION}" = "help" ] || [ "${ACTION}" = "--help" ] || [ "${ACTION}" = "-h" ]; then
  echo "Usage: $0 {up|down|restart|status|promote|abort|retry|logs [flags]|health|port-forward [port]}"
  exit 0
fi

META="$(resolve_service_manifest "${SERVICE_KEY}")"
MANIFEST_REL="$(echo "${META}" | cut -d: -f1)"
TARGET_RESOURCE="$(echo "${META}" | cut -d: -f2)"
DEFAULT_PORT="$(echo "${META}" | cut -d: -f4)"
MANIFEST_PATH="${K8S_ROOT}/${MANIFEST_REL}"

check_kubectl

case "${ACTION}" in
  up|start|apply)
    log_info "Deploying Canary Rollout (${TARGET_RESOURCE})..."
    ensure_foundation
    kubectl apply -f "${MANIFEST_PATH}"
    wait_for_workload "${TARGET_RESOURCE}"
    log_success "${SERVICE_KEY} rollout applied successfully."
    ;;
  down|stop|delete)
    log_info "Stopping Canary Rollout..."
    kubectl delete -f "${MANIFEST_PATH}" --ignore-not-found=true
    log_success "${SERVICE_KEY} rollout stopped."
    ;;
  restart)
    log_info "Restarting Canary Rollout..."
    if check_argo_rollouts_cli; then
      kubectl argo rollouts restart "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}"
    else
      kubectl rollout restart "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}"
    fi
    wait_for_workload "${TARGET_RESOURCE}"
    log_success "${SERVICE_KEY} restarted successfully."
    ;;
  status)
    log_info "Status for ${SERVICE_KEY} Rollout:"
    if check_argo_rollouts_cli; then
      kubectl argo rollouts get "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}" || true
    else
      kubectl get "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}" -o wide 2>/dev/null || true
    fi
    kubectl get pods -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=service-registry" -o wide 2>/dev/null || true
    kubectl get svc -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=service-registry" 2>/dev/null || true
    ;;
  promote)
    log_info "Promoting Canary Rollout..."
    if check_argo_rollouts_cli; then
      kubectl argo rollouts promote "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}" "$@"
      log_success "Rollout promoted."
    else
      log_warn "kubectl argo rollouts plugin required for progressive promotion."
    fi
    ;;
  abort)
    log_warn "Aborting Canary Rollout..."
    if check_argo_rollouts_cli; then
      kubectl argo rollouts abort "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}"
      log_success "Rollout aborted."
    else
      log_warn "kubectl argo rollouts plugin required for abort command."
    fi
    ;;
  retry)
    log_info "Retrying Canary Rollout..."
    if check_argo_rollouts_cli; then
      kubectl argo rollouts retry "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}"
      log_success "Rollout retried."
    else
      log_warn "kubectl argo rollouts plugin required for retry command."
    fi
    ;;
  logs)
    log_info "Fetching logs for ${SERVICE_KEY}..."
    kubectl logs -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=service-registry" --all-containers=true "$@"
    ;;
  health)
    check_service_health "${SERVICE_KEY}"
    ;;
  port-forward)
    local_port="${1:-${DEFAULT_PORT}}"
    log_info "Port forwarding Canary Stable service on localhost:${local_port} -> ${DEFAULT_PORT}..."
    kubectl port-forward -n "${K8S_NAMESPACE}" "svc/llmobs-canary-stable" "${local_port}:${DEFAULT_PORT}" --address="0.0.0.0"
    ;;
  *)
    log_error "Unknown action: ${ACTION}"
    echo "Usage: $0 {up|down|restart|status|promote|abort|retry|logs [flags]|health|port-forward [port]}"
    exit 1
    ;;
esac
