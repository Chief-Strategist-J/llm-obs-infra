#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

TARGET_SERVICE="${1:-help}"
CUSTOM_PORT="${2:-}"

if [ "${TARGET_SERVICE}" = "help" ] || [ "${TARGET_SERVICE}" = "--help" ] || [ "${TARGET_SERVICE}" = "-h" ]; then
  echo "Usage: $0 <service_name|all|stop> [local_port]"
  echo "Services: $(get_all_services)"
  exit 0
fi

check_kubectl

is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN -n -P >/dev/null 2>&1
  elif command -v ss >/dev/null 2>&1; then
    ss -tlpn | grep -q ":${port} "
  else
    return 1
  fi
}

if [ "${TARGET_SERVICE}" = "stop" ]; then
  log_info "Stopping all active kubectl port-forward processes for namespace '${K8S_NAMESPACE}'..."
  pkill -f "kubectl port-forward.*-n ${K8S_NAMESPACE}" || true
  log_success "Active port forwards terminated."
  exit 0
fi

forward_single_service() {
  local svc_key="$1"
  local requested_port="$2"
  local meta
  meta="$(resolve_service_manifest "${svc_key}")"

  if [ -z "${meta}" ]; then
    log_error "Unknown service: ${svc_key}"
    return 1
  fi

  local target_resource
  local default_port
  target_resource="$(echo "${meta}" | cut -d: -f2)"
  default_port="$(echo "${meta}" | cut -d: -f4)"

  local res_type
  local res_name
  res_type="$(echo "${target_resource}" | cut -d/ -f1)"
  res_name="$(echo "${target_resource}" | cut -d/ -f2)"

  local target_svc="${res_name}"
  if [ "${res_type}" = "rollout" ]; then
    target_svc="llmobs-canary-stable"
  fi

  local local_port="${requested_port:-${default_port}}"

  if is_port_in_use "${local_port}"; then
    log_warn "Local port ${local_port} appears to already be in use."
  fi

  log_info "Port forwarding svc/${target_svc} (local ${local_port} -> cluster ${default_port})..."
  kubectl port-forward "svc/${target_svc}" "${local_port}:${default_port}" -n "${K8S_NAMESPACE}" --address="0.0.0.0"
}

if [ "${TARGET_SERVICE}" = "all" ]; then
  log_info "Launching background port-forwarding for all core services in namespace '${K8S_NAMESPACE}'..."
  services_list="$(get_all_services)"
  for svc in ${services_list}; do
    meta="$(resolve_service_manifest "${svc}")"
    target_resource="$(echo "${meta}" | cut -d: -f2)"
    default_port="$(echo "${meta}" | cut -d: -f4)"
    res_type="$(echo "${target_resource}" | cut -d/ -f1)"
    res_name="$(echo "${target_resource}" | cut -d/ -f2)"
    target_svc="${res_name}"
    if [ "${res_type}" = "rollout" ]; then
      target_svc="llmobs-canary-stable"
    fi

    if ! is_port_in_use "${default_port}"; then
      log_info "Forwarding ${target_svc} on port ${default_port}..."
      kubectl port-forward "svc/${target_svc}" "${default_port}:${default_port}" -n "${K8S_NAMESPACE}" --address="0.0.0.0" >/dev/null 2>&1 &
    else
      log_warn "Port ${default_port} in use, skipping background forward for ${target_svc}."
    fi
  done
  log_success "Background port-forwards started. Run '$0 stop' to terminate all forwards."
else
  forward_single_service "${TARGET_SERVICE}" "${CUSTOM_PORT}"
fi
