#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

TARGET_SERVICE="all"
DELETE_STORAGE=false
DELETE_NAMESPACE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delete-storage|--purge-storage)
      DELETE_STORAGE=true
      shift
      ;;
    --delete-namespace)
      DELETE_NAMESPACE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [service_name|all] [--purge-storage] [--delete-namespace]"
      exit 0
      ;;
    *)
      TARGET_SERVICE="$1"
      shift
      ;;
  esac
done

check_kubectl

if [ "${DELETE_NAMESPACE}" = true ]; then
  log_warn "Deleting entire namespace '${K8S_NAMESPACE}' and all enclosed resources..."
  kubectl delete namespace "${K8S_NAMESPACE}" --ignore-not-found=true
  log_success "Namespace '${K8S_NAMESPACE}' deleted."
  exit 0
fi

if [ "${TARGET_SERVICE}" = "all" ]; then
  log_info "Tearing down all application workloads in namespace '${K8S_NAMESPACE}'..."

  if [ -f "${K8S_ROOT}/rollouts/canary-deployment-rollout.yaml" ]; then
    log_info "Deleting canary rollout..."
    kubectl delete -f "${K8S_ROOT}/rollouts/canary-deployment-rollout.yaml" --ignore-not-found=true
  fi

  for manifest in "${K8S_ROOT}/deployments"/*.yaml; do
    if [ -f "${manifest}" ]; then
      log_info "Deleting $(basename "${manifest}")..."
      kubectl delete -f "${manifest}" --ignore-not-found=true
    fi
  done

  if [ "${DELETE_STORAGE}" = true ]; then
    log_warn "Deleting PersistentVolumeClaims..."
    kubectl delete -f "${K8S_ROOT}/persistent-volume-claims.yaml" --ignore-not-found=true
  fi

  log_success "All application workloads torn down successfully."
else
  meta="$(resolve_service_manifest "${TARGET_SERVICE}")"
  if [ -z "${meta}" ]; then
    log_error "Unknown service: ${TARGET_SERVICE}"
    exit 1
  fi

  manifest_rel="$(echo "${meta}" | cut -d: -f1)"
  manifest_path="${K8S_ROOT}/${manifest_rel}"

  if [ -f "${manifest_path}" ]; then
    log_info "Tearing down service '${TARGET_SERVICE}' using ${manifest_rel}..."
    kubectl delete -f "${manifest_path}" --ignore-not-found=true
    log_success "Service '${TARGET_SERVICE}' torn down successfully."
  else
    log_error "Manifest not found: ${manifest_path}"
    exit 1
  fi
fi
