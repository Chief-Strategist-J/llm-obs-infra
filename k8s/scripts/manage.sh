#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

COMMAND="${1:-help}"
shift || true

execute_up() {
  local target="${1:-all}"
  shift || true

  check_kubectl
  ensure_foundation
  ensure_storage

  if [ "${target}" = "all" ]; then
    log_info "Deploying all infrastructure and application services in topological order..."

    local ordered_services=("alloydb" "redis" "clickhouse" "kafka" "tempo" "otel" "grafana" "temporal" "canary")
    for svc in "${ordered_services[@]}"; do
      "${SCRIPT_DIR}/services/deploy-${svc}.sh" up || "${SCRIPT_DIR}/services/deploy-${svc}-rollout.sh" up || "${SCRIPT_DIR}/services/deploy-${svc}-collector.sh" up
    done
    log_success "All Kubernetes services deployed successfully."
  else
    local script_path
    script_path="$(find "${SCRIPT_DIR}/services" -name "deploy-${target}*.sh" | head -n 1)"
    if [ -n "${script_path}" ] && [ -x "${script_path}" ]; then
      "${script_path}" up "$@"
    else
      log_error "Deployment script for '${target}' not found under ${SCRIPT_DIR}/services."
      exit 1
    fi
  fi
}

execute_down() {
  "${SCRIPT_DIR}/teardown-cluster.sh" "$@"
}

execute_restart() {
  local target="${1:-all}"
  shift || true

  check_kubectl

  if [ "${target}" = "all" ]; then
    log_info "Restarting all deployments and rollouts in namespace '${K8S_NAMESPACE}'..."
    kubectl rollout restart deployment -n "${K8S_NAMESPACE}"
    if check_argo_rollouts_cli; then
      kubectl argo rollouts restart rollout/llmobs-canary-rollout -n "${K8S_NAMESPACE}" || true
    fi
    log_success "Restart signal dispatched to all workloads."
  else
    local script_path
    script_path="$(find "${SCRIPT_DIR}/services" -name "deploy-${target}*.sh" | head -n 1)"
    if [ -n "${script_path}" ] && [ -x "${script_path}" ]; then
      "${script_path}" restart "$@"
    else
      log_error "Service script for '${target}' not found."
      exit 1
    fi
  fi
}

execute_status() {
  local target="${1:-all}"
  shift || true

  check_kubectl

  if [ "${target}" = "all" ]; then
    log_info "==================== Kubernetes Stack Overview ===================="
    echo -e "${CYAN}${BOLD}Deployments:${NC}"
    kubectl get deployments -n "${K8S_NAMESPACE}" -o wide 2>/dev/null || true
    echo ""
    echo -e "${CYAN}${BOLD}Argo Rollouts:${NC}"
    kubectl get rollouts -n "${K8S_NAMESPACE}" 2>/dev/null || true
    echo ""
    echo -e "${CYAN}${BOLD}Pods:${NC}"
    kubectl get pods -n "${K8S_NAMESPACE}" -o wide 2>/dev/null || true
    echo ""
    echo -e "${CYAN}${BOLD}Services:${NC}"
    kubectl get svc -n "${K8S_NAMESPACE}" 2>/dev/null || true
    echo ""
    echo -e "${CYAN}${BOLD}PersistentVolumeClaims:${NC}"
    kubectl get pvc -n "${K8S_NAMESPACE}" 2>/dev/null || true
  else
    local script_path
    script_path="$(find "${SCRIPT_DIR}/services" -name "deploy-${target}*.sh" | head -n 1)"
    if [ -n "${script_path}" ] && [ -x "${script_path}" ]; then
      "${script_path}" status "$@"
    else
      log_error "Service script for '${target}' not found."
      exit 1
    fi
  fi
}

execute_logs() {
  local target="${1:-help}"
  shift || true

  if [ "${target}" = "help" ]; then
    log_error "Please specify a service to stream logs from. Available: $(get_all_services)"
    exit 1
  fi

  local script_path
  script_path="$(find "${SCRIPT_DIR}/services" -name "deploy-${target}*.sh" | head -n 1)"
  if [ -n "${script_path}" ] && [ -x "${script_path}" ]; then
    "${script_path}" logs "$@"
  else
    log_error "Service script for '${target}' not found."
    exit 1
  fi
}

case "${COMMAND}" in
  up)
    execute_up "$@"
    ;;
  down)
    execute_down "$@"
    ;;
  restart)
    execute_restart "$@"
    ;;
  status)
    execute_status "$@"
    ;;
  logs)
    execute_logs "$@"
    ;;
  health)
    "${SCRIPT_DIR}/test-health.sh" "$@"
    ;;
  port-forward)
    "${SCRIPT_DIR}/port-forward.sh" "$@"
    ;;
  bootstrap)
    "${SCRIPT_DIR}/bootstrap-cluster.sh" "$@"
    ;;
  teardown)
    "${SCRIPT_DIR}/teardown-cluster.sh" "$@"
    ;;
  help|--help|-h)
    echo "Usage: $0 {up [service|all]|down [service|all]|restart [service|all]|status [service|all]|logs <service>|health [service|all]|port-forward <service|all|stop>|bootstrap|teardown}"
    echo ""
    echo "Services: $(get_all_services)"
    exit 0
    ;;
  *)
    log_error "Unknown command: ${COMMAND}"
    echo "Usage: $0 {up|down|restart|status|logs|health|port-forward|bootstrap|teardown} [options]"
    exit 1
    ;;
esac
