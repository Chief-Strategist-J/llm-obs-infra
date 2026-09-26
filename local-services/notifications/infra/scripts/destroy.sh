#!/usr/bin/env bash
# ALGORITHM:
# 1. Prompt operator for explicit confirmation before destructive action
# 2. Execute terraform destroy targeting all layered modules
# 3. Clean up cached local execution plans and state backups

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
cd "$INFRA_DIR"

command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is not installed"; exit 1; }

echo "WARNING: This will destroy all infrastructure resources managed in this module."
read -r -p "Type 'yes' to confirm destruction: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Destruction aborted by user."
  exit 0
fi

terraform destroy -auto-approve -var-file=terraform.tfvars
rm -f tfplan

echo "Infrastructure destruction completed successfully."
