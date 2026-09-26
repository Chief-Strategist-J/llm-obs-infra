#!/usr/bin/env bash
# ALGORITHM:
# 1. Verify existence of required CLI tools (terraform, gcloud)
# 2. Extract and validate GCP project and region configuration
# 3. Enable required Google Cloud services and APIs
# 4. Initialize Terraform working directory
# 5. Format and validate Terraform configuration files
# 6. Generate and execute Terraform execution plan

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
cd "$INFRA_DIR"

command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is not installed"; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo "Error: gcloud is not installed"; exit 1; }

if [ ! -f "terraform.tfvars" ]; then
  if [ -f "terraform.tfvars.example" ]; then
    cp "terraform.tfvars.example" "terraform.tfvars"
  else
    echo "Error: terraform.tfvars not found"; exit 1
  fi
fi

PROJECT_ID=$(grep -E '^[[:space:]]*gcp_project_id[[:space:]]*=' terraform.tfvars | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/' || true)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
  ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
  if [ -n "$ACTIVE_PROJECT" ] && [ "$ACTIVE_PROJECT" != "(unset)" ]; then
    PROJECT_ID="$ACTIVE_PROJECT"
    sed -i -E "s/gcp_project_id[[:space:]]*=[[:space:]]*\"[^\"]+\"/gcp_project_id = \"$PROJECT_ID\"/" terraform.tfvars
  fi
fi

echo "Setting up infrastructure for GCP project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1 || true

REQUIRED_SERVICES=(
  "compute.googleapis.com"
  "iam.googleapis.com"
  "cloudresourcemanager.googleapis.com"
  "logging.googleapis.com"
  "monitoring.googleapis.com"
)

for svc in "${REQUIRED_SERVICES[@]}"; do
  gcloud services enable "$svc" --project="$PROJECT_ID" >/dev/null 2>&1 || true
done

terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan
terraform apply -auto-approve tfplan
rm -f tfplan

echo "Infrastructure setup completed successfully."
terraform output
