#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

TARGET_SERVICE="${1:-all}"

if [ "${TARGET_SERVICE}" = "--help" ] || [ "${TARGET_SERVICE}" = "-h" ]; then
  echo "Usage: $0 [service_name|all]"
  exit 0
fi

check_kubectl

inspect_single_service_health() {
  local svc_key="$1"
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

  echo -e "${CYAN}${BOLD}------------------------------------------------------------${NC}"
  echo -e "${BOLD}Health Inspection: ${svc_key} (${target_resource})${NC}"
  echo -e "${CYAN}${BOLD}------------------------------------------------------------${NC}"

  if ! kubectl get "${target_resource}" -n "${K8S_NAMESPACE}" >/dev/null 2>&1; then
    echo -e "Workload Status: ${RED}NOT DEPLOYED${NC}"
    return 1
  fi

  local ready_replicas
  if [ "${res_type}" = "rollout" ]; then
    ready_replicas="$(kubectl get "${target_resource}" -n "${K8S_NAMESPACE}" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")"
  else
    ready_replicas="$(kubectl get "${target_resource}" -n "${K8S_NAMESPACE}" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")"
  fi

  if [ -z "${ready_replicas}" ]; then
    ready_replicas="0"
  fi

  echo -e "Ready Replicas:  ${GREEN}${ready_replicas}${NC}"

  local pod_selector
  pod_selector="$(kubectl get "${target_resource}" -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.selector.matchLabels}' | sed -e 's/[{}]//g' -e 's/"//g' -e 's/:/=/g' -e 's/,/,/g')"

  if [ -n "${pod_selector}" ]; then
    echo "Associated Pods:"
    kubectl get pods -n "${K8S_NAMESPACE}" -l "${pod_selector}" -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,IP:.status.podIP,NODE:.spec.nodeName
  fi

  if kubectl get svc "${res_name}" -n "${K8S_NAMESPACE}" >/dev/null 2>&1; then
    local cluster_ip
    cluster_ip="$(kubectl get svc "${res_name}" -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.clusterIP}')"
    echo -e "Service ClusterIP: ${CYAN}${cluster_ip}:${default_port}${NC}"
    local ep_count
    ep_count="$(kubectl get endpoints "${res_name}" -n "${K8S_NAMESPACE}" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)"
    echo -e "Endpoints Available: ${GREEN}${ep_count}${NC}"
  fi

  echo ""
}

log_info "Executing health checks in namespace '${K8S_NAMESPACE}'..."

if [ "${TARGET_SERVICE}" = "all" ]; then
  services_list="$(get_all_services)"
  for svc in ${services_list}; do
    inspect_single_service_health "${svc}" || true
  done

  echo -e "${YELLOW}${BOLD}================ Recent Namespace Warnings / Events ================${NC}"
  kubectl get events -n "${K8S_NAMESPACE}" --field-selector type=Warning --sort-by='.lastTimestamp' 2>/dev/null | tail -n 10 || true
else
  inspect_single_service_health "${TARGET_SERVICE}"
fi
