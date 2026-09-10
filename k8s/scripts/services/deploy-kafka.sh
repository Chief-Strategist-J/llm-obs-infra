#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common.sh"

SERVICE_KEY="kafka"
ACTION="${1:-up}"
shift || true

if [ "${ACTION}" = "help" ] || [ "${ACTION}" = "--help" ] || [ "${ACTION}" = "-h" ]; then
  echo "Usage: $0 {up|down|restart|status|logs [flags]|health|port-forward [port]}"
  exit 0
fi

META="$(resolve_service_manifest "${SERVICE_KEY}")"
MANIFEST_REL="$(echo "${META}" | cut -d: -f1)"
TARGET_RESOURCE="$(echo "${META}" | cut -d: -f2)"
STORAGE_MODE="$(echo "${META}" | cut -d: -f3)"
DEFAULT_PORT="$(echo "${META}" | cut -d: -f4)"
MANIFEST_PATH="${K8S_ROOT}/${MANIFEST_REL}"

check_kubectl

case "${ACTION}" in
  up|start|apply)
    log_info "Deploying ${SERVICE_KEY} (${TARGET_RESOURCE})..."
    if [ "${STORAGE_MODE}" = "stateful" ]; then
      ensure_storage
    else
      ensure_foundation
    fi
    kubectl apply -f "${MANIFEST_PATH}"
    wait_for_workload "${TARGET_RESOURCE}"
    log_success "${SERVICE_KEY} is up and running."
    ;;
  down|stop|delete)
    log_info "Stopping ${SERVICE_KEY}..."
    kubectl delete -f "${MANIFEST_PATH}" --ignore-not-found=true
    log_success "${SERVICE_KEY} stopped."
    ;;
  restart)
    log_info "Restarting ${SERVICE_KEY}..."
    kubectl rollout restart "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}"
    wait_for_workload "${TARGET_RESOURCE}"
    log_success "${SERVICE_KEY} restarted successfully."
    ;;
  status)
    log_info "Status for ${SERVICE_KEY}:"
    kubectl get "${TARGET_RESOURCE}" -n "${K8S_NAMESPACE}" -o wide 2>/dev/null || true
    kubectl get pods -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_KEY}" -o wide 2>/dev/null || true
    kubectl get svc -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_KEY}" 2>/dev/null || true
    ;;
  logs)
    log_info "Fetching logs for ${SERVICE_KEY}..."
    kubectl logs -n "${K8S_NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_KEY}" --all-containers=true "$@"
    ;;
  health)
    check_service_health "${SERVICE_KEY}"
    ;;
  port-forward)
    local_port="${1:-${DEFAULT_PORT}}"
    log_info "Port forwarding ${SERVICE_KEY} on localhost:${local_port} -> ${DEFAULT_PORT}..."
    kubectl port-forward -n "${K8S_NAMESPACE}" "svc/llmobs-kafka-broker" "${local_port}:${DEFAULT_PORT}" --address="0.0.0.0"
    ;;
  *)
    log_error "Unknown action: ${ACTION}"
    echo "Usage: $0 {up|down|restart|status|logs [flags]|health|port-forward [port]}"
    exit 1
    ;;
esac
