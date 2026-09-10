#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

SKIP_STORAGE=false
WAIT_FOR_PVCS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-storage)
      SKIP_STORAGE=true
      shift
      ;;
    --wait)
      WAIT_FOR_PVCS=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--skip-storage] [--wait]"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

check_kubectl

log_info "========================================================"
log_info "Bootstrapping Kubernetes Infrastructure for '${K8S_NAMESPACE}'"
log_info "========================================================"

ensure_foundation

if [ "${SKIP_STORAGE}" = false ]; then
  ensure_storage

  if [ "${WAIT_FOR_PVCS}" = true ]; then
    log_info "Verifying PersistentVolumeClaim bindings..."
    kubectl get pvc -n "${K8S_NAMESPACE}"
  fi
else
  log_warn "Skipping PersistentVolumeClaim creation as requested."
fi

echo ""
log_success "Foundational resources created successfully in namespace '${K8S_NAMESPACE}':"
kubectl get namespace "${K8S_NAMESPACE}"
kubectl get configmap llmobs-system-config -n "${K8S_NAMESPACE}"
kubectl get secret llmobs-credentials -n "${K8S_NAMESPACE}"
kubectl get pvc -n "${K8S_NAMESPACE}" 2>/dev/null || true
echo ""
log_info "Bootstrap complete. Individual services can now be deployed."
